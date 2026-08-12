from app.graph.state import GraphState
from app.models.schemas import Recommendation

# Phase 1/3 stub: static rules keyed on finding content. Replace with a
# pgvector similarity lookup against a fix-knowledge-base once that's built.
_RULES = [
    (
        "Rubber-Stamping",
        Recommendation(
            finding_reference="Automation Bias / Rubber-Stamping",
            fix_type="SOP",
            prescriptive_action=(
                "Introduce mandatory review friction: require a minimum dwell "
                "time and a written justification field before an approval "
                "action is accepted for this decision category."
            ),
        ),
    ),
    (
        "PII exposure",
        Recommendation(
            finding_reference="PII exposure detected in logs",
            fix_type="CODE",
            prescriptive_action="Add a redaction filter to the logging pipeline before persistence.",
            code_snippet=(
                "import re\n"
                "PII_RE = re.compile(r'[\\w.+-]+@[\\w-]+\\.[\\w.-]+')\n"
                "def redact(text: str) -> str:\n"
                "    return PII_RE.sub('[REDACTED_EMAIL]', text)\n"
            ),
        ),
    ),
]


def recommender_node(state: GraphState) -> dict:
    recommendations: list[Recommendation] = []
    for finding in state["synthesized_findings"]:
        for keyword, template in _RULES:
            if keyword.lower() in finding.description.lower():
                rec = template.model_copy(update={"finding_reference": finding.description})
                recommendations.append(rec)
                break
    return {"recommendations": recommendations, "current_status": "COMPLETE"}
