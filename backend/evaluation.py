import json
import os
import time
from typing import Dict, Any, List, Optional
from backend.gateway import Gateway
from backend.token_vault import TokenVault
from backend.tokenizer import Tokenizer
from backend.performance import PerformanceTracker

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

class EvaluationRunner:
    def __init__(self, gateway: Gateway, vault: TokenVault, tokenizer: Tokenizer, perf_tracker: PerformanceTracker):
        self.gateway = gateway
        self.vault = vault
        self.tokenizer = tokenizer
        self.perf_tracker = perf_tracker
        self.latest_results: Optional[Dict[str, Any]] = None

    def reset(self):
        """Clears evaluation state, vault, and performance records."""
        self.latest_results = None
        self.vault.reset_metrics()
        self.perf_tracker.clear()
        self.gateway.audit_logger.clear()
        self.gateway.tool_registry.clear_payload_history()

    def load_test_cases(self) -> List[Dict[str, Any]]:
        path = os.path.join(DATA_DIR, "synthetic_test_cases.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return []

    def run_evaluation(self) -> Dict[str, Any]:
        test_cases = self.load_test_cases()
        if not test_cases:
            return {"error": "No synthetic test cases found."}

        # Clear prior state for fresh benchmark
        self.reset()

        tp = 0
        fp = 0
        fn = 0
        tn = 0

        total_protected_tested = 0
        leakage_free_count = 0
        leakage_failures = 0
        leakage_details = []

        test_case_results = []
        pii_by_category = {}

        # 1. Run standard Gateway pipeline over 100 test cases
        for tc in test_cases:
            tc_id = tc["id"]
            category = tc.get("category", "UNKNOWN")
            tool_name = tc.get("tool_name", "web_search")
            args = tc.get("arguments", {})
            user_prompt = tc.get("user_prompt", "")
            expected_pii = tc.get("expected_pii", [])
            expected_action = tc.get("expected_action", "allow")
            session_id = f"eval_session_{tc_id}"

            # Execute request through mandatory gateway
            res = self.gateway.process_request(
                tool_name=tool_name,
                arguments=args,
                session_id=session_id,
                user_prompt_preview=user_prompt,
                request_id=f"EVAL-{tc_id}"
            )

            # Ground Truth vs Prediction Evaluation
            detected_pii = res.get("pii_detected", [])
            actual_action = res.get("action", "allow")
            actual_decision = res.get("decision", "ALLOW")

            # Update category counts
            if category not in pii_by_category:
                pii_by_category[category] = {"detected": 0, "expected": 0, "cases": 0}
            pii_by_category[category]["cases"] += 1
            pii_by_category[category]["expected"] += len(expected_pii)
            pii_by_category[category]["detected"] += len(detected_pii)

            # Calculate Confusion Matrix (TP, FP, FN, TN)
            # Unit of evaluation: PII instance & non-PII instance checks
            num_expected = len(expected_pii)
            num_detected = len(detected_pii)

            if num_expected > 0 and num_detected > 0:
                matched_tp = min(num_expected, num_detected)
                tp += matched_tp
                if num_detected > num_expected:
                    fp += (num_detected - num_expected)
                elif num_expected > num_detected:
                    fn += (num_expected - num_detected)
            elif num_expected > 0 and num_detected == 0:
                fn += num_expected
            elif num_expected == 0 and num_detected > 0:
                fp += num_detected
            else: # num_expected == 0 and num_detected == 0
                tn += 1

            # Outbound Leakage Assessment
            protected_values = tc.get("protected_values", [])
            if protected_values and actual_decision != "BLOCK":
                total_protected_tested += len(protected_values)
                verif = res.get("outbound_verification", {})
                if verif.get("passed", True):
                    leakage_free_count += len(protected_values)
                else:
                    leakage_failures += 1
                    leakage_details.append({
                        "test_case_id": tc_id,
                        "tool_name": tool_name,
                        "leaked_values": verif.get("leaked_values", []),
                        "received_payload": res.get("received_by_mock_tool")
                    })

            # Check overall pass/fail status for test case
            passed_test = True
            if actual_decision == "BLOCK" and expected_action == "block":
                passed_test = True
            elif actual_decision != "BLOCK" and expected_action == "block":
                passed_test = False
            elif expected_action != "block" and actual_decision == "BLOCK":
                passed_test = False
            elif expected_action in ["redact", "tokenize"] and not detected_pii and num_expected > 0:
                passed_test = False

            test_case_results.append({
                "id": tc_id,
                "category": category,
                "tool_name": tool_name,
                "user_prompt": user_prompt,
                "expected_pii_count": num_expected,
                "detected_pii_count": num_detected,
                "expected_action": expected_action,
                "actual_decision": actual_decision,
                "passed": passed_test,
                "timings_ms": res.get("timings_ms", {})
            })

        # 2. Execute Restoration Benchmark Cases (Authorized, Cross-session, Expired, Unknown)
        restoration_test_cases = [
            # Valid authorized restoration
            {"token_type": "PHONE_NUMBER", "val": "9876543210", "sess": "s_valid", "req_sess": "s_valid", "expect": "success"},
            {"token_type": "EMAIL_ADDRESS", "val": "eval_user@example.com", "sess": "s_valid2", "req_sess": "s_valid2", "expect": "success"},
            {"token_type": "PERSON", "val": "Anita Sharma", "sess": "s_valid3", "req_sess": "s_valid3", "expect": "success"},
            # Cross-session unauthorized restoration
            {"token_type": "EMAIL_ADDRESS", "val": "secret_cross@example.com", "sess": "sess_A", "req_sess": "sess_B", "expect": "denied_cross_session"},
            {"token_type": "IN_PAN", "val": "ABCDE1234F", "sess": "sess_X", "req_sess": "sess_Y", "expect": "denied_cross_session"},
            # Unknown token restoration
            {"token_type": "UNKNOWN", "val": None, "sess": "s_any", "req_sess": "s_any", "token_override": "[TOK_UNKNOWN_999999]", "expect": "unknown"},
            # Expired token restoration
            {"token_type": "EXPIRED", "val": "expired_val", "sess": "s_exp", "req_sess": "s_exp", "ttl": 0, "expect": "expired"}
        ]

        for r_case in restoration_test_cases:
            if r_case.get("token_override"):
                token = r_case["token_override"]
            else:
                ttl = r_case.get("ttl", 300)
                token = self.tokenizer.tokenize(r_case["val"], r_case["sess"], entity_type=r_case["token_type"], ttl=ttl)
                if ttl == 0:
                    time.sleep(0.01)

            # Perform restoration attempt
            _ = self.vault.restore_token(token, r_case["req_sess"])

        # Calculate Final Metrics
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        detection_rate = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0

        leakage_prevention_rate = (leakage_free_count / total_protected_tested * 100.0) if total_protected_tested > 0 else 100.0

        vault_stats = self.vault.get_stats()
        perf_stats = self.perf_tracker.get_summary_stats()

        summary = {
            "total_requests": len(test_cases),
            "requests_summary": {
                "allowed": sum(1 for r in test_case_results if r["actual_decision"] == "ALLOW"),
                "sanitized": sum(1 for r in test_case_results if r["actual_decision"] in ["REDACT", "TOKENIZE"]),
                "blocked": sum(1 for r in test_case_results if r["actual_decision"] == "BLOCK")
            },
            "detection_analytics": {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1_score, 4),
                "detection_rate_pct": round(detection_rate, 2),
                "by_category": pii_by_category,
                "test_cases": test_case_results
            },
            "leakage_prevention": {
                "total_protected_instances": total_protected_tested,
                "leakage_free_instances": leakage_free_count,
                "leakage_count": leakage_failures,
                "leakage_prevention_rate_pct": round(leakage_prevention_rate, 2),
                "leakage_failures": leakage_details
            },
            "restoration_analytics": vault_stats,
            "performance_analytics": perf_stats
        }

        self.latest_results = summary
        return summary
