from app.graph.state import GraphState

SYSTEM_PROMPT = (
    "You are the Lead Auditor. Review findings submitted by the Bias, "
    "Security, and HITL agents. De-duplicate overlapping findings and "
    "resolve any conflicting risk assessments of the same evidence."
)


def synthesis_node(state: GraphState) -> dict:
    seen: set[tuple[str, str]] = set()
    deduped = []
    for finding in state["findings"]:
        key = (finding.agent_name, finding.description)
        if key not in seen:
            seen.add(key)
            deduped.append(finding)

    status = "FINDINGS_SYNTHESIZED" if deduped else "NO_FINDINGS"
    return {"synthesized_findings": deduped, "current_status": status}
