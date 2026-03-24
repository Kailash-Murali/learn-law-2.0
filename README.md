# Constitutional Law Research Agent System

A sophisticated multi-agent system for Indian constitutional law research using Groq LLM with custom tool calling, Indian Kanoon API integration, Springer Nature academic search, and four XAI (Explainable AI) pipelines. Served via a FastAPI backend and a Next.js frontend.

## Table of Contents

- System Overview
- Features
- Installation
- Usage
- System Architecture
- XAI Logic Routing
- Configuration
- API Endpoints
- Troubleshooting
- Legal Disclaimer
- Contributing
- License

---

## System Overview

This system consists of six specialised agents and four XAI services working together:

### Agents

| Agent                    | File                              | Purpose                                                                  |
| ------------------------ | --------------------------------- | ------------------------------------------------------------------------ |
| **UI Agent**             | `agents/ui_agent.py`              | Parses natural language queries into structured JSON research parameters |
| **Research Agent**       | `agents/research_agent.py`        | Collects legal data from Indian Kanoon, Springer Nature, and Groq LLM   |
| **XAI Validation Agent** | `agents/xai_validation_agent.py` | Anti-hallucination: citation verification, bad-law detection, risk score |
| **Documentation Agent**  | `agents/documentation_agent.py`  | Generates structured legal analysis, executive summaries, and reports    |
| **Drafting Agent**       | `agents/drafting_agent.py`       | Produces legal drafts (petitions, opinions, notices, etc.)               |
| **Springer Agent**       | `springer_agent.py`              | Springer Nature Meta + OpenAccess API integration for academic papers    |

### XAI Services (local, no LLM calls)

| Service                   | File                                  | Purpose                                                        |
| ------------------------- | ------------------------------------- | -------------------------------------------------------------- |
| **SHAP Confidence**       | `agents/shap_service.py`             | SHAP-based feature attribution for bad-law confidence scores   |
| **DiCE Counterfactuals**  | `agents/dice_service.py`             | Diverse counterfactual explanations for classification queries |
| **Attention Proxy**       | `agents/attention_proxy_service.py`  | TF-IDF cosine similarity for source-sentence attribution       |

### Architecture

```
Next.js Frontend (learn-law/)
        │
        ▼  HTTP
FastAPI Server (api_server.py)
        │
        ├─► ResearchAdapter (cli_adapter.py)
        │         │
        │         ▼
        │   Coordinator (autogen_agent.py)
        │     ├─► UIAgent ──► parse query
        │     ├─► ResearchAgent ──► Groq LLM + Indian Kanoon + Springer
        │     ├─► XAIValidationAgent ──► citation verification + bad-law detection
        │     ├─► DocumentationAgent / DraftingAgent ──► final output
        │     └─► UIFormatter ──► structured JSON payload (incl. query_type routing)
        │
        └─► XAI Endpoints (local scikit-learn services)
              ├─► /api/xai/confidence-breakdown  (SHAP)
              ├─► /api/xai/counterfactuals        (DiCE — classification queries only)
              └─► /api/xai/attention-map           (TF-IDF attention proxy)
```

---

## Features

