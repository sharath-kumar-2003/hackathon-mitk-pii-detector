"""
Comprehensive PII Firewall enforcement tests — all 14 scenarios from specification.
Uses only synthetic PII. No hardcoded backend outcomes. All assertions driven by
actual gateway execution results.
"""
import pytest
import os
import time
from backend.detector import PIIDetector
from backend.policy_engine import PolicyEngine
from backend.tokenizer import Tokenizer
from backend.token_vault import TokenVault
from backend.tools.mock_tools import MockToolRegistry
from backend.audit_logger import AuditLogger
from backend.performance import PerformanceTracker
from backend.gateway import Gateway

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
POLICIES_FILE = os.path.join(DATA_DIR, "synthetic_tool_policies.json")


@pytest.fixture
def full_stack():
    """Full gateway stack — fresh vault per test for isolation."""
    detector = PIIDetector()
    policy_engine = PolicyEngine(POLICIES_FILE)
    vault = TokenVault(default_ttl_seconds=300)
    tokenizer = Tokenizer(vault)
    tool_registry = MockToolRegistry()
    tool_registry.clear_payload_history()
    audit_logger = AuditLogger(max_logs=200)
    perf_tracker = PerformanceTracker()
    gw = Gateway(
        detector=detector,
        policy_engine=policy_engine,
        tokenizer=tokenizer,
        token_vault=vault,
        tool_registry=tool_registry,
        audit_logger=audit_logger,
        perf_tracker=perf_tracker,
        db_manager=None,
    )
    return gw, tool_registry, vault, tokenizer


# ---------------------------------------------------------------------------
# Test 1: Tokenized recipient with redacted body PII
# ---------------------------------------------------------------------------
def test_tokenized_recipient_redacted_body(full_stack):
    """
    Section 3 canonical example:
    - 'to' field -> TOKENIZE  (send_email policy: field_rules.to = tokenize)
    - Email in 'body' -> REDACT (field_rules.body = redact)
    - Phone in 'body' -> REDACT
    - 'subject' with no PII -> ALLOW
    """
    gw, registry, vault, _ = full_stack
    session = "comp-test-01"

    payload = {
        "to": "rahul.sharma@example.com",
        "subject": "Customer Notification & Verification",
        "body": (
            "Hi, my name is Rahul Sharma, my email is rahul.sharma@example.com, "
            "my phone number is +1-202-555-0147, and my address is 123 Maple Street, Springfield. "
            "Please send these details to the external tool."
        ),
    }

    res = gw.process_request("send_email", payload, session_id=session)
    sanitized = res["sanitized_arguments"]

    # 'to' must be a token, not the raw email
    assert "rahul.sharma@example.com" not in sanitized["to"], (
        f"Raw email leaked into 'to': {sanitized['to']}"
    )
    assert sanitized["to"].startswith("<"), f"Expected token in 'to', got: {sanitized['to']}"

    # Token in 'to' must be restorable (authorized TOKENIZE mapping)
    token = sanitized["to"]
    restored = vault.retrieve(token, session)
    assert restored == "rahul.sharma@example.com", f"Restoration failed for token {token}"

    # 'body' email must be REDACTED
    assert "rahul.sharma@example.com" not in sanitized["body"], "Email leaked into body"
    assert "[REDACTED_EMAIL_ADDRESS]" in sanitized["body"], (
        f"Expected [REDACTED_EMAIL_ADDRESS] in body, got: {sanitized['body']}"
    )

    # Phone in body must be protected
    assert "+1-202-555-0147" not in sanitized["body"], "Phone number leaked into body"

    # Subject with no PII passes through
    assert sanitized["subject"] == "Customer Notification & Verification"

    # Outbound verification must pass
    assert res["outbound_verification"]["passed"] is True

    # Mock tool must have received sanitized payload
    received = registry.received_payloads[-1]["received_arguments"]
    assert "rahul.sharma@example.com" not in str(received), "Raw email reached mock tool!"


