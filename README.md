# Constitutional Law Research Agent System

A sophisticated multi-agent system for constitutional law research using Google's Gemini 2.5 Pro with custom tool calling and SQLite database integration.

## System Overview

This system consists of four specialized agents working together to provide comprehensive constitutional law research:

### Agents

1. **UI Agent** - Processes natural language user input and converts it to structured JSON queries
2. **Main Agent** - Orchestrates the overall workflow and coordinates between agents
3. **Research Agent** - Collects extensive legal data from multiple sources (cases, statutes, articles)
4. **Documentation Agent** - Generates professional, structured documentation suitable for legal use

### Architecture

```
User Query → UI Agent → Main Agent → Research Agent → Documentation Agent → Final Report
              ↓           ↓            ↓                 ↓
           SQLite DB   Status Mgmt   Legal APIs      Structured JSON
```

## Features

- **Natural Language Processing**: Convert plain English queries into structured legal research parameters
- **Comprehensive Research**: Searches case law, statutes, pending cases, and scholarly articles
- **Professional Documentation**: Generates executive summaries, legal analysis, and recommendations
- **Database Integration**: Persistent storage of all queries, research, and results
- **Explainability & Traceability**: Structured logs, artefact snapshots, and decision metadata for every agent
- **Deterministic Controls**: Pinned prompts, zero-temperature LLM settings, and normalized external queries ensure repeatable outcomes
- **Retry Logic**: Robust error handling with exponential backoff
- **Status Tracking**: Real-time status updates for long-running research tasks

## Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key
- SQLite (included with Python)

### Setup

1. **Clone or download the system files**
2. **Install dependencies**:

   ```bash
   pip install google-generativeai sqlite3 asyncio
   ```
