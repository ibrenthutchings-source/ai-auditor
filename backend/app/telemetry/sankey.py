from collections import defaultdict
from typing import List

from app.models.schemas import AuditFinding, Recommendation, SankeyLink


def build_sankey_links(
    regulatory_context: str,
    findings: List[AuditFinding],
    recommendations: List[Recommendation],
) -> List[SankeyLink]:
    """Flow: regulatory_context -> agent -> risk_level -> fix_type (or "Unaddressed").

    Recommendations are matched back to findings by substring on
    `finding_reference`, since recommender_node joins the descriptions of
    every finding a single rule addressed into one reference string.
    """
    weights: dict[tuple[str, str], float] = defaultdict(float)

    for finding in findings:
        fix_type = next(
            (
                rec.fix_type
                for rec in recommendations
                if finding.description in rec.finding_reference
            ),
            "Unaddressed",
        )
        weights[(regulatory_context, finding.agent_name)] += 1
        weights[(finding.agent_name, finding.risk_level)] += 1
        weights[(finding.risk_level, fix_type)] += 1

    return [SankeyLink(source=s, target=t, value=v) for (s, t), v in weights.items()]
