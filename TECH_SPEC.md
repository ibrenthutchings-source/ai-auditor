# AI Auditor Council: Technical Implementation Specification

Target Audience: AI Coding Assistant (e.g., Claude Code, Cursor)
Goal: Build the MVP of an automated, multi-agent AI governance platform orchestrated via LangGraph, utilizing local LLMs.

## 1. System Architecture & Tech Stack

Backend / Orchestration: Python 3.11+, FastAPI, LangGraph (for state-machine agent routing), LangChain (for agent tool calling).

Local LLM Serving (Railway Private Service): Ollama running custom quantized Llama 3.1 8B models. The service is exposed only to the internal Railway network (private networking is configured via the Railway project/service settings, not a static `railway.toml` block — see Section 6).

Structured output reliability: Because an 8B quantized model will not reliably emit valid nested JSON on the first try, all agent output must go through `PydanticOutputParser` wrapped in LangChain's `OutputFixingParser` (retry-with-error-feedback), from Phase 1 onward — not bolted on later once real local-model output starts failing validation.

Database: PostgreSQL with pgvector. Scope for MVP: pgvector is used specifically for similarity retrieval of past findings inside `bias_evaluator_node` and `security_evaluator_node` (RAG over prior audit findings). If that retrieval isn't wired into the graph, pgvector should not be added as a dependency yet — don't carry an unused vector store.

Audit-log integrity: Because this is a compliance/governance product, its own audit trail must be append-only. `AuditFinding` and `AuditState` records are written once and never updated in place; corrections are new rows referencing the original by `audit_id`. Evaluate a hash-chain (each row includes a hash of the previous row) if tamper-evidence becomes a requirement — not required for MVP, but the append-only table design is.

Frontend (Future Phase): Next.js (React), TailwindCSS, React Flow (for Sankey/Graph visualizations), Recharts (for radar charts).

## 2. Recommended Repository Structure

```
ai-auditor-council/
├── infra/                   # Deployment & Infrastructure configs
│   ├── Dockerfile.ollama    # Custom Dockerfile for the Railway LLM service
│   ├── start-ollama.sh      # Entrypoint to pull models automatically
│   └── railway.toml         # Railway configuration file (build-time settings only)
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # Config, DB connections
│   │   ├── agents/          # LangChain/LangGraph agent definitions
│   │   │   ├── lead_auditor.py
│   │   │   ├── bias_agent.py
│   │   │   ├── security_agent.py
│   │   │   ├── hitl_agent.py
│   │   ├── graph/           # LangGraph state and workflow definition
│   │   │   ├── state.py
│   │   │   ├── workflow.py
│   │   ├── models/          # SQLAlchemy & Pydantic models
│   │   │   ├── schemas.py
│   │   ├── recommender/     # Logic for mapping findings to actionable fixes
│   │   └── utils/
│   ├── requirements.txt
│   └── main.py
└── frontend/                # (To be built in Phase 3)
```

## 3. Core Data Models (Pydantic Schemas)

