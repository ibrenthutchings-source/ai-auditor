from app.core.config import settings
from app.core.llm import run_structured_findings
from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are an AI Governance Auditor specializing in Human-in-the-Loop "
    "compliance. You are given pre-computed approval-rate and "
    "time-to-approve statistics plus the raw review logs. Look for "
    "qualitative rubber-stamping signals the numbers alone might miss "
    "(e.g. identical or boilerplate justification text across reviews). "
    "Report the agent_name as 'HITL Agent'. Do not re-flag the exact "
    "threshold breach already computed for you -- only report additional "
    "signal. Return an empty findings list if there is none."
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

    context = state["regulatory_context"]
    findings: list[AuditFinding] = []
    errors: list[str] = []

    if context in settings.HITL_RUBBER_STAMP_THRESHOLDS:
        max_rate, max_seconds = settings.HITL_RUBBER_STAMP_THRESHOLDS[context]
    else:
        # Silently falling back here would mean a caller who mistypes (or
        # hasn't yet configured) a regulatory_context gets evaluated
        # against unrelated default thresholds without ever knowing --
        # a false negative in a compliance product. Surface it instead.
        max_rate, max_seconds = settings.HITL_RUBBER_STAMP_THRESHOLDS["default"]
        errors.append(
            f"hitl_evaluator_node: unknown regulatory_context '{context}', "
            "falling back to 'default' HITL thresholds"
        )

    # Deterministic pass: the compliance-critical, precisely-thresholded check.
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

    # LLM pass: supplementary qualitative signal (see SYSTEM_PROMPT).
    evidence = (
        f"approval_rate={approval_rate:.2f}, avg_time_to_approve={avg_time}, "
        f"threshold_rate={max_rate}, threshold_seconds={max_seconds}\nlogs={approvals}"
    )
    llm_findings, error = run_structured_findings(SYSTEM_PROMPT, evidence=evidence)
    findings.extend(llm_findings)
    if error:
        errors.append(f"hitl_evaluator_node: {error}")

    return {"findings": findings, "errors": errors}
