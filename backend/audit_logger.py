import time
import uuid
from typing import Dict, Any, List, Optional

class AuditLogger:
    def __init__(self, max_logs: int = 500):
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = max_logs

    def clear(self):
        self.logs.clear()

    def log_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        req_id = event_data.get("request_id") or f"REQ-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "request_id": req_id,
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": event_data.get("session_id", "session_default"),
            "tool_name": event_data.get("tool_name", "unknown"),
            "user_prompt_preview": event_data.get("user_prompt_preview", ""),
            "original_arguments_preview": event_data.get("original_arguments_preview", {}),
            "sanitized_arguments_preview": event_data.get("sanitized_arguments_preview", {}),
            "policy_decision": event_data.get("policy_decision", "UNKNOWN"),
            "policy_reason": event_data.get("policy_reason", ""),
            "pii_detected": event_data.get("pii_detected", []), # List of dicts or PII entity types
            "sanitization_action": event_data.get("sanitization_action", "none"),
            "outbound_verification": event_data.get("outbound_verification", {}),
            "restoration_outcome": event_data.get("restoration_outcome", {}),
            "timings_ms": event_data.get("timings_ms", {}),
            "final_status": event_data.get("final_status", "COMPLETED"),
            "is_evaluation_run": event_data.get("is_evaluation_run", False)
        }
        self.logs.insert(0, record)
        if len(self.logs) > self.max_logs:
            self.logs.pop()
        return record

    def get_logs(self, limit: int = 100, tool_name: Optional[str] = None, pii_type: Optional[str] = None, outcome: Optional[str] = None) -> List[Dict[str, Any]]:
        filtered = self.logs
        if tool_name:
            filtered = [l for l in filtered if l.get("tool_name") == tool_name]
        if pii_type:
            filtered = [l for l in filtered if any(p.get("entity_type") == pii_type for p in l.get("pii_detected", []))]
        if outcome:
            filtered = [l for l in filtered if l.get("final_status", "").lower() == outcome.lower() or l.get("policy_decision", "").lower() == outcome.lower()]
        return filtered[:limit]