AI Coder Instruction: Implement these schemas in `backend/app/models/schemas.py`. They are critical for ensuring structured outputs from the LLMs.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class AuditFinding(BaseModel):
    agent_name: str = Field(description="The name of the agent reporting (e.g., 'Bias Agent', 'Security Agent')")
    risk_level: str = Field(description="Severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    description: str = Field(description="Detailed explanation of the issue found")
    affected_components: List[str] = Field(description="Which parts of the system are affected")
    raw_evidence: str = Field(description="Snippets of logs or prompts proving the issue")

class Recommendation(BaseModel):
    finding_reference: str = Field(description="Short summary of the finding this addresses")
    fix_type: str = Field(description="'CODE', 'INFRASTRUCTURE', 'SOP', 'PROMPT'")
    prescriptive_action: str = Field(description="Exact steps to fix the issue")
    code_snippet: Optional[str] = Field(default=None, description="Provide IaC or Python code if applicable")

class AuditState(BaseModel):
    """The shared state passed through the LangGraph workflow."""
    audit_id: str
    target_system_logs: List[Dict[str, Any]]
    regulatory_context: str
    findings: List[AuditFinding] = []
    recommendations: List[Recommendation] = []
    current_status: str = "INITIALIZED"
    errors: List[str] = []
```

## 4. LangGraph Workflow Definition

AI Coder Instruction: Build a state graph in `backend/app/graph/workflow.py` using `langgraph.graph.StateGraph`.

Graph Nodes:

- `intake_node`: Validates input logs, sets up `AuditState`.
- `bias_evaluator_node`: Analyzes logs for demographic skew. Appends to `findings`.
- `security_evaluator_node`: Analyzes for prompt injection / data leakage. Appends to `findings`.
- `hitl_evaluator_node`: Checks human override rates (automation bias). Appends to `findings`.
- `synthesis_node` (Lead Auditor): Reviews all findings, resolves conflicts.
- `recommender_node`: Generates actionable `Recommendation` objects based on findings.

Edges / Routing:

- `START -> intake_node`
- `intake_node -> PARALLEL EXECUTION (bias_evaluator_node, security_evaluator_node, hitl_evaluator_node)`
- `(bias_evaluator_node, security_evaluator_node, hitl_evaluator_node) -> synthesis_node`
- `synthesis_node -> recommender_node`
- `recommender_node -> END`

## 5. Agent Prompts & Tools

### A. Security & Guardrail Agent

System Prompt: "You are an expert AI Security Auditor. Analyze the provided system logs. Look for attempts to bypass system prompts (jailbreaks), extraction of PII, or data exfiltration. If a risk is found, output a structured AuditFinding."

Tools/Functions:
- `regex_pii_scanner`: deterministic regex tool (not an LLM call) covering, at minimum: SSNs, credit card numbers (Luhn-validated), emails, phone numbers. Ship an explicit pattern list in `backend/app/agents/security_agent.py` rather than leaving detection entirely to the LLM.
- `search_cve_database`: MVP scope is a static local JSON file of known LLM/AI-system CVEs (prompt injection classes, known jailbreak patterns), not a live NVD API integration. Document this as a stub explicitly so it isn't mistaken for live threat intel.

### B. HITL/HOTL Agent

System Prompt: "You are an AI Governance Auditor specializing in Human-in-the-Loop compliance. Analyze the user interaction logs. Calculate the human override rate. If humans approve AI actions with an approval rate and median time-to-approve both below the configured thresholds for the current `regulatory_context`, flag this as 'Automation Bias / Rubber-Stamping'."

Thresholds (approval rate, time-to-approve) are **not hardcoded** — they are read from a per-`regulatory_context` config (e.g. `backend/app/core/config.py` or a config table), because a fixed "100% in <2s" rule produces false positives for task categories where near-instant approval is legitimate (e.g. low-risk auto-approved categories). Default thresholds ship for MVP but must be overridable per context.

Tools/Functions: `calculate_time_to_approve`, `query_user_cohort_history`

## 6. Railway Deployment & Local LLM Hosting

AI Coder Instruction: Use these configurations to deploy the private Ollama instance on Railway. This ensures the Llama 3.1 8B model runs securely inside the private network without public internet exposure.

Note: Persistent volumes and private networking are **not** configured via static keys in `railway.toml` — they are provisioned as actual Railway resources (via the Railway MCP tools / dashboard: `create_volume`, service networking settings). `railway.toml` here only carries build-time settings. Do not add placeholder `nixPkgs` entries — remove the `[phases.setup]` block entirely unless a real Nix package is needed.

File: `infra/Dockerfile.ollama`

```dockerfile
FROM ollama/ollama:latest

# Copy the startup script
COPY start-ollama.sh /start-ollama.sh
RUN chmod +x /start-ollama.sh

# Expose the default Ollama port
EXPOSE 11434

# Use the custom startup script to ensure the model is pulled
ENTRYPOINT ["/start-ollama.sh"]
```

File: `infra/start-ollama.sh`

```sh
#!/bin/sh
set -e

# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!

# Poll until the API is actually ready instead of a fixed sleep
echo "Waiting for Ollama service to start..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Pull the 8B Llama 3.1 model. This is a no-op if the layer already
# exists on the mounted volume, but still incurs a manifest check on
# every boot -- acceptable for MVP, revisit if boot latency matters.
echo "Pulling Llama 3.1 8B model..."
ollama pull llama3.1

# Keep the container alive with the actual server process
wait $OLLAMA_PID
```

File: `infra/railway.toml`

```toml
[build]
dockerfilePath = "infra/Dockerfile.ollama"

[deploy]
restartPolicyType = "ON_FAILURE"
```

Volume and private networking are provisioned separately (Railway MCP `create_volume` mounted at `/root/.ollama`, plus the service's default private networking address `<service>.railway.internal`) -- not declared here.

Backend Integration Note:
In your FastAPI/LangChain backend (`backend/app/core/config.py`), set the LLM Base URL to the internal Railway network address:
`OLLAMA_BASE_URL = "http://ollama.railway.internal:11434"`

## 7. Implementation Phases (Execution Plan for AI)

### Phase 1: Foundation & Dummy Graph

- Initialize the Python environment and install dependencies (`langchain`, `langgraph`, `fastapi`, `pydantic`).
- Create the Pydantic schemas in `schemas.py`.
- Build a basic LangGraph using standard OpenAI-compatible models just to verify the parallel node execution and state updating logic works, with output already routed through `PydanticOutputParser` (not deferred to Phase 2), so the parsing failure mode is caught early with a cheap, reliable model before local 8B inference is in the loop.

### Phase 2: Railway Infrastructure & Local Models

- Deploy the `infra/Dockerfile.ollama` service to Railway.
- Attach a persistent volume to the `/root/.ollama` path via Railway MCP / dashboard.
- Update the backend to use `ChatOllama` via the internal Railway URL.
- Add `OutputFixingParser` retry loop and tune prompts against the actual 8B model's failure modes (expect this to take iteration -- budget time for it).

### Phase 3: The Recommender Engine

- Implement the `recommender_node`.
- Connect it to a mock vector database (or local JSON file) containing known fixes (e.g., "If rubber-stamping detected -> output UI friction code").

### Phase 4: Telemetry & API Polish

- Format the final output of the FastAPI endpoint to include structure suitable for Sankey diagrams (source -> target -> value).
