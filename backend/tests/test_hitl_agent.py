from app.agents.hitl_agent import calculate_time_to_approve, hitl_evaluator_node


def test_calculate_time_to_approve_averages():
    entries = [{"time_to_approve_seconds": 1.0}, {"time_to_approve_seconds": 3.0}]
    assert calculate_time_to_approve(entries) == 2.0


def test_calculate_time_to_approve_none_when_no_data():
    assert calculate_time_to_approve([{"decision": "approved"}]) is None


def test_hitl_flags_rubber_stamping(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "regulatory_context": "default",
        "target_system_logs": [
            {"event": "human_review", "decision": "approved", "time_to_approve_seconds": 0.5},
            {"event": "human_review", "decision": "approved", "time_to_approve_seconds": 0.8},
        ],
    }
    result = hitl_evaluator_node(state)
    critical = [f for f in result["findings"] if f.risk_level == "CRITICAL"]
    assert len(critical) == 1
    assert result["errors"] == []


def test_hitl_no_flag_when_review_is_slow(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "regulatory_context": "default",
        "target_system_logs": [
            {"event": "human_review", "decision": "approved", "time_to_approve_seconds": 30.0},
        ],
    }
    result = hitl_evaluator_node(state)
    assert not any(f.risk_level == "CRITICAL" for f in result["findings"])


def test_hitl_unknown_regulatory_context_is_surfaced(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "regulatory_context": "nonexistent-context",
        "target_system_logs": [
            {"event": "human_review", "decision": "approved", "time_to_approve_seconds": 0.5},
        ],
    }
    result = hitl_evaluator_node(state)
    assert any("nonexistent-context" in e for e in result["errors"])
