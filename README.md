# Constitutional Law Research Agent System

A sophisticated multi-agent system for constitutional law research using Google's Gemini 2.5 Flash with custom tool calling, Indian Kanoon API integration, Springer Nature academic search, and SQLite database integration.

## Table of Contents

- System Overview
- Features
- Installation
- Usage
- System Architecture
- Database Schema
- Configuration
- Explainability & Tracing
- API Integrations
- Troubleshooting
- Legal Disclaimer
- Contributing
- License

---

## System Overview

This system consists of four specialized agents working together to provide comprehensive constitutional law research:

### Agents

| Agent                         | File                       | Purpose                                                                          |
| ----------------------------- | -------------------------- | -------------------------------------------------------------------------------- |
| **UI Agent**            | `ui_agent.py`            | Processes natural language user input and converts it to structured JSON queries |
| **Main Agent**          | `main_agent.py`          | Orchestrates the overall workflow and coordinates between agents                 |
| **Research Agent**      | `research_agent.py`      | Collects legal data from multiple sources (cases, statutes, articles)            |
| **Documentation Agent** | `documentation_agent.py` | Generates professional, structured documentation suitable for legal use          |

### Architecture

```
User Query → UI Agent → Main Agent → Research Agent → Documentation Agent → Final Report
              ↓           ↓            ↓                 ↓
           SQLite DB   Status Mgmt   Legal APIs      Structured JSON
                                    (Indian Kanoon,
                                     Springer Nature)
```

---

## Features

