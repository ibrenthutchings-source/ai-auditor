from app.core.llm import run_structured_findings
from app.graph.state import GraphState
from app.models.schemas import AuditFinding

SYSTEM_PROMPT = (
    "You are the Lead Auditor. You are given a JSON list of findings already "
    "submitted by the Bias, Security, and HITL agents (exact duplicates "
    "already removed). Some of these may describe the SAME underlying issue "
    "IN THE SAME agent_name, phrased differently -- merge only those into a "
    "single finding, keeping the highest risk_level among the merged group, "
    "the union of affected_components, and combining raw_evidence. "
    "NEVER merge findings that have different agent_name values, even if "
    "they describe related or causally-connected events -- each agent "
    "evaluates a distinct governance dimension (bias, security, HITL "
    "compliance) and must remain separately attributable in the audit "
    "trail. A merged finding's agent_name must always be a single "
    "unchanged agent_name from its inputs, never a combination. Findings "
    "that are genuinely distinct issues, or that come from different "
    "agents, must be returned unchanged and separately. Return the "
    "complete final list of findings -- never drop a distinct issue, only "
    "merge true same-agent duplicates."
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
        original_agent_names = {f.agent_name for f in deduped}
        evidence = "\n".join(f.model_dump_json() for f in deduped)
        merged_findings, error = run_structured_findings(SYSTEM_PROMPT, evidence=evidence)
        if error:
            errors.append(f"synthesis_node: {error}")
        elif not merged_findings:
            errors.append("synthesis_node: LLM merge returned no findings, keeping exact-dedup result")
        elif len(merged_findings) > len(deduped):
            errors.append("synthesis_node: LLM merge grew the findings list, keeping exact-dedup result")
        elif any(f.agent_name not in original_agent_names for f in merged_findings):
            # The prompt forbids cross-agent merges (each agent covers a
            # distinct governance dimension and must stay separately
            # attributable), but LLM output isn't trusted to always obey
            # instructions -- verify in code, not just in the prompt.
            errors.append(
                "synthesis_node: LLM merge introduced an agent_name not present in the "
                "original findings (likely an illegal cross-agent merge), keeping exact-dedup result"
            )
        else:
            synthesized = merged_findings

    status = "FINDINGS_SYNTHESIZED" if synthesized else "NO_FINDINGS"
    if state.get("current_status") == "FAILED":
        status = "FAILED"
    return {"synthesized_findings": synthesized, "current_status": status, "errors": errors}
