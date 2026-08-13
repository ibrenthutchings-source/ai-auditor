from app.core.llm import run_structured_findings
from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are the Lead Auditor. You are given a JSON list of findings already "
    "submitted by the Bias, Security, and HITL agents (exact duplicates "
    "already removed). Some of these may describe the SAME underlying issue "
    "in different words -- merge those into a single finding, keeping the "
    "highest risk_level among the merged group, the union of "
    "affected_components, and combining raw_evidence. Findings that are "
    "genuinely distinct issues must be returned unchanged and separately. "
    "Return the complete final list of findings -- never drop a distinct "
    "issue, only merge true duplicates."
)

# Bound the synthesis LLM call to a sane batch size; a pathological number
# of findings (e.g. a bug elsewhere spamming the findings list) shouldn't
# turn into an unbounded prompt.
MAX_FINDINGS_FOR_LLM_MERGE = 25


def synthesis_node(state: GraphState) -> dict:
    seen: set[tuple[str, str]] = set()
    deduped: list[AuditFinding] = []
    for finding in state["findings"]:
        key = (finding.agent_name, finding.description)
        if key not in seen:
            seen.add(key)
            deduped.append(finding)

    errors: list[str] = []
    synthesized = deduped

    # Exact-match dedup above is fast and reliable but only catches
    # identical (agent, description) pairs. A second pass asks the LLM to
    # merge near-duplicates phrased differently (e.g. an LLM-derived
    # finding restating a deterministic regex finding). This is
    # best-effort: any failure or suspicious output falls back to the
    # exact-dedup result rather than risking silently dropping a finding.
    if 1 < len(deduped) <= MAX_FINDINGS_FOR_LLM_MERGE:
        evidence = "\n".join(f.model_dump_json() for f in deduped)
        merged_findings, error = run_structured_findings(SYSTEM_PROMPT, evidence=evidence)
        if error:
            errors.append(f"synthesis_node: {error}")
        elif merged_findings and len(merged_findings) <= len(deduped):
            synthesized = merged_findings
        elif not merged_findings:
            errors.append("synthesis_node: LLM merge returned no findings, keeping exact-dedup result")

    status = "FINDINGS_SYNTHESIZED" if synthesized else "NO_FINDINGS"
    if state.get("current_status") == "FAILED":
        status = "FAILED"
    return {"synthesized_findings": synthesized, "current_status": status, "errors": errors}
