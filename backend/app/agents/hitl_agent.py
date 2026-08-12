from app.core.config import settings
from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are an AI Governance Auditor specializing in Human-in-the-Loop "
    "compliance. Analyze the user interaction logs. Calculate the human "
    "override rate and time-to-approve. If both fall below the configured "
    "thresholds for the current regulatory context, flag this as "
    "'Automation Bias / Rubber-Stamping'."
)


def calculate_time_to_approve(entries: list[dict]) -> float | None:
    times = [e["time_to_approve_seconds"] for e in entries if "time_to_approve_seconds" in e]
    if not times:
        return None
    return sum(times) / len(times)


def hitl_evaluator_node(state: GraphState) -> dict:
    approvals = [e for e in state["target_system_logs"] if e.get("event") == "human_review"]
    if not approvals:
        return {"findings": []}

    approved = [e for e in approvals if e.get("decision") == "approved"]
    approval_rate = len(approved) / len(approvals)
    avg_time = calculate_time_to_approve(approvals)

    max_rate, max_seconds = settings.HITL_RUBBER_STAMP_THRESHOLDS.get(
        state["regulatory_context"], settings.HITL_RUBBER_STAMP_THRESHOLDS["default"]
    )

    findings: list[AuditFinding] = []
    if avg_time is not None and approval_rate >= max_rate and avg_time <= max_seconds:
        findings.append(
            AuditFinding(
                agent_name="HITL Agent",
                risk_level="CRITICAL",
                description=(
                    f"Automation Bias / Rubber-Stamping suspected: {approval_rate:.0%} "
                    f"approval rate with average time-to-approve of {avg_time:.1f}s."
                ),
                affected_components=["human_review_queue"],
                raw_evidence=f"{len(approved)}/{len(approvals)} approved, avg_time={avg_time:.2f}s",
            )
        )
    return {"findings": findings}