- **Natural Language Processing**: Convert plain English queries into structured legal research parameters using Gemini AI
- **Comprehensive Research**: Searches case law, statutes, pending cases, and scholarly articles
- **Real API Integrations**:
  - [Indian Kanoon](https://indiankanoon.org/) for Indian case law, statutes, and pending cases
  - [Springer Nature](https://dev.springernature.com/) for academic legal articles
- **Professional Documentation**: Generates executive summaries, legal analysis, and recommendations
- **Database Integration**: Persistent storage of all queries, research, and results
- **Explainability & Traceability**: Structured logs, artefact snapshots, and decision metadata for every agent
- **Deterministic Controls**: Pinned prompts, zero-temperature LLM settings, and normalized external queries ensure repeatable outcomes
- **Retry Logic**: Robust error handling with exponential backoff
- **Status Tracking**: Real-time status updates for long-running research tasks

---

## Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Indian Kanoon API token
- Springer Nature API keys (Meta and OpenAccess)

### Setup

1. **Clone or download the system files**
2. **Create and activate a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```
3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```
4. **Set up API keys**:

   **Option A: Environment Variables (Recommended)**

   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```

   **Option B: Edit `config.py`**

   ```python
   GEMINI_API_KEY = "your-actual-gemini-api-key-here"
   IK_API_TOKEN = "your-indian-kanoon-token"
   SPRINGER_META_API_KEY = "your-springer-meta-key"
   SPRINGER_OPENACCESS_API_KEY = "your-springer-openaccess-key"
   ```
5. **Initialize the database**:
   The database (`constitutional_law.db`) will be created automatically on first run.

---

## Usage

### Command Line Interface

The main entry point is `main.py`.

#### Interactive Mode

```bash
python main.py
```

This starts an interactive session where you can:

- Enter constitutional law research queries
- Check status of ongoing research
- View completed results
- Explore processing traces and artefacts

#### Single Query Mode

```bash
python main.py "What are the current limits on executive power?"
```

### CLI Commands

| Command                    | Description                                            |
| -------------------------- | ------------------------------------------------------ |
| `help`, `h`            | Show available commands                                |
| `status <request_id>`    | Check status of a research request                     |
| `result <request_id>`    | Display full research results                          |
| `trace <request_id>`     | Show detailed chronological trace of processing steps  |
| `artefacts <request_id>` | List all intermediate data snapshots for a request     |
| `artefact_content <id>`  | Show the full content of a specific artefact by its ID |
| `clear`                  | Clear the screen                                       |
| `quit`, `exit`, `q`  | Exit the program                                       |

### Example Queries

- "What is the current status of affirmative action in education?"
- "How has Article 21 been interpreted in recent Supreme Court cases?"
- "What are the constitutional limits on presidential emergency powers?"
- "How do state religious freedom laws interact with federal civil rights protections?"

### Example Session

```
ConLaw> What are the fundamental rights under Article 21?

Processing query: 'What are the fundamental rights under Article 21?'
This may take a moment...

✓ Research completed! Request ID: 15
Status: completed

Research Summary:
  • Cases found: 10
  • Statutes found: 5
  • Articles found: 8
  • Sources searched: 4

Executive Summary:
  Article 21 of the Indian Constitution guarantees the right to life and personal liberty...

Use 'result 15' to see full documentation
Use 'trace 15' to view the processing trace.

ConLaw> trace 15

==========================================================
PROCESSING TRACE FOR REQUEST 15
==========================================================

[2025-01-15T10:30:45] AGENT: MainAgent | TYPE: EVENT
--------------------------------------------------------------------------------
  Event Type: request_received
  Phase: received
  Payload: {"user_id": "cli_user", "query": "What are the fundamental rights under Article 21?"}
...
```

---

## System Architecture

### Agent Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Input                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UIAgent (ui_agent.py)                                                       │
│  • Receives natural language query                                           │
│  • Uses Gemini to convert to structured JSON                                 │
│  • Stores query in database                                                  │
│  • Can generate clarifying questions for ambiguous queries                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  MainAgent (main_agent.py)                                                   │
│  • Orchestrates workflow                                                     │
│  • Updates status (pending → researching → documenting → completed)          │
│  • Implements retry logic with exponential backoff                           │
│  • Coordinates TraceLogger for explainability                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ResearchAgent (research_agent.py)                                           │
│  • Uses Gemini to generate tool plan (which APIs to query)                   │
│  • Queries Indian Kanoon API for:                                            │
│    - Case law (judgments)                                                    │
│    - Statutes (acts)                                                         │
│    - Pending cases                                                           │
│  • Queries Springer Nature API for academic articles                         │
│  • Normalizes and aggregates results                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DocumentationAgent (documentation_agent.py)                                 │
│  • Processes research results                                                │
│  • Uses Gemini to generate structured legal analysis                         │
│  • Creates executive summary, case law review, statutory provisions          │
│  • Provides recommendations and additional resources                         │
│  • Has fallback documentation if AI generation fails                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Final Documentation                                │
│  • Structured JSON suitable for HTML rendering                               │
│  • Stored in database for retrieval                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component                 | File                | Description                                                               |
| ------------------------- | ------------------- | ------------------------------------------------------------------------- |
| `Config`                | config.py           | Centralized configuration for API keys, database path, and agent settings |
| `ConstitutionalLawDB`   | database.py         | SQLite database handler with methods for all CRUD operations              |
| `TraceLogger`           | trace_logger.py     | Records structured logs, artefacts, and decisions for explainability      |
| `AsyncIKApi`            | `ik_api_async.py` | Async wrapper for Indian Kanoon API                                       |
| `SpringerLegalResearch` | springer.py         | Springer Nature API integration for academic articles                     |
| Custom Exceptions         | `exceptions.py`   | Hierarchy of custom exceptions for error handling                         |

---

## Database Schema

The SQLite database (`ConstitutionalLawDB`) contains the following tables:

### `user_requests`

| Column             | Type        | Description                                                   |
| ------------------ | ----------- | ------------------------------------------------------------- |
| `id`             | INTEGER     | Primary key                                                   |
| `user_id`        | TEXT        | User identifier                                               |
| `timestamp`      | DATETIME    | When request was submitted                                    |
| `original_query` | TEXT        | Original user question                                        |
| `query_summary`  | TEXT (JSON) | Structured research parameters                                |
| `status`         | TEXT        | Current status (pending, researching, documenting, completed) |

### `research_results`

| Column                 | Type        | Description                  |
| ---------------------- | ----------- | ---------------------------- |
| `id`                 | INTEGER     | Primary key                  |
| `request_id`         | INTEGER     | Foreign key to user_requests |
| `sources`            | TEXT (JSON) | Research sources used        |
| `case_laws`          | TEXT (JSON) | Relevant cases               |
| `statutes`           | TEXT (JSON) | Constitutional provisions    |
| `pending_cases`      | TEXT (JSON) | Ongoing cases                |
| `articles`           | TEXT (JSON) | Scholarly articles           |
| `research_timestamp` | DATETIME    | When research was completed  |

### `documentation_output`

| Column                 | Type        | Description                       |
| ---------------------- | ----------- | --------------------------------- |
| `id`                 | INTEGER     | Primary key                       |
| `request_id`         | INTEGER     | Foreign key to user_requests      |
| `output_json`        | TEXT (JSON) | Complete structured documentation |
| `creation_timestamp` | DATETIME    | When documentation was generated  |

### `trace_logs`

| Column         | Type        | Description                 |
| -------------- | ----------- | --------------------------- |
| `id`         | INTEGER     | Primary key                 |
| `request_id` | INTEGER     | Foreign key (nullable)      |
| `agent`      | TEXT        | Agent that logged the event |
| `phase`      | TEXT        | Processing phase            |
| `event_type` | TEXT        | Type of event               |
| `payload`    | TEXT (JSON) | Event payload with hash     |
| `created_at` | DATETIME    | Timestamp                   |

### `artefact_snapshots`

| Column            | Type        | Description                     |
| ----------------- | ----------- | ------------------------------- |
| `id`            | INTEGER     | Primary key                     |
| `request_id`    | INTEGER     | Foreign key (nullable)          |
| `agent`         | TEXT        | Agent that created the artefact |
| `artefact_type` | TEXT        | Type of artefact                |
| `content`       | TEXT (JSON) | Full artefact content with hash |
| `created_at`    | DATETIME    | Timestamp                       |

### `decision_metadata`

| Column            | Type        | Description                  |
| ----------------- | ----------- | ---------------------------- |
| `id`            | INTEGER     | Primary key                  |
| `request_id`    | INTEGER     | Foreign key (nullable)       |
| `agent`         | TEXT        | Agent that made the decision |
| `decision_type` | TEXT        | Type of decision             |
| `rationale`     | TEXT        | Reasoning for the decision   |
| `metadata`      | TEXT (JSON) | Decision metadata            |
| `created_at`    | DATETIME    | Timestamp                    |

---

## Configuration

All configuration is centralized in `config.py`:

```python
class Config:
    # Database
    DATABASE_PATH = "constitutional_law.db"
  
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-key")
    GEMINI_MODEL = "gemini-2.5-flash"
  
    # Indian Kanoon API
    IK_API_TOKEN = "your-indian-kanoon-token"
  
    # Springer Nature APIs
    SPRINGER_META_API_KEY = "your-meta-api-key"
    SPRINGER_OPENACCESS_API_KEY = "your-openaccess-api-key"
  
    # Agent settings
    AGENT_CONFIG = {
        "max_retries": 3,
        "retry_delay": 1.0,
        "timeout": 30.0
    }
```

---

## Explainability & Tracing

Every agent interaction leaves an audit trail via `TraceLogger`:

### Trace Types

1. **Structured Logs** (`trace_logs` table)

   - Captures who did what, when, and why
   - Includes hashed payloads for integrity verification
2. **Artefact Snapshots** (`artefact_snapshots` table)

   - Preserves raw Gemini responses
   - Stores cleaned, structured objects
   - Enables replay and debugging
3. **Decision Metadata** (`decision_metadata` table)

   - Records agent reasoning
   - Documents query structuring decisions
   - Explains tool plan choices

### Viewing Traces

```bash
# In CLI
ConLaw> trace 15
ConLaw> artefacts 15
ConLaw> artefact_content 42
```

### Direct Database Query

```powershell
python -c "import sqlite3, json; conn = sqlite3.connect('constitutional_law.db'); conn.row_factory = sqlite3.Row; cur = conn.cursor();
for table in ('trace_logs','artefact_snapshots','decision_metadata'):
   cur.execute('SELECT * FROM ' + table + ' WHERE request_id=? ORDER BY id', (15,));
   rows = [dict(row) for row in cur.fetchall()];
   print(f'== {table} ==');
   for row in rows: print(json.dumps(row, indent=2, default=str));
conn.close()"
```

---

## API Integrations

### Indian Kanoon API

Integration via `AsyncIKApi` and `ik_api_async.py`:

- **Case Law**: Search judgments by keywords, case names, legal provisions
- **Statutes**: Search acts and statutory provisions
- **Pending Cases**: Find ongoing litigation

Query operators supported:

- `ANDD` - Logical AND
- `ORR` - Logical OR
- `NOTT` - Logical NOT
- Quoted phrases for exact matches

### Springer Nature API

Integration via `SpringerLegalResearch`:

- **Meta API**: Broader metadata search across Springer publications
- **OpenAccess API**: Full-text search for open access content

Configured for Basic plan compatibility with optimized query transformation.

### Query Normalization

The `ResearchAgent` normalizes queries using `extract_query_string` to ensure consistent API calls:

```python
def extract_query_string(tool_plan_value: str) -> str:
    # Extracts clean query string from tool plan
    # Removes formInput prefixes, doctypes, and metadata
```

---

## Troubleshooting

### Common Issues

| Issue                      | Solution                                                             |
| -------------------------- | -------------------------------------------------------------------- |
| "API key not found"        | Ensure `GEMINI_API_KEY` is set in environment or config.py         |
| "Database locked"          | Close other processes accessing the database; check file permissions |
| "Research timeout"         | Increase timeout values in config.py; check internet connection      |
| "JSON parsing error"       | Usually resolves with retry logic; check Gemini API status           |
| "Indian Kanoon rate limit" | Reduce `maxpages` parameter; add delays between requests           |
| "Springer empty results"   | Use simpler queries (2-3 keywords); check Basic plan constraints     |

### Logs

The system uses Python's `logging` module. Check console output for detailed error messages:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Testing API Connections

```bash
# Test Indian Kanoon
python test.py

# Test Springer Nature
python springer.py
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

1. **Add new data sources**: Implement new API methods in `research_agent.py`
2. **Enhance documentation formats**: Modify prompts in `documentation_agent.py`
3. **Improve query processing**: Update Gemini prompts in `ui_agent.py`
4. **Add new agent types**: Follow the existing pattern with proper tracing

### Code Style

- Use type hints for all function parameters and returns
- Document all public methods with docstrings
- Add trace logging for new agent interactions
- Handle exceptions using the custom exception hierarchy in `exceptions.py`

---

## Project Structure

```
legal-research/
├── main.py                 # CLI entry point
├── main_agent.py           # Main orchestration agent
├── ui_agent.py             # User input processing agent
├── research_agent.py       # Research coordination agent
├── documentation_agent.py  # Documentation generation agent
├── database.py             # SQLite database handler
├── trace_logger.py         # Explainability tracing
├── config.py               # Configuration settings
├── exceptions.py           # Custom exception hierarchy
├── ik_api_async.py         # Indian Kanoon API wrapper
├── springer.py             # Springer Nature API integration
├── requirements.txt        # Python dependencies
├── test.py                 # API testing script
├── constitutional_law.db   # SQLite database (created on first run)
└── learn-law/              # Next.js frontend (separate project)
```

---

## License

This system is provided as-is for educational and research purposes.
