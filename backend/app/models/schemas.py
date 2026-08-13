from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
FixType = Literal["CODE", "INFRASTRUCTURE", "SOP", "PROMPT"]


class AuditFinding(BaseModel):
    agent_name: str = Field(description="The name of the agent reporting (e.g., 'Bias Agent', 'Security Agent')")
    risk_level: RiskLevel = Field(description="Severity of the finding")
    description: str = Field(description="Detailed explanation of the issue found")
    affected_components: List[str] = Field(description="Which parts of the system are affected")
    raw_evidence: str = Field(description="Snippets of logs or prompts proving the issue")


class FindingsResult(BaseModel):
    """Wrapper so the LLM can return zero or more findings as one structured object."""

    findings: List[AuditFinding] = Field(default_factory=list)


class Recommendation(BaseModel):
    finding_reference: str = Field(description="Short summary of the finding this addresses")
    fix_type: FixType = Field(description="Category of remediation")
    prescriptive_action: str = Field(description="Exact steps to fix the issue")
    code_snippet: Optional[str] = Field(default=None, description="IaC or Python code, if applicable")


class SankeyLink(BaseModel):
    """One source -> target -> value edge for a Sankey/flow diagram."""

    source: str
    target: str
    value: float


class AuditState(BaseModel):
    """The shared state passed through the LangGraph workflow."""

    audit_id: str
    target_system_logs: List[Dict[str, Any]]
    regulatory_context: str
    findings: List[AuditFinding] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    current_status: str = "INITIALIZED"
    errors: List[str] = Field(default_factory=list)
    sankey_links: List[SankeyLink] = Field(default_factory=list)