# ---------------------------------------------------------------------------
# Test 2: Repeated email in multiple fields (different per-field policies)
# ---------------------------------------------------------------------------
def test_repeated_email_multi_field_policy(full_stack):
    """
    Same email in 'to' (TOKENIZE) and 'body' (REDACT).
    Both must be protected independently per field policy.
    """
    gw, registry, vault, _ = full_stack
    session = "comp-test-02"
    email = "repeated.user@example.com"

    payload = {
        "to": email,
        "subject": "Repeated Address Test",
        "body": f"Please also send to {email} as backup.",
    }

    res = gw.process_request("send_email", payload, session_id=session)
    sanitized = res["sanitized_arguments"]

    # 'to' -> token
    assert email not in sanitized["to"]
    assert "<" in sanitized["to"]

    # 'body' -> redacted
    assert email not in sanitized["body"]
    assert "[REDACTED_EMAIL_ADDRESS]" in sanitized["body"]

    # protected_values must record both TOKENIZE and REDACT actions
    pv = res.get("protected_values", [])
    pv_emails = [p for p in pv if email in p.get("value", "")]
    actions = {p["action"] for p in pv_emails}
    assert "TOKENIZE" in actions, f"Expected TOKENIZE in actions: {actions}"
    assert "REDACT" in actions, f"Expected REDACT in actions: {actions}"


# ---------------------------------------------------------------------------
# Test 3: Address detection and redaction
# ---------------------------------------------------------------------------
def test_address_detection_and_redaction(full_stack):
    """Postal/street address in content is detected and protected."""
    gw, registry, vault, _ = full_stack
    session = "comp-test-03"

    payload = {
        "title": "Address Test",
        "content": (
            "Please ship to John Smith at Residential Address: "
            "742 Evergreen Terrace, Springfield, IL 62704. "
            "Contact: john.smith@example.com"
        ),
    }

    res = gw.process_request("document_summarizer", payload, session_id=session)
    sanitized = res["sanitized_arguments"]

    assert "john.smith@example.com" not in sanitized["content"], "Email leaked in content"
    assert "742 Evergreen Terrace" not in sanitized["content"], (
        "Street address leaked into sanitized content"
    )
    assert res["outbound_verification"]["passed"] is True


# ---------------------------------------------------------------------------
# Test 4: Authorized token restoration
# ---------------------------------------------------------------------------
def test_authorized_token_restoration(full_stack):
    """Tokenized value is fully restorable with correct session."""
    _, _, vault, tokenizer = full_stack
    session = "comp-test-04"
    original = "secure.user@example.com"

    token = tokenizer.tokenize(original, session, entity_type="EMAIL_ADDRESS")
    result = vault.restore_token(token, session)

    assert result["status"] == "success", f"Expected success, got: {result}"
    assert result["value"] == original, f"Wrong restored value: {result['value']}"
    assert result["entity_type"] == "EMAIL_ADDRESS"


# ---------------------------------------------------------------------------
# Test 5: Attempted restoration of a redacted value (no vault entry)
# ---------------------------------------------------------------------------
def test_redacted_value_has_no_vault_entry(full_stack):
    """
    Redacted values must NOT have token vault entries.
    document_summarizer.content = REDACT -> no tokens stored.
    """
    gw, _, vault, _ = full_stack
    session = "comp-test-05"

    payload = {
        "title": "Redact Only",
        "content": "SSN: 123-45-6789 and email redact.me@example.com",
    }

    res = gw.process_request("document_summarizer", payload, session_id=session)
    sanitized = res["sanitized_arguments"]

    # Content field uses REDACT policy - no <TOKEN> patterns should appear
    assert "<" not in sanitized.get("content", ""), (
        f"Tokens found in redacted field: {sanitized['content']}"
    )
    assert "[REDACTED" in sanitized.get("content", ""), "Expected redaction placeholder"

    # Vault must have zero entries for this redact-only session
    vault_entries = [v for v in vault.vault.values() if v["session_id"] == session]
    assert len(vault_entries) == 0, f"Vault entries for redact session: {vault_entries}"


# ---------------------------------------------------------------------------
# Test 6: Unauthorized restoration (wrong session)
# ---------------------------------------------------------------------------
def test_unauthorized_cross_session_restoration(full_stack):
    """Tokens must not be restorable from a different session ID."""
    _, _, vault, tokenizer = full_stack
    session_a = "comp-test-06a"
    session_b = "comp-test-06b"

    token = tokenizer.tokenize("private@example.com", session_a, entity_type="EMAIL_ADDRESS")
    result = vault.restore_token(token, session_b)

    assert result["status"] == "denied", f"Cross-session access must be denied: {result}"
    assert result["value"] is None
    assert vault.get_stats()["cross_session_attempts"] >= 1


# ---------------------------------------------------------------------------
# Test 7: Unknown token and expired token
# ---------------------------------------------------------------------------
def test_unknown_token_rejected(full_stack):
    """Unknown tokens are rejected with status=denied."""
    _, _, vault, _ = full_stack
    result = vault.restore_token("<EMAIL_DEADBEEF>", "any-session")
    assert result["status"] == "denied"
    assert "Unknown" in result["reason"]
    assert vault.get_stats()["unknown_tokens"] >= 1