- **Groq LLM Backend**: Fast inference via Groq API for all agent reasoning
- **Comprehensive Research**: Case law, statutes, pending cases, and scholarly articles
- **Real API Integrations**:
  - [Indian Kanoon](https://indiankanoon.org/) for Indian case law, statutes, and pending cases
  - [Springer Nature](https://dev.springernature.com/) for academic legal articles
- **Three XAI Pipelines**: SHAP confidence breakdown, DiCE counterfactuals, attention-proxy source attribution
- **Query-Type Routing**: Classification queries trigger DiCE; advisory queries trigger attention map (see XAI Logic Routing)
- **Anti-Hallucination Validation**: Indian Kanoon cross-verification, bad-law detection, hallucination risk scoring
- **Professional Documentation**: Executive summaries, legal analysis, legal drafts, and PDF/DOCX export
- **User Feedback Loop**: Thumbs up/down + grievance input logged to `feedback_log.jsonl` for continuous improvement
- **Chain-of-Thought Traces**: Every agent logs reasoning steps viewable in the UI
- **Deterministic Controls**: Pinned prompts, zero-temperature LLM settings, normalised external queries

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ and pnpm
- Groq API key
- Indian Kanoon API token
- Springer Nature API keys (Meta and OpenAccess)

### Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd learn-law
pnpm install
```

### Environment Variables

```bash
export GROQ_API_KEY="your-groq-api-key"
export IK_API_TOKEN="your-indian-kanoon-token"
export SPRINGER_META_API_KEY="your-springer-meta-key"
export SPRINGER_OPENACCESS_API_KEY="your-springer-openaccess-key"
```

---

## Usage

### Start the Backend

```bash
python -m uvicorn api_server:app --port 8000
```

### Start the Frontend

```bash
cd learn-law
pnpm dev
```

Then open [http://localhost:3000](http://localhost:3000).

### Example Queries

**Classification** (triggers DiCE counterfactuals):
- "Is Section 66A of the IT Act still valid?"
- "What is the current status of Section 124A IPC?"

**Advisory** (triggers attention-map source attribution):
- "My client has a property dispute — what compensation rules apply?"
- "How should I advise on arbitration under the 1996 Act?"

---

## System Architecture

### Key Components

| Component           | File                    | Description                                                    |
| ------------------- | ----------------------- | -------------------------------------------------------------- |
| `FastAPI Server`    | `api_server.py`         | HTTP bridge between Next.js frontend and Python backend        |
| `ResearchAdapter`   | `cli_adapter.py`        | Adapter pattern isolating AutoGen system for API/CLI use       |
| `Coordinator`       | `autogen_agent.py`      | Orchestrates the multi-agent workflow end to end               |
| `UIFormatter`       | `autogen_agent.py`      | Deterministic transformer: raw result → frontend JSON payload  |
| `Config`            | `config.py`             | Centralised configuration for API keys and agent settings      |
| Custom Exceptions   | `exceptions.py`         | Hierarchy of custom exceptions for error handling              |

---

## XAI Logic Routing

The system classifies every query as **classification** or **advisory** and routes to the appropriate XAI tool:

### Classification Queries

Pattern: *"Is this law still valid?"*, *"Was Section X struck down?"*, *"Current status of…"*

- **DiCE counterfactuals** are generated with dynamically extracted features (year, court level, fundamental rights article, etc.)
- The contrastive panel shows a table: *"If the year was 2015 instead of 1983 → Predicted Outcome: Upheld"*

### Advisory / Generative Queries

Pattern: *"My client has a property dispute…"*, *"How should I advise on…"*

- DiCE is **hidden** (no binary outcome to flip)
- **Attention Map** is highlighted — click any sentence in the answer to see which source documents it was drawn from
- **Source Validation** shows exactly where the LLM pulled compensation and arbitration rules from

### Other XAI Features (always available)

- **SHAP Confidence Breakdown**: Shown in the bad-law cards — explains *why* a law was flagged as struck down
- **Surrogate Decision Tree**: Shown in Chain-of-Thought panel — visualises the AI's grounding logic as a decision tree
- **Chain-of-Thought Traces**: Every agent's reasoning steps are expandable in the CoT panel

---

## Configuration

All configuration is centralised in `config.py`:

```python
class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    IK_API_TOKEN = os.getenv("IK_API_TOKEN", "")
    SPRINGER_META_API_KEY = os.getenv("SPRINGER_META_API_KEY", "")
    SPRINGER_OPENACCESS_API_KEY = os.getenv("SPRINGER_OPENACCESS_API_KEY", "")
```

---

## API Endpoints

### Core

| Method | Path              | Description                     |
| ------ | ----------------- | ------------------------------- |
| GET    | `/api/health`     | System health + missing keys    |
| POST   | `/api/research`   | Full research pipeline          |
| POST   | `/api/parse`      | Parse query without research    |
| GET    | `/api/download`   | Download generated PDF/DOCX     |
| POST   | `/api/feedback`   | Submit user feedback            |

### XAI

| Method | Path                             | Description                          |
| ------ | -------------------------------- | ------------------------------------ |
| POST   | `/api/xai/confidence-breakdown`  | SHAP feature attribution             |
| POST   | `/api/xai/counterfactuals`       | DiCE diverse counterfactuals         |
| POST   | `/api/xai/attention-map`         | TF-IDF sentence-source attribution   |

---

## Troubleshooting

| Issue                                  | Solution                                                               |
| -------------------------------------- | ---------------------------------------------------------------------- |
| "API key not found"                    | Ensure `GROQ_API_KEY` is set in environment or `config.py`            |
| SHAP "size-1 array" error              | Fixed — the SHAP extraction now handles 3-D ndarray from SHAP ≥ 0.41  |
| DiCE fires with hardcoded features     | Fixed — features are now dynamically derived from the query context    |
| Indian Kanoon rate limit               | Reduce request frequency; add delays between searches                  |
| Springer empty results                 | Use simpler queries (2-3 keywords); check API plan constraints         |

---

## Project Structure

```
learn-law-2.0/
├── api_server.py               # FastAPI HTTP server (primary entry point)
├── cli_adapter.py              # Adapter pattern around AutoGen system
├── autogen_agent.py            # Multi-agent orchestrator + UIFormatter
├── springer_agent.py           # Springer Nature API agent
├── config.py                   # Centralised configuration
├── exceptions.py               # Custom exception hierarchy
├── requirements.txt            # Python dependencies
├── feedback_log.jsonl          # User feedback log
├── agents/
│   ├── base_agent.py           # Base agent class (Groq LLM wrapper)
│   ├── ui_agent.py             # Query parsing agent
│   ├── research_agent.py       # Legal research agent
│   ├── xai_validation_agent.py # Anti-hallucination validation
│   ├── documentation_agent.py  # Documentation generation
│   ├── drafting_agent.py       # Legal draft generation
│   ├── shap_service.py         # SHAP confidence breakdown
│   ├── dice_service.py         # DiCE counterfactual service
│   └── attention_proxy_service.py # TF-IDF attention proxy
└── learn-law/                  # Next.js frontend
    ├── app/
    │   ├── page.tsx            # Main chat interface
    │   └── api/                # Next.js API routes (proxy to FastAPI)
    └── components/
        └── learn-law/          # UI components (panels, highlighter, etc.)
```

---

## Legal Disclaimer

This system is for **research and educational purposes only**.

- Always verify legal information with qualified attorneys
- The system provides research assistance but **does not constitute legal advice**
- Case law and statutory information may not reflect the most recent updates
- AI-generated analysis should be reviewed by legal professionals

---

## Contributing

To extend this system:

1. **Add new data sources**: Implement new API methods in `agents/research_agent.py`
2. **Enhance documentation formats**: Modify prompts in `agents/documentation_agent.py`
3. **Add new XAI services**: Follow the pattern in `agents/shap_service.py` — local sklearn, no LLM
4. **Improve query processing**: Update Groq prompts in `agents/ui_agent.py`

### Code Style

- Use type hints for all function parameters and returns
- Document all public methods with docstrings
- Add trace logging for new agent interactions
- Handle exceptions using the custom exception hierarchy in `exceptions.py`

---

## License

This system is provided as-is for educational and research purposes.
