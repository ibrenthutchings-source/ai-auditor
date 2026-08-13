from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.graph.workflow import audit_graph
from app.models.schemas import AuditState
from app.telemetry.sankey import build_sankey_links

app = FastAPI(title="AI Auditor Council")

# Local dev only: the Next.js frontend runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    sankey_links = build_sankey_links(
        result["regulatory_context"],
        result["synthesized_findings"],
        result["recommendations"],
    )
    return AuditState(
        audit_id=result["audit_id"],
        target_system_logs=result["target_system_logs"],
        regulatory_context=result["regulatory_context"],
        findings=result["synthesized_findings"],
        recommendations=result["recommendations"],
        current_status=result["current_status"],
        errors=result["errors"],
        sankey_links=sankey_links,
    )
