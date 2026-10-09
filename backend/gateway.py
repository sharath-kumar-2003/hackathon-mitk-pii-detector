import time
import uuid
from typing import Dict, Any, List, Optional
from backend.detector import PIIDetector
from backend.policy_engine import PolicyEngine
from backend.tokenizer import Tokenizer
from backend.token_vault import TokenVault
from backend.tools.mock_tools import MockToolRegistry
from backend.outbound_verifier import OutboundVerifier
from backend.audit_logger import AuditLogger
from backend.performance import PerformanceTracker
from backend.database import DatabaseManager

class Gateway:
    def __init__(
        self,
        detector: PIIDetector,
        policy_engine: PolicyEngine,
        tokenizer: Tokenizer,
        token_vault: TokenVault,
        tool_registry: MockToolRegistry,
        audit_logger: AuditLogger,
        perf_tracker: PerformanceTracker,
        db_manager: Optional[DatabaseManager] = None
    ):
        self.detector = detector
        self.policy_engine = policy_engine
        self.tokenizer = tokenizer
        self.token_vault = token_vault
        self.tool_registry = tool_registry
        self.audit_logger = audit_logger
        self.perf_tracker = perf_tracker
        self.db_manager = db_manager
        self.outbound_verifier = OutboundVerifier()

    def _sanitize_recursive(
        self,
        payload: Any,
        redact_fields: List[str],
        policy_action: str,
        session_id: str,
        req_id: str,
        protected_values: List[Dict[str, Any]],
        parent_key: str = "",
        inside_redact: bool = False
    ) -> Any:
        if isinstance(payload, str):
            spans = self.detector.analyze_text(payload)
            if spans:
                should_protect = inside_redact or (not redact_fields) or (parent_key in redact_fields)
                if should_protect:
                    for s in spans:
                        protected_values.append({"field": parent_key or "text", "value": payload[s.start:s.end]})
                    if policy_action == "tokenize":
                        return self.tokenizer.tokenize_spans(payload, spans, session_id, req_id)
                    elif policy_action == "redact":
                        return self.detector.anonymize_text(payload, spans)
            return payload

        elif isinstance(payload, dict):
            new_dict = {}
            for k, v in payload.items():
                is_redact_key = inside_redact or (k in redact_fields) or (not redact_fields)
                new_dict[k] = self._sanitize_recursive(
                    v, redact_fields, policy_action, session_id, req_id, protected_values, parent_key=k, inside_redact=is_redact_key
                )
            return new_dict

        elif isinstance(payload, list):
            return [
                self._sanitize_recursive(
                    item, redact_fields, policy_action, session_id, req_id, protected_values, parent_key=parent_key, inside_redact=inside_redact
                )
                for item in payload
            ]

        return payload

    def process_request(
        self,
        tool_name: str,
        arguments: Any,
        session_id: str = "default_session",
        user_prompt_preview: str = "",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        req_id = request_id or f"REQ-{uuid.uuid4().hex[:8].upper()}"
        start_total = time.perf_counter()

        stage_timings = {
            "detection_ms": 0.0,
            "policy_ms": 0.0,
            "transformation_ms": 0.0,
            "verification_ms": 0.0
        }

        # Step 1: Policy Engine Evaluation
        t_policy_start = time.perf_counter()
        policy_eval = self.policy_engine.evaluate_request(tool_name, arguments)
        stage_timings["policy_ms"] = (time.perf_counter() - t_policy_start) * 1000.0

        if policy_eval["decision"] == "BLOCK":
            total_ms = (time.perf_counter() - start_total) * 1000.0
            self.perf_tracker.record_run(0.001, total_ms, stage_timings)
            
            result = {
                "request_id": req_id,
                "status": "blocked",
                "action": "BLOCK",
                "decision": "BLOCK",
                "reason": policy_eval["reason"],
                "pii_detected": [],
                "sanitized_arguments": None,
                "mock_tool_output": None,
                "outbound_verification": {
                    "passed": True,
                    "explanation": "Call blocked prior to tool execution."
                },
                "restoration_result": None,
                "timings_ms": {**stage_timings, "total_ms": round(total_ms, 3)}
            }

            event = {
                "request_id": req_id,
                "session_id": session_id,
                "tool_name": tool_name,
                "user_prompt_preview": user_prompt_preview,
                "original_arguments_preview": arguments,
                "sanitized_arguments_preview": None,
                "policy_decision": "BLOCK",
                "policy_reason": policy_eval["reason"],
                "pii_detected": [],
                "sanitization_action": "blocked",
                "outbound_verification": result["outbound_verification"],
                "restoration_outcome": None,
                "timings_ms": result["timings_ms"],
                "final_status": "BLOCKED"
            }
            self.audit_logger.log_event(event)
            if self.db_manager:
                self.db_manager.log_event(event)

            return result

        # Step 2: PII Detection
        t_detect_start = time.perf_counter()
        detected_entities = self.detector.analyze_payload(arguments)
        stage_timings["detection_ms"] = (time.perf_counter() - t_detect_start) * 1000.0

        # Step 3: Transformation / Redaction / Tokenization (Recursive)
        t_trans_start = time.perf_counter()
        policy_action = policy_eval["action"].lower()
        protected_values: List[Dict[str, Any]] = []

        redact_fields = policy_eval.get("policy", {}).get("redact_pii_in", []) if policy_eval.get("policy") else []

        sanitized_arguments = self._sanitize_recursive(
            arguments, redact_fields, policy_action, session_id, req_id, protected_values
        )

        stage_timings["transformation_ms"] = (time.perf_counter() - t_trans_start) * 1000.0

        # Step 4: Measure Baseline Latency (Direct Mock Tool Call without Firewall)
        t_base_start = time.perf_counter()
        try:
            _ = self.tool_registry.execute_tool(tool_name, arguments, session_id, is_baseline_check=True)
        except Exception:
            pass
        baseline_ms = (time.perf_counter() - t_base_start) * 1000.0

        # Step 5: Execute Mock Tool through Protected Path
        tool_output = self.tool_registry.execute_tool(tool_name, sanitized_arguments, session_id)
        received_by_mock = tool_output.get("received_payload", sanitized_arguments)

        # Step 6: Outbound Leakage Verification
        t_verif_start = time.perf_counter()
        verification_result = self.outbound_verifier.verify_payload(received_by_mock, protected_values)
        stage_timings["verification_ms"] = (time.perf_counter() - t_verif_start) * 1000.0

        # Step 7: Authorized Restoration of Mock Tool Response
        restoration_res = None
        if isinstance(tool_output, dict):
            resp_str = str(tool_output)
            restoration_res = self.tokenizer.restore_text(resp_str, session_id)

        total_ms = (time.perf_counter() - start_total) * 1000.0
        self.perf_tracker.record_run(baseline_ms, total_ms, stage_timings)

        final_status = "SANITIZED" if detected_entities else "ALLOWED"
        if not verification_result["passed"]:
            final_status = "LEAKAGE_FAILED"

        result = {
            "request_id": req_id,
            "status": final_status.lower(),
            "action": policy_action,
            "decision": policy_eval["decision"],
            "reason": policy_eval["reason"],
            "pii_detected": detected_entities,
            "protected_values": protected_values,
            "sanitized_arguments": sanitized_arguments,
            "received_by_mock_tool": received_by_mock,
            "mock_tool_output": tool_output,
            "outbound_verification": verification_result,
            "restoration_result": restoration_res,
            "timings_ms": {
                **stage_timings,
                "baseline_ms": round(baseline_ms, 3),
                "total_ms": round(total_ms, 3)
            }
        }

        event = {
            "request_id": req_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "user_prompt_preview": user_prompt_preview,
            "original_arguments_preview": arguments,
            "sanitized_arguments_preview": sanitized_arguments,
            "policy_decision": policy_eval["decision"],
            "policy_reason": policy_eval["reason"],
            "pii_detected": detected_entities,
            "sanitization_action": policy_action,
            "outbound_verification": verification_result,
            "restoration_outcome": restoration_res,
            "timings_ms": result["timings_ms"],
            "final_status": final_status
        }
        self.audit_logger.log_event(event)
        if self.db_manager:
            self.db_manager.log_event(event)

        return result
