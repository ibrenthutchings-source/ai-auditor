import operator
from typing import Annotated, Any, Dict, List, TypedDict

from app.models.schemas import AuditFinding, Recommendation


class GraphState(TypedDict):
    """LangGraph working state.

    `findings` and `errors` use an `operator.add` reducer because the
    bias/security/HITL evaluator nodes run in parallel and each append
    to the same key -- without a reducer, concurrent writes to one key
    raise an InvalidUpdateError.
    """

    audit_id: str
    target_system_logs: List[Dict[str, Any]]
    regulatory_context: str
    findings: Annotated[List[AuditFinding], operator.add]
    # Plain-replace (no reducer): written once by synthesis_node after the
    # parallel evaluators have finished appending to `findings`.
    synthesized_findings: List[AuditFinding]
    recommendations: List[Recommendation]
    current_status: str
    errors: Annotated[List[str], operator.add]
