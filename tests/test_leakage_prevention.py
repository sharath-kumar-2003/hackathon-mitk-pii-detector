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
    return gw, tool_registry

def test_leakage_prevention_redaction(gateway_setup):
    gw, registry = gateway_setup
    secret_phone = "9876543210"
    
    res = gw.process_request(
        tool_name="web_search",
        arguments={"query": f"Search details for helpline {secret_phone}"},
        session_id="test_leak_01"
    )
    
    assert res["decision"] == "REDACT"
    assert res["outbound_verification"]["passed"] is True
    
    # Check exact received payload in mock tool registry
    received_payload = registry.received_payloads[-1]["received_arguments"]
    assert secret_phone not in str(received_payload)
    assert "<" in str(received_payload) or "[TOK_" in str(received_payload) or "[REDACTED" in str(received_payload)

def test_leakage_prevention_tokenization(gateway_setup):
    gw, registry = gateway_setup
    secret_email = "sensitive.user@example.com"
    
    res = gw.process_request(
        tool_name="send_email",
        arguments={
            "to": secret_email,
            "subject": "Confidential",
            "body": f"Please send report to {secret_email}"
        },
        session_id="test_leak_02"
    )
    
    assert res["decision"] == "TOKENIZE"
    assert res["outbound_verification"]["passed"] is True
    
    received_payload = registry.received_payloads[-1]["received_arguments"]
    # Body should contain token, NOT the raw email string
    assert secret_email not in received_payload["body"]
    assert "<EMAIL" in received_payload["body"] or "<" in received_payload["body"]

def test_policy_fail_closed_unknown_tool(gateway_setup):
    gw, registry = gateway_setup
    
    res = gw.process_request(
        tool_name="unknown_malicious_tool",
        arguments={"cmd": "rm -rf /"},
        session_id="test_fail_close"
    )
    
    assert res["decision"] == "BLOCK"
    assert res["status"] == "blocked"
    # Tool must NOT have been called!
    last_payloads = [p for p in registry.received_payloads if p["tool_name"] == "unknown_malicious_tool"]
    assert len(last_payloads) == 0

def test_policy_fail_closed_unpermitted_field(gateway_setup):
    gw, registry = gateway_setup
    
    res = gw.process_request(
        tool_name="web_search",
        arguments={"query": "test", "unpermitted_secret_token": "SECRET-12345"},
        session_id="test_unpermitted"
    )
    
    assert res["decision"] == "BLOCK"
    assert res["status"] == "blocked"
