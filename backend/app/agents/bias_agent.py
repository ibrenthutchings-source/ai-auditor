from collections import Counter

from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are an AI Fairness Auditor. Analyze the provided system logs for "
    "demographic skew in outcomes across groups. If a statistically notable "
    "skew is found, output a structured AuditFinding."
)


def bias_evaluator_node(state: GraphState) -> dict:
    outcomes_by_group: Counter[str] = Counter()
    for entry in state["target_system_logs"]:
        group = entry.get("demographic_group")
        outcome = entry.get("outcome")
        if group and outcome == "denied":
            outcomes_by_group[group] += 1

    findings: list[AuditFinding] = []
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
    return {"findings": findings}
