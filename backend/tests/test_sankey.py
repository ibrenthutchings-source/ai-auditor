from app.models.schemas import AuditFinding, Recommendation
from app.telemetry.sankey import build_sankey_links


def test_build_sankey_links_matched_and_unaddressed():
    findings = [
        AuditFinding(
            agent_name="HITL Agent",
            risk_level="CRITICAL",
            description="Rubber-stamping suspected.",
            affected_components=["x"],
            raw_evidence="",
        ),
        AuditFinding(
            agent_name="Bias Agent",
            risk_level="MEDIUM",
            description="Unmatched novel finding.",
            affected_components=["x"],
            raw_evidence="",
        ),
    ]
    recommendations = [
        Recommendation(
            finding_reference="Rubber-stamping suspected.",
            fix_type="SOP",
            prescriptive_action="do something",
        )
    ]

    links = build_sankey_links("default", findings, recommendations)
    as_dict = {(l.source, l.target): l.value for l in links}

    assert as_dict[("default", "HITL Agent")] == 1.0
    assert as_dict[("HITL Agent", "CRITICAL")] == 1.0
    assert as_dict[("CRITICAL", "SOP")] == 1.0
    assert as_dict[("MEDIUM", "Unaddressed")] == 1.0


def test_build_sankey_links_aggregates_counts():
    findings = [
        AuditFinding(
            agent_name="Security Agent",
            risk_level="HIGH",
            description="a",
            affected_components=[],
            raw_evidence="",
        ),
        AuditFinding(
            agent_name="Security Agent",
            risk_level="HIGH",
            description="b",
            affected_components=[],
            raw_evidence="",
        ),
    ]
    links = build_sankey_links("default", findings, [])
    as_dict = {(l.source, l.target): l.value for l in links}
    assert as_dict[("default", "Security Agent")] == 2.0
    assert as_dict[("Security Agent", "HIGH")] == 2.0
