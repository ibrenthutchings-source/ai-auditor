from fastapi import FastAPI

from app.graph.workflow import audit_graph
from app.models.schemas import AuditState

app = FastAPI(title="AI Auditor Council")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/audit", response_model=AuditState)
def run_audit(payload: AuditState) -> AuditState:
    result = audit_graph.invoke(
        {
            "audit_id": payload.audit_id,
            "target_system_logs": payload.target_system_logs,
            "regulatory_context": payload.regulatory_context,
            "findings": [],
            "synthesized_findings": [],
            "recommendations": [],
            "current_status": "INITIALIZED",
            "errors": [],
        }
    )
    return AuditState(
        audit_id=result["audit_id"],
        target_system_logs=result["target_system_logs"],
        regulatory_context=result["regulatory_context"],
        findings=result["synthesized_findings"],
        recommendations=result["recommendations"],
        current_status=result["current_status"],
        errors=result["errors"],
    )
