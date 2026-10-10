from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import json
import csv
import io

from backend.simulated_agent import SimulatedAgent
from backend.detector import PIIDetector
from backend.policy_engine import PolicyEngine
from backend.tokenizer import Tokenizer
from backend.token_vault import TokenVault
from backend.tools.mock_tools import MockToolRegistry
from backend.audit_logger import AuditLogger
from backend.performance import PerformanceTracker
from backend.gateway import Gateway
from backend.evaluation import EvaluationRunner
from backend.database import DatabaseManager

app = FastAPI(title="PII Firewall for AI Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
policies_file = os.path.join(DATA_DIR, "synthetic_tool_policies.json")

agent = SimulatedAgent()
detector = PIIDetector()
policy_engine = PolicyEngine(policies_file)
vault = TokenVault(default_ttl_seconds=300)
tokenizer = Tokenizer(vault)
tool_registry = MockToolRegistry()
audit_logger = AuditLogger(max_logs=500)
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

evaluation_runner = EvaluationRunner(gateway, vault, tokenizer, perf_tracker)

class AgentRequest(BaseModel):
    user_request: str
    session_id: Optional[str] = "session_default"
    action_override: Optional[str] = None

class DirectToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = "session_default"
    action_override: Optional[str] = None

class RestorationRequest(BaseModel):
    token: str
    session_id: str

@app.get("/")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "PII Firewall for AI Agents",
        "gemini": detector.gemini_status,
    }

@app.get("/api/gemini/status")
def gemini_status():
    """Returns current Gemini API status including quota info."""
    return detector.gemini_status


@app.post("/api/agent/run")
def run_agent(req: AgentRequest):
    if not req.user_request.strip():
        raise HTTPException(status_code=400, detail="User request prompt cannot be empty.")
    
    tool_request = agent.handle_request(req.user_request, req.session_id)
    gateway_result = gateway.process_request(
        tool_name=tool_request["tool_name"],
        arguments=tool_request["arguments"],
        session_id=tool_request["session_id"],
        user_prompt_preview=req.user_request,
        action_override=req.action_override
    )
    return {
        "user_request": req.user_request,
        "tool_request": tool_request,
        "gateway_result": gateway_result
    }

@app.post("/api/gateway/process")
def process_direct_tool(req: DirectToolRequest):
    return gateway.process_request(
        tool_name=req.tool_name,
        arguments=req.arguments,
        session_id=req.session_id,
        user_prompt_preview=f"Direct invocation of {req.tool_name}",
        action_override=req.action_override
    )

@app.post("/api/evaluation/run")
def run_evaluation():
    results = evaluation_runner.run_evaluation()
    run_id = f"RUN-{int(os.times().elapsed * 1000)}"
    db_manager.save_evaluation_run(run_id, results)
    return results

@app.post("/api/evaluation/reset")
def reset_evaluation():
    evaluation_runner.reset()
    db_manager.clear_all()
    return {
        "status": "reset",
        "message": "Evaluation test data, audit logs, token vault, database records, and performance metrics successfully cleared."
    }

@app.get("/api/evaluation/export")
def export_evaluation(format: str = Query("json", pattern="^(json|csv)$")):
    results = evaluation_runner.latest_results
    if not results:
        raise HTTPException(status_code=404, detail="No evaluation results found. Run evaluation benchmark first.")
    
    if format == "json":
        return Response(
            content=json.dumps(results, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=pii_firewall_evaluation.json"}
        )
    elif format == "csv":
        test_cases = results.get("detection_analytics", {}).get("test_cases", [])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Test Case ID", "Category", "Tool Name", "Expected PII Count", "Detected PII Count", "Expected Action", "Actual Decision", "Passed"])
        for tc in test_cases:
            writer.writerow([
                tc.get("id"), tc.get("category"), tc.get("tool_name"),
                tc.get("expected_pii_count"), tc.get("detected_pii_count"),
                tc.get("expected_action"), tc.get("actual_decision"), tc.get("passed")
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pii_firewall_evaluation.csv"}
        )

@app.get("/api/dashboard/metrics")
def get_dashboard_metrics():
    if evaluation_runner.latest_results:
        return evaluation_runner.latest_results
    
    db_logs = db_manager.get_logs(limit=200)
    total_logs = len(db_logs) if db_logs else len(audit_logger.logs)
    logs_to_use = db_logs if db_logs else audit_logger.logs

    if total_logs == 0:
        return {
            "has_data": False,
            "message": "No test results yet. Run evaluation or execute simulation requests to populate dashboard metrics."
        }

    allowed = sum(1 for l in logs_to_use if l["policy_decision"] == "ALLOW")
    redacted = sum(1 for l in logs_to_use if l["policy_decision"] == "REDACT" or l.get("sanitization_action") == "redact")
    tokenized = sum(1 for l in logs_to_use if l["policy_decision"] == "TOKENIZE" or l.get("sanitization_action") == "tokenize")
    blocked = sum(1 for l in logs_to_use if l["policy_decision"] == "BLOCK")

    total_pii = sum(len(l["pii_detected"]) for l in logs_to_use)
    
    perf = perf_tracker.get_summary_stats()
    vault_stats = vault.get_stats()

    return {
        "has_data": True,
        "total_requests": total_logs,
        "requests_summary": {
            "allowed": allowed,
            "redacted": redacted,
            "tokenized": tokenized,
            "sanitized": redacted + tokenized,
            "blocked": blocked
        },
        "detection_analytics": {
            "total_pii_detected": total_pii
        },
        "restoration_analytics": vault_stats,
        "performance_analytics": perf
    }

@app.get("/api/dashboard/logs")
def get_logs(
    limit: int = Query(50, ge=1, le=200),
    tool_name: Optional[str] = None,
    pii_type: Optional[str] = None,
    outcome: Optional[str] = None
):
    db_logs = db_manager.get_logs(limit=limit, tool_name=tool_name, outcome=outcome)
    if db_logs:
        return db_logs
    return audit_logger.get_logs(limit=limit, tool_name=tool_name, pii_type=pii_type, outcome=outcome)

@app.get("/api/dashboard/policies")
def get_policies():
    return policy_engine.policies

@app.post("/api/restoration/restore")
def restore_token(req: RestorationRequest):
    res = vault.restore_token(req.token, req.session_id)
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