def test_expired_token_rejected():
    """Expired tokens are denied even with correct session."""
    vault = TokenVault(default_ttl_seconds=0)
    tokenizer = Tokenizer(vault)
    session = "comp-test-07b"

    token = tokenizer.tokenize("will-expire@example.com", session, entity_type="EMAIL_ADDRESS", ttl=0)
    time.sleep(0.05)

    result = vault.restore_token(token, session)
    assert result["status"] == "denied"
    assert "expired" in result["reason"].lower()
    assert vault.get_stats()["expired_tokens"] >= 1


# ---------------------------------------------------------------------------
# Test 8: Unknown tool -> BLOCK, zero tool invocations
# ---------------------------------------------------------------------------
def test_unknown_tool_blocked_zero_invocations(full_stack):
    """
    Unregistered tool must be BLOCKED before any tool execution.
    Mock tool invocation count must remain zero.
    """
    gw, registry, _, _ = full_stack
    initial_count = len(registry.received_payloads)

    res = gw.process_request(
        tool_name="payment_gateway",
        arguments={"account": "9876543210", "amount": 5000, "ssn": "123-45-6789"},
        session_id="comp-test-08",
    )

    assert res["decision"] == "BLOCK", f"Expected BLOCK, got {res['decision']}"
    assert res["status"] == "blocked"
    assert res["sanitized_arguments"] is None
    assert res["mock_tool_output"] is None

    new_payloads = registry.received_payloads[initial_count:]
    assert len(new_payloads) == 0, f"Tool invoked {len(new_payloads)} times despite BLOCK!"


# ---------------------------------------------------------------------------
# Test 9: Missing policy -> fail-closed
# ---------------------------------------------------------------------------
def test_missing_policy_fail_closed(full_stack):
    """No policy configured for tool -> BLOCK (fail closed)."""
    gw, registry, _, _ = full_stack
    initial_count = len(registry.received_payloads)

    res = gw.process_request(
        tool_name="no_policy_tool_xyz",
        arguments={"data": "some value"},
        session_id="comp-test-09",
    )

    assert res["decision"] == "BLOCK"
    assert res["status"] == "blocked"
    assert len(registry.received_payloads) == initial_count


# ---------------------------------------------------------------------------
# Test 10: Malformed arguments -> BLOCK
# ---------------------------------------------------------------------------
def test_malformed_arguments_blocked(full_stack):
    """Non-dict arguments must be blocked before any processing."""
    gw, registry, _, _ = full_stack
    initial_count = len(registry.received_payloads)

    res = gw.process_request(
        tool_name="send_email",
        arguments="this is a string not a dict",
        session_id="comp-test-10",
    )

    assert res["decision"] == "BLOCK"
    assert res["status"] == "blocked"
    assert len(registry.received_payloads) == initial_count


# ---------------------------------------------------------------------------
# Test 11: Outbound verifier catches leakage (original PII remaining)
# ---------------------------------------------------------------------------
def test_outbound_verifier_catches_leakage():
    """
    If sanitization failed and raw PII reaches the verifier,
    the verifier must detect the leakage and return passed=False.
    """
    from backend.outbound_verifier import OutboundVerifier

    verifier = OutboundVerifier()
    raw_email = "leaked.user@example.com"

    leaked_payload = {"to": raw_email, "body": "Sensitive data here"}
    protected_items = [{"field": "to", "value": raw_email, "action": "TOKENIZE"}]

    result = verifier.verify_payload(leaked_payload, protected_items)
    assert result["passed"] is False, "Verifier must detect the leak"
    assert result["leakage_detected"] is True
    assert raw_email in result["leaked_values"]


# ---------------------------------------------------------------------------
# Test 12: Block invocation count = 0 for all block scenarios
# ---------------------------------------------------------------------------
def test_all_block_scenarios_zero_invocations(full_stack):
    """
    For every BLOCK trigger, the mock tool must receive zero new payloads.
    """
    gw, registry, _, _ = full_stack

    scenarios = [
        ("hacker_tool", {"cmd": "drop table users"}, "Unknown tool"),
        ("send_email", {"to": "a@b.com", "body": "x", "INJECTED_FIELD": "bad"}, "Unpermitted field"),
        ("web_search", "string not dict", "Malformed args"),
    ]

    for tool, args, desc in scenarios:
        count_before = len(registry.received_payloads)
        res = gw.process_request(tool, args, session_id=f"block-zero-{desc.replace(' ', '-')}")
        count_after = len(registry.received_payloads)

        assert res["status"] == "blocked", f"[{desc}] Expected blocked, got {res['status']}"
        assert count_after == count_before, (
            f"[{desc}] Tool was invoked despite BLOCK! "
            f"New payloads: {registry.received_payloads[count_before:]}"
        )


