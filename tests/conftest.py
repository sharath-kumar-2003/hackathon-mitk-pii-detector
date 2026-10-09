import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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


@pytest.fixture(scope="module")
def detector():
    """Shared PIIDetector — expensive to initialize, reuse per module."""
    return PIIDetector()


@pytest.fixture
def vault():
    return TokenVault(default_ttl_seconds=300)


@pytest.fixture
def tokenizer(vault):
    return Tokenizer(vault)


@pytest.fixture
def policy_engine():
    return PolicyEngine(POLICIES_FILE)


@pytest.fixture
def tool_registry():
    reg = MockToolRegistry()
    reg.clear_payload_history()
    return reg


@pytest.fixture
def audit_logger():
    return AuditLogger(max_logs=100)


@pytest.fixture
def perf_tracker():
    return PerformanceTracker()


@pytest.fixture
def gateway(detector, policy_engine, tokenizer, vault, tool_registry, audit_logger, perf_tracker):
    """Full Gateway instance with no DB (unit test isolation)."""
    return Gateway(
        detector=detector,
        policy_engine=policy_engine,
        tokenizer=tokenizer,
        token_vault=vault,
        tool_registry=tool_registry,
        audit_logger=audit_logger,
        perf_tracker=perf_tracker,
        db_manager=None
    )
