from app.agents.security_agent import regex_pii_scanner, security_evaluator_node


def test_regex_pii_scanner_detects_email():
    assert regex_pii_scanner("contact me at jane.doe@example.com") == ["email"]


def test_regex_pii_scanner_detects_ssn():
    assert regex_pii_scanner("SSN: 123-45-6789") == ["ssn"]


def test_regex_pii_scanner_no_hit():
    assert regex_pii_scanner("nothing sensitive here") == []


def test_security_evaluator_node_flags_pii_deterministically(stub_llm):
    stub_llm(['{"findings": []}'])
    state = {
        "target_system_logs": [
            {"component": "chat_widget", "content": "email me at a@b.com"},
        ]
    }
    result = security_evaluator_node(state)
    assert len(result["findings"]) == 1
    assert result["findings"][0].risk_level == "HIGH"
    assert result["errors"] == []


def test_security_evaluator_node_reports_llm_error_without_raising(stub_llm):
    stub_llm(["not valid json"])
    state = {"target_system_logs": [{"component": "chat_widget", "content": "hello"}]}
    result = security_evaluator_node(state)
    assert result["errors"]
    assert "security_evaluator_node" in result["errors"][0]