# ---------------------------------------------------------------------------
# Test 13: Tool response re-protection (token in response is restorable)
# ---------------------------------------------------------------------------
def test_tool_response_token_restorable(full_stack):
    """
    After a tokenized send_email call, the token in the tool response
    must be restorable from the vault using the same session.
    """
    gw, _, vault, _ = full_stack
    session = "comp-test-13"
    email = "resp.restore@example.com"

    payload = {"to": email, "subject": "Restoration Test", "body": "Test body content."}
    res = gw.process_request("send_email", payload, session_id=session)

    token_in_to = res["sanitized_arguments"]["to"]
    assert vault.retrieve(token_in_to, session) == email, (
        "Token not in vault — tokenization failed or session mismatch"
    )

    # restoration_result should attempt to restore tokens from tool response
    restoration = res.get("restoration_result") or {}
    if restoration.get("tokens_found"):
        restored_text = restoration.get("restored_text", "")
        assert email in restored_text, (
            f"Original email not in restored_text: {restored_text}"
        )


# ---------------------------------------------------------------------------
# Test 14: Natural language + nested JSON sanitization
# ---------------------------------------------------------------------------
def test_natural_language_full_sanitization(full_stack):
    """Natural-language body with multiple PII types is fully sanitized."""
    gw, registry, _, _ = full_stack

    payload = {
        "title": "NL Test",
        "content": (
            "Dear Support Team, I am John Doe. My SSN is 123-45-6789. "
            "Please update my email: john.doe@example.com and phone: +1-555-019-2834. "
            "My Aadhaar is 1234 5678 9012. Thank you."
        ),
    }

    res = gw.process_request("document_summarizer", payload, session_id="comp-test-14a")
    content = res["sanitized_arguments"]["content"]

    assert "123-45-6789" not in content, "SSN leaked"
    assert "john.doe@example.com" not in content, "Email leaked"
    assert "+1-555-019-2834" not in content, "Phone leaked"
    assert "1234 5678 9012" not in content, "Aadhaar leaked"
    assert res["outbound_verification"]["passed"] is True


def test_nested_json_all_fields_sanitized(full_stack):
    """Nested dict + list values with PII are all sanitized."""
    gw, registry, _, _ = full_stack

    payload = {
        "to": "outer@example.com",
        "subject": "Nested JSON",
        "body": {
            "primary_email": "inner@example.com",
            "phones": ["9876543210", "9000000001"],
            "note": "Contact inner@example.com or call 9876543210",
        },
    }

    res = gw.process_request("send_email", payload, session_id="comp-test-14b")
    body = res["sanitized_arguments"]["body"]

    assert "inner@example.com" not in str(body), "Inner email leaked"
    assert "9876543210" not in str(body), "Phone leaked"
    assert "9000000001" not in str(body), "Phone leaked"
    assert res["outbound_verification"]["passed"] is True


# ---------------------------------------------------------------------------
# Metrics: Leakage prevention rate = 100% for all planted PII
# ---------------------------------------------------------------------------
def test_leakage_prevention_rate_100_percent(full_stack):
    """
    Plant known PII across fields; verify none reaches the mock tool.
    Leakage prevention rate must be 100%.
    """
    gw, registry, vault, _ = full_stack
    session = "metrics-test-01"

    planted = {
        "email_to": "plant.user@example.com",
        "email_body": "plant.user@example.com",
        "phone_body": "+1-555-777-8888",
    }

    payload = {
        "to": planted["email_to"],
        "subject": "Metrics Test",
        "body": f"Contact {planted['email_body']} or call {planted['phone_body']}",
    }

    res = gw.process_request("send_email", payload, session_id=session)
    received = registry.received_payloads[-1]["received_arguments"]
    received_str = str(received)

    protected = sum(1 for v in planted.values() if v not in received_str)
    rate = (protected / len(planted)) * 100

    print(f"\n[Metrics] Planted: {len(planted)}, Protected: {protected}, Rate: {rate:.1f}%")

    assert rate == 100.0, (
        f"Leakage prevention rate: {rate}% — expected 100%. Received: {received}"
    )
    assert res["outbound_verification"]["passed"] is True
    assert len(res["pii_detected"]) >= 2, f"Expected >= 2 detections, got {len(res['pii_detected'])}"
