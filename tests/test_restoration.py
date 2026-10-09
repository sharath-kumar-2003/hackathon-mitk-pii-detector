from backend.token_vault import TokenVault
from backend.tokenizer import Tokenizer
import time

def test_restoration_success():
    """Test that a token maps back to the exact original value with the correct session."""
    vault = TokenVault()
    tokenizer = Tokenizer(vault)
    
    session_id = "test-session-01"
    original_value = "9000000001"
    
    # Tokenize the value
    token = tokenizer.tokenize(original_value, session_id, entity_type="PHONE_NUMBER")
    
    # Verify the token format
    assert token.startswith("<") and token.endswith(">")
    assert token != original_value
    
    # Restore the token using the correct session ID
    restored_value = vault.retrieve(token, session_id)
    
    # Measure restoration correctness
    assert restored_value == original_value

def test_restoration_failure_wrong_session():
    """Test that tokens cannot be restored using a different session ID."""
    vault = TokenVault()
    tokenizer = Tokenizer(vault)
    
    session_1 = "session-01"
    session_2 = "session-02"
    original_value = "secret@example.com"
    
    token = tokenizer.tokenize(original_value, session_1, entity_type="EMAIL_ADDRESS")
    
    # Attempt to retrieve with the wrong session
    restored_value = vault.retrieve(token, session_2)
    
    # Measure unauthorized access denial
    assert restored_value is None
    stats = vault.get_stats()
    assert stats["cross_session_attempts"] == 1

def test_restoration_failure_invalid_token():
    """Test that an invalid token returns None during restoration."""
    vault = TokenVault()
    tokenizer = Tokenizer(vault)
    
    # Attempt to retrieve a non-existent token
    restored_value = vault.retrieve("[TOK_INVALID_123456]", "session-01")
    
    assert restored_value is None
    stats = vault.get_stats()
    assert stats["unknown_tokens"] == 1

def test_restoration_failure_expired_token():
    """Test that expired tokens are rejected during restoration."""
    vault = TokenVault(default_ttl_seconds=0) # Instant expiry
    tokenizer = Tokenizer(vault)
    
    session_id = "session-ttl-test"
    original_value = "sensitive_data"
    
    token = tokenizer.tokenize(original_value, session_id, ttl=0)
    time.sleep(0.01) # Ensure time passes
    
    restored_value = vault.retrieve(token, session_id)
    assert restored_value is None
    stats = vault.get_stats()
    assert stats["expired_tokens"] == 1
