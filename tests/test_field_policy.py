import pytest
import os
from backend.detector import PIIDetector
from backend.policy_engine import PolicyEngine
from backend.tokenizer import Tokenizer
from backend.token_vault import TokenVault
from backend.tools.mock_tools import MockToolRegistry
from backend.audit_logger import AuditLogger
from backend.performance import PerformanceTracker
from backend.gateway import Gateway

@pytest.fixture
def gateway_setup():
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    policies_file = os.path.join(DATA_DIR, "synthetic_tool_policies.json")
    
    detector = PIIDetector()
    policy_engine = PolicyEngine(policies_file)
    vault = TokenVault()
    tokenizer = Tokenizer(vault)
    tool_registry = MockToolRegistry()
    audit_logger = AuditLogger()
    perf_tracker = PerformanceTracker()

    gw = Gateway(
        detector=detector,
        policy_engine=policy_engine,
        tokenizer=tokenizer,
        token_vault=vault,
        tool_registry=tool_registry,
        audit_logger=audit_logger,
        perf_tracker=perf_tracker
    )
    return gw, tool_registry, vault

def test_integration_email_policy_field_differentiation(gateway_setup):
    """
    Integration test specified in Section 4 of prompt:
    Same PII (rahul@example.com) in 'to' (TOKENIZE) and 'body' (REDACT).
    """
    gw, registry, vault = gateway_setup
    
    payload = {
        "to": "rahul@example.com",
        "subject": "Customer Notification",
        "body": "Please contact rahul@example.com about the request."
    }
    
    res = gw.process_request(
        tool_name="send_email",
        arguments=payload,
        session_id="test_field_diff_01"
    )
    
    sanitized = res["sanitized_arguments"]
    
    # 1. 'to' field must be TOKENIZED with opaque scoped token <EMAIL_ADDRESS_XXXXXX>
    assert "rahul@example.com" not in sanitized["to"]
    assert sanitized["to"].startswith("<EMAIL_ADDRESS_") or sanitized["to"].startswith("<EMAIL_")
    
    # 2. 'body' field must be REDACTED with [REDACTED_EMAIL_ADDRESS] placeholder
    assert "rahul@example.com" not in sanitized["body"]
    assert "[REDACTED_EMAIL_ADDRESS]" in sanitized["body"]
    
    # 3. 'subject' field must be ALLOWED as is
    assert sanitized["subject"] == "Customer Notification"
    
    # 4. Outbound verification must pass
    assert res["outbound_verification"]["passed"] is True
    
    # 5. Token in 'to' must be restorable via Token Vault
    token_in_to = sanitized["to"]
    restored_val = vault.retrieve(token_in_to, "test_field_diff_01")
    assert restored_val == "rahul@example.com"

def test_field_policy_block_unpermitted():
    """Test fail-closed behavior when an unpermitted field is provided."""
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    policies_file = os.path.join(DATA_DIR, "synthetic_tool_policies.json")
    gw = Gateway(
        detector=PIIDetector(),
        policy_engine=PolicyEngine(policies_file),
        tokenizer=Tokenizer(TokenVault()),
        token_vault=TokenVault(),
        tool_registry=MockToolRegistry(),
        audit_logger=AuditLogger(),
        perf_tracker=PerformanceTracker()
    )
    
    res = gw.process_request(
        tool_name="web_search",
        arguments={"query": "test", "unauthorized_secret": "MALICIOUS-123"},
        session_id="test_block"
    )
    
    assert res["decision"] == "BLOCK"
    assert res["status"] == "blocked"