3. **Set up API keys**:

   **Option A: Environment Variables (Recommended)**

   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```

   **Option B: Edit config.py**

   ```python
   GEMINI_API_KEY = "your-actual-gemini-api-key-here"
   ```
4. **Initialize the database**:
   The database will be created automatically on first run.

## Usage

### Command Line Interface

#### Interactive Mode

```bash
python main.py
```

This starts an interactive session where you can:

- Enter constitutional law research queries
- Check status of ongoing research
- View completed results
- Get help and guidance

#### Single Query Mode

```bash
python main.py "What are the current limits on executive power?"
```

### Example Queries

- "What is the current status of affirmative action in education?"
- "How has the Equal Protection Clause been interpreted in recent Supreme Court cases?"
- "What are the constitutional limits on presidential emergency powers?"
- "How do state religious freedom laws interact with federal civil rights protections?"

### CLI Commands

- `help` - Show available commands
- `status <request_id>` - Check status of a research request
- `result <request_id>` - Display full research results
- `clear` - Clear the screen
- `quit` - Exit the program

## Database Schema

### Tables

#### user_requests

- `id` - Primary key
- `user_id` - User identifier
- `timestamp` - When request was submitted
- `original_query` - Original user question
- `query_summary` - Structured JSON of research parameters
- `status` - Current status (pending, researching, documenting, completed)

#### research_results

- `id` - Primary key
- `request_id` - Foreign key to user_requests
- `sources` - JSON array of research sources
- `case_laws` - JSON array of relevant cases
- `statutes` - JSON array of constitutional provisions
- `pending_cases` - JSON array of ongoing cases
- `articles` - JSON array of scholarly articles
- `research_timestamp` - When research was completed

#### documentation_output

- `id` - Primary key
- `request_id` - Foreign key to user_requests
- `output_json` - Complete structured documentation
- `creation_timestamp` - When documentation was generated

## Configuration

### API Integration Placeholders

The system includes placeholders for integration with legal databases:

- **CourtListener API** - Federal court opinions
- **Justia API** - Legal resources
- **Qdrant Vector Database** - RAG-based document search

To implement these integrations:

1. Sign up for API access with the respective services
2. Add your API keys to `config.py`
3. Implement the actual API calls in `research_agent.py`

### Customization

#### Agent Behavior

Modify agent prompts in the respective agent files to customize:

- Research focus areas
- Documentation style
- Analysis depth
- Output format

#### Database

Extend the database schema in `database.py` to add:

- User management
- Research categories
- Citation tracking
- Usage analytics

## System Architecture

### Agent Communication Flow

1. **User Input Processing**

   - UI Agent receives natural language query
   - Gemini converts to structured JSON
   - Query stored in database
2. **Research Coordination**

   - Main Agent updates status to "researching"
   - Research Agent searches multiple sources
   - Results deduplicated and validated
   - Research data stored in database
3. **Documentation Generation**

   - Main Agent updates status to "documenting"
   - Documentation Agent processes research results
   - Gemini generates structured legal analysis
   - Final documentation stored and marked complete

### Deterministic Output Controls

The system minimizes randomness so retries give consistent results:

- **Prompt Registry**: Agent prompts are stored as versioned templates (see `ui_agent.py`, `research_agent.py`, `documentation_agent.py`) so text generation always starts from the same instructions.
- **LLM Settings**: The Gemini client uses temperature `0`, `top_p` `0`, and capped token budgets via `config.py`, eliminating sampling variance.
- **Retry Strategy**: `MainAgent` drives exponential backoff with fixed intervals, and failed runs log the exact attempt count.
- **Query Normalization**: `ResearchAgent` canonicalizes Indian Kanoon queries (ordering, spacing, removal of redundant tokens) before hitting external APIs.
- **Shared State**: `TraceLogger` hashes payloads; comparing hashes across runs quickly shows whether responses changed.

Together these controls make it straightforward to reproduce outputs across environments or identify when an upstream dependency diverges.

### Explainability Tracing

Every agent interaction now leaves an audit trail so you can replay exactly how a report was built:

- **Structured Logs** (`trace_logs` table) capture who did what, when, and why with hashed payloads.
- **Artefact Snapshots** (`artefact_snapshots` table) preserve the raw Gemini responses alongside the cleaned, structured objects stored in the system.
- **Decision Metadata** (`decision_metadata` table) records each agent's reasoning (for example, how queries were structured or why a tool plan was chosen).

All three tables link back to the originating `request_id`, making it easy to filter for a specific run.

#### Peeking at a Trace (example for request `13`)

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3, json; conn = sqlite3.connect('constitutional_law.db'); conn.row_factory = sqlite3.Row; cur = conn.cursor();
for table in ('trace_logs','artefact_snapshots','decision_metadata'):
   cur.execute('SELECT * FROM ' + table + ' WHERE request_id=? ORDER BY id', (13,));
   rows = [dict(row) for row in cur.fetchall()];
   print(f'== {table} ==');
   if not rows:
      print('(no rows)');
   else:
      for row in rows:
         print(json.dumps(row, indent=2, default=str));
conn.close()"
```

Replace `13` with any other request ID you want to audit. The output includes the timestamped payloads, Gemini artefacts, and decision rationales for that run.

### Error Handling

- **Custom Exception Hierarchy**: Specific exceptions for different failure modes
- **Retry Logic**: Exponential backoff for API rate limits
- **Graceful Degradation**: Fallback responses when AI generation fails
- **Database Rollback**: Consistent state even during failures

### Production Considerations

#### Security

- Store API keys in environment variables
- Implement user authentication
- Add input sanitization
- Use HTTPS for API communication

#### Scalability

- Add connection pooling for database
- Implement async/await throughout
- Add caching layer for repeated queries
- Consider microservices architecture

#### Monitoring

- Add structured logging
- Implement metrics collection
- Monitor API usage and costs
- Track research quality metrics

## Legal Disclaimer

This system is for research and educational purposes. Always verify legal information with qualified attorneys. The system provides research assistance but does not constitute legal advice.

## Troubleshooting

### Common Issues

**"API key not found"**

- Ensure GEMINI_API_KEY is set in environment or config.py

**"Database locked"**

- Close any other processes accessing the database file
- Check file permissions

**"Research timeout"**

- Increase timeout values in config.py
- Check internet connection for API access

**"JSON parsing error"**

- This typically resolves with retry logic
- Check Gemini API status if persistent

### Logs

Check the console output for detailed error messages and processing status.

## Contributing

To extend this system:

1. **Add new data sources** in `research_agent.py`
2. **Enhance documentation formats** in `documentation_agent.py`
3. **Improve query processing** in `ui_agent.py`
4. **Add new agent types** following the existing pattern

## License

This system is provided as-is for educational and research purposes.
