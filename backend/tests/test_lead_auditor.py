from app.agents.lead_auditor import synthesis_node
from app.models.schemas import AuditFinding


def _finding(agent_name, description, risk_level="HIGH"):
    return AuditFinding(
        agent_name=agent_name,
        risk_level=risk_level,
        description=description,
        affected_components=["x"],
        raw_evidence="",
    )


def test_exact_duplicates_are_deduped_without_llm_call(stub_llm):
    fake = stub_llm(["should not be called"])
    state = {"findings": [_finding("Security Agent", "same"), _finding("Security Agent", "same")]}
    result = synthesis_node(state)
    assert len(result["synthesized_findings"]) == 1
    assert result["current_status"] == "FINDINGS_SYNTHESIZED"


def test_near_duplicates_merged_via_llm(stub_llm):
    merged_json = (
        '{"findings": [{"agent_name": "Security Agent", "risk_level": "HIGH", '
        '"description": "merged description", "affected_components": ["x"], '
        '"raw_evidence": "merged"}]}'
    )
    stub_llm([merged_json])
    state = {
        "findings": [
            _finding("Security Agent", "PII exposure via email"),
            _finding("Security Agent", "raw email address found in logs"),
        ]
    }
    result = synthesis_node(state)
    assert len(result["synthesized_findings"]) == 1
    assert result["synthesized_findings"][0].description == "merged description"


def test_cross_agent_merge_is_rejected_even_if_llm_attempts_it(stub_llm):
    # The LLM violates the "never merge across agents" instruction --
    # code-level validation must catch this and fall back rather than
    # trusting it.
    illegal_merge_json = (
        '{"findings": [{"agent_name": "HITL Agent, Security Agent", "risk_level": "CRITICAL", '
        '"description": "combined finding", "affected_components": ["x"], '
        '"raw_evidence": "combined"}]}'
    )
    stub_llm([illegal_merge_json])
    state = {
        "findings": [
            _finding("HITL Agent", "rubber stamping issue"),
            _finding("Security Agent", "prompt injection issue"),
        ]
    }
    result = synthesis_node(state)
    assert len(result["synthesized_findings"]) == 2
    assert {f.agent_name for f in result["synthesized_findings"]} == {"HITL Agent", "Security Agent"}
    assert any("cross-agent" in e for e in result["errors"])


def test_llm_merge_failure_falls_back_to_exact_dedup(stub_llm):
    stub_llm(["not valid json"])
    state = {
        "findings": [
            _finding("Security Agent", "finding one"),
            _finding("Security Agent", "finding two"),
        ]
    }
    result = synthesis_node(state)
    assert len(result["synthesized_findings"]) == 2
    assert result["errors"]


def test_no_findings_status():
    state = {"findings": []}
    result = synthesis_node(state)
    assert result["synthesized_findings"] == []
    assert result["current_status"] == "NO_FINDINGS"
