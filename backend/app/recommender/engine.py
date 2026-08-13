import json
from functools import lru_cache
from pathlib import Path

from app.graph.state import GraphState
from app.models.schemas import AuditFinding, Recommendation

_FIXES_PATH = Path(__file__).parent / "fixes.json"


@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    with _FIXES_PATH.open() as f:
        return json.load(f)


def _match_rule(finding: AuditFinding, rules: list[dict]) -> dict | None:
    text = finding.description.lower()
    for rule in rules:
        if any(tag in text for tag in rule["tags"]):
            return rule
    return None


def recommender_node(state: GraphState) -> dict:
    rules = _load_rules()

    # Group findings by matched rule so one fix knowledge-base entry
    # produces exactly one Recommendation, even if several findings
    # (e.g. an LLM-derived finding and a deterministic regex finding)
    # independently flag the same underlying issue.
    matches: dict[str, tuple[dict, list[AuditFinding]]] = {}
    for finding in state["synthesized_findings"]:
        rule = _match_rule(finding, rules)
        if rule is None:
            continue
        rule_id = rule["id"]
        if rule_id not in matches:
            matches[rule_id] = (rule, [])
        matches[rule_id][1].append(finding)

    recommendations = [
        Recommendation(
            finding_reference="; ".join(f.description for f in findings),
            fix_type=rule["fix_type"],
            prescriptive_action=rule["prescriptive_action"],
            code_snippet=rule["code_snippet"],
        )
        for rule, findings in matches.values()
    ]

    return {"recommendations": recommendations, "current_status": "COMPLETE"}
