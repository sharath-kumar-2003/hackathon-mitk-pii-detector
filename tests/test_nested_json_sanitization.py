import pytest
from backend.detector import PIIDetector
from backend.policy_engine import PolicyEngine
from backend.tokenizer import Tokenizer
from backend.token_vault import TokenVault
from backend.tools.mock_tools import MockToolRegistry
from backend.audit_logger import AuditLogger
from backend.performance import PerformanceTracker
from backend.gateway import Gateway
from backend.database import DatabaseManager

def test_nested_json_sanitization():
    detector = PIIDetector()
    policy_engine = PolicyEngine("data/synthetic_tool_policies.json")
    vault = TokenVault()
    tokenizer = Tokenizer(vault)
    tool_registry = MockToolRegistry()
    audit_logger = AuditLogger()
    perf_tracker = PerformanceTracker()
    db_manager = DatabaseManager()

    gateway = Gateway(
        detector=detector,
        policy_engine=policy_engine,
        tokenizer=tokenizer,
        token_vault=vault,
        tool_registry=tool_registry,
        audit_logger=audit_logger,
        perf_tracker=perf_tracker,
        db_manager=db_manager
    )

    nested_args = {
        "to": "admin@example.com",
        "subject": "Nested Test",
        "body": {
            "contact_email": "nested.user@example.com",
            "phones": ["9876543210", "9000000001"]
        }
    }

    res = gateway.process_request("send_email", nested_args, session_id="test_nested_sess")
    
    assert res["status"] in ["sanitized", "allowed"]
    sanitized = res["sanitized_arguments"]
    assert "nested.user@example.com" not in str(sanitized["body"])
    assert "9876543210" not in str(sanitized["body"])
    assert res["outbound_verification"]["passed"] is True
