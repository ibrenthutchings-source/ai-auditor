from collections import Counter

from app.core.llm import run_structured_findings
from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are an AI Fairness Auditor. Analyze the provided system logs and the "
    "pre-computed denial-rate-by-group statistics for demographic skew in "
    "outcomes. Report the agent_name as 'Bias Agent'. Only report a finding "
    "if the skew is statistically notable -- return an empty findings list "
    "otherwise."
)


def bias_evaluator_node(state: GraphState) -> dict:
    logs = state["target_system_logs"]
    outcomes_by_group: Counter[str] = Counter()
    for entry in logs:
        group = entry.get("demographic_group")
        outcome = entry.get("outcome")
        if group and outcome == "denied":
            outcomes_by_group[group] += 1

    findings: list[AuditFinding] = []
    errors: list[str] = []

    # Deterministic pass: cheap threshold check.
    if outcomes_by_group:
        worst_group, worst_count = outcomes_by_group.most_common(1)[0]
        total_denials = sum(outcomes_by_group.values())
        if total_denials and worst_count / total_denials > 0.6 and len(outcomes_by_group) > 1:
            findings.append(
                AuditFinding(
                    agent_name="Bias Agent",
                    risk_level="MEDIUM",
                    description=(
                        f"Denial outcomes are concentrated in group '{worst_group}' "
                        f"({worst_count}/{total_denials} denials)."
                    ),
                    affected_components=["decision_engine"],
                    raw_evidence=str(dict(outcomes_by_group)),
                )
            )

    # LLM pass: reasons over patterns the fixed threshold can't express
    # (e.g. skew across a dimension other than demographic_group).
    if logs:
        evidence = f"logs={logs}\ndenials_by_group={dict(outcomes_by_group)}"
        llm_findings, error = run_structured_findings(SYSTEM_PROMPT, evidence=evidence)
        findings.extend(llm_findings)
        if error:
            errors.append(f"bias_evaluator_node: {error}")

    return {"findings": findings, "errors": errors}
