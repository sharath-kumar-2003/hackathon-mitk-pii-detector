import time
from typing import Dict, Any, Optional

class TokenVault:
    def __init__(self, default_ttl_seconds: int = 300):
        self.vault: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds
        
        # Restoration audit counters
        self.metrics = {
            "tokens_generated": 0,
            "authorized_attempts": 0,
            "successful_restorations": 0,
            "failed_restorations": 0,
            "expired_tokens": 0,
            "unknown_tokens": 0,
            "cross_session_attempts": 0
        }

    def reset_metrics(self):
        self.vault.clear()
        self.metrics = {
            "tokens_generated": 0,
            "authorized_attempts": 0,
            "successful_restorations": 0,
            "failed_restorations": 0,
            "expired_tokens": 0,
            "unknown_tokens": 0,
            "cross_session_attempts": 0
        }

    def store(self, token: str, value: str, entity_type: str, session_id: str, request_id: str = "req_default", ttl: Optional[int] = None) -> None:
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        now = time.time()
        self.vault[token] = {
            "value": value,
            "entity_type": entity_type,
            "session_id": session_id,
            "request_id": request_id,
            "created_at": now,
            "expires_at": now + ttl_seconds
        }
        self.metrics["tokens_generated"] += 1

    def retrieve(self, token: str, session_id: str) -> Optional[str]:
        """Backward compatible retrieve method that returns string or None."""
        result = self.restore_token(token, session_id)
        return result["value"]

    def restore_token(self, token: str, session_id: str) -> Dict[str, Any]:
        """Strict authorized restoration method returning detailed result status."""
        self.metrics["authorized_attempts"] += 1
        now = time.time()

        if token not in self.vault:
            self.metrics["failed_restorations"] += 1
            self.metrics["unknown_tokens"] += 1
            return {
                "status": "denied",
                "reason": "Unknown token",
                "value": None,
                "token": token
            }

        record = self.vault[token]

        # Expiry check
        if now > record["expires_at"]:
            self.metrics["failed_restorations"] += 1
            self.metrics["expired_tokens"] += 1
            return {
                "status": "denied",
                "reason": "Token expired",
                "value": None,
                "token": token
            }

        # Cross-session security check
        if record["session_id"] != session_id:
            self.metrics["failed_restorations"] += 1
            self.metrics["cross_session_attempts"] += 1
            return {
                "status": "denied",
                "reason": f"Cross-session authorization failure (Token bound to session '{record['session_id']}', request from '{session_id}')",
                "value": None,
                "token": token
            }

        # Successful exact-match restoration
        self.metrics["successful_restorations"] += 1
        return {
            "status": "success",
            "reason": "Authorized token restoration successful",
            "value": record["value"],
            "entity_type": record["entity_type"],
            "token": token
        }

    def get_stats(self) -> Dict[str, Any]:
        total_eligible = self.metrics["authorized_attempts"]
        accuracy = (self.metrics["successful_restorations"] / total_eligible * 100.0) if total_eligible > 0 else 0.0
        return {
            **self.metrics,
            "restoration_accuracy": round(accuracy, 2),
            "active_tokens_in_vault": len(self.vault)
        }
