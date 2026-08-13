from app.graph.workflow import audit_graph


def _initial_state(logs, regulatory_context="default"):
    return {
        "audit_id": "test",
        "target_system_logs": logs,
        "regulatory_context": regulatory_context,
        "findings": [],
        "synthesized_findings": [],
        "recommendations": [],
        "current_status": "INITIALIZED",
        "errors": [],
    }


def test_graph_runs_end_to_end_with_no_llm_findings(stub_llm):
    stub_llm(['{"findings": []}'])
    logs = [
        {"component": "chat_widget", "content": "contact me at a@b.com"},
        {"demographic_group": "A", "outcome": "denied"},
        {"demographic_group": "A", "outcome": "denied"},
        {"demographic_group": "B", "outcome": "denied"},
        {"event": "human_review", "decision": "approved", "time_to_approve_seconds": 0.5},
    ]
    result = audit_graph.invoke(_initial_state(logs))
    assert result["current_status"] == "COMPLETE"
    # The stub LLM returns an empty findings list for every call, including
    # synthesis_node's near-duplicate merge pass -- that correctly triggers
    # its "don't trust an empty merge" fallback, which logs a warning but
    # must not drop the deterministically-derived findings.
    assert all("keeping exact-dedup result" in e for e in result["errors"])
    agent_names = {f.agent_name for f in result["synthesized_findings"]}
    assert "Security Agent" in agent_names
    assert "Bias Agent" in agent_names
    assert "HITL Agent" in agent_names
    assert len(result["recommendations"]) >= 1


def test_graph_handles_empty_logs():
    result = audit_graph.invoke(_initial_state([]))
    # intake_node's FAILED status must survive the rest of the graph --
    # recommender_node must not stomp it with COMPLETE.
    assert result["current_status"] == "FAILED"
    assert result["errors"]
    assert result["recommendations"] == []
