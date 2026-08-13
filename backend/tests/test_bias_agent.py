from app.agents.bias_agent import bias_evaluator_node


def test_bias_evaluator_flags_concentrated_denials(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "target_system_logs": [
            {"demographic_group": "A", "outcome": "denied"},
            {"demographic_group": "A", "outcome": "denied"},
            {"demographic_group": "B", "outcome": "denied"},
        ]
    }
    result = bias_evaluator_node(state)
    assert len(result["findings"]) == 1
    assert result["findings"][0].agent_name == "Bias Agent"
    assert "'A'" in result["findings"][0].description


def test_bias_evaluator_no_finding_when_evenly_distributed(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "target_system_logs": [
            {"demographic_group": "A", "outcome": "denied"},
            {"demographic_group": "B", "outcome": "denied"},
        ]
    }
    result = bias_evaluator_node(state)
    assert result["findings"] == []


def test_bias_evaluator_no_finding_single_group(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "target_system_logs": [
            {"demographic_group": "A", "outcome": "denied"},
            {"demographic_group": "A", "outcome": "denied"},
        ]
    }
    result = bias_evaluator_node(state)
    assert result["findings"] == []
