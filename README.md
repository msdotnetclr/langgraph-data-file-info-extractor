# Data File Info Extractor

A LangGraph agent that reads data specification documents, splits them into overlapping chunks, processes them sequentially with context carry-forward, and extracts structured JSON with file-level and field-level metadata.

Now with a **React web UI** and **human-in-the-loop** review workflow — review extraction results, provide feedback, and iterate until approved. Accumulated feedback is summarized into domain-specific instructions for future extractions.

Supports **DeepSeek** and **Azure OpenAI** as LLM backends.

## State Graph

```
START
  → split_specification       (read file, split into overlapping chunks)
  → extract_next_chunk ⤻      (loop: LLM extracts fields per chunk)
  → reduce_results             (merge metadata, deduplicate and sort fields)
  → review_results             [INTERRUPT — wait for human]
      ├── approve → store_approved_result → END
      └── reject  → incorporate_feedback → split_specification (re-run with new instructions)
```

## Architecture

```
                     ┌──────────────────────────┐
                     │       React SPA (Vite)     │
                     │   http://localhost:5173    │
                     └─────────────┬──────────────┘
                                   │ REST + SSE
                     ┌─────────────▼──────────────┐
                     │     FastAPI Server          │
                     │   http://localhost:8000     │
                     │                             │
                     │  /api/domains               │
                     │  /api/sources               │
                     │  /api/sessions              │
                     │  /api/sessions/:id/start    │  SSE streaming
                     │  /api/sessions/:id/review   │
                     │  /api/outputs               │
                     │  /api/extract               │  Stateless (CLI mode)
                     │  /api/input-tree            │
                     └─────────────┬───────────────┘
                                   │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
         ┌──────────┐       ┌───────────────┐    ┌──────────────┐
         │  src/    │       │ AsyncSqlite   │    │  File Store  │
         │ LangGraph│       │  Saver +      │    │  data/{input,│
         │  agent   │       │  aiosqlite    │    │   output}/   │
         └──────────┘       └───────────────┘    └──────────────┘
```

### CLI Path

```
main.py  →  build_graph()  →  in-memory execution (no checkpoint, no HITL)
```

The CLI path shares the same core graph code but compiles without a checkpointer and without the HITL nodes, keeping it fast and stateless.

## Project Structure

```text
project/
├── main.py                         # CLI entry point (preserved)
├── pyproject.toml                  # Python dependencies
├── langgraph.json                  # LangGraph Studio/CLI config
├── .env.example                    # Environment variables template
│
├── src/                            # Shared core (CLI + server)
│   ├── state.py                    # AgentState with HITL fields
│   ├── agent.py                    # build_graph() + build_interactive_graph()
│   ├── nodes.py                    # All graph nodes (extract, review, feedback)
│   ├── llm.py                      # LLM client, retry, prompt builder, summarizer
│   ├── storage.py                  # InputStore + OutputStore (file-based)
│   ├── session_manager.py          # SessionStore + AsyncSqliteSaver lifecycle
│   └── tools.py                    # (reserved)
│
├── server/                         # FastAPI backend
│   ├── main.py                     # App with CORS, 6 routers mounted
│   └── api/
│       ├── schemas.py              # Pydantic models
│       ├── domains.py              # Domain CRUD + instructions
│       ├── sources.py              # Source CRUD + upload-spec + input-tree
│       ├── sessions.py             # Session CRUD
│       ├── extract.py              # SSE streaming extraction + stateless endpoint
│       ├── review.py               # Review data + submit decision + summarization
│       └── outputs.py              # Output store browser
│
├── client/                         # React SPA (Vite + TypeScript + Tailwind)
│   └── src/
│       ├── api/client.ts           # Typed API functions
│       ├── components/             # Layout, Modal, TreeView
│       └── pages/
│           ├── Dashboard.tsx       # Domain/source stats
│           ├── DomainList.tsx      # Domain CRUD table
│           ├── DomainDetail.tsx    # Instructions editor + source management
│           ├── Sessions.tsx        # Session list with status filters
│           ├── SessionDetail.tsx   # Session info + start/review buttons
│           ├── ExtractProgress.tsx # SSE live progress bar
│           ├── Review.tsx          # Tabbed results + approve/re-run
│           ├── NotFound.tsx        # 404 page
│           └── Outputs.tsx         # Output store tree browser + viewer
│
├── tests/
│   ├── test_nodes.py               # Splitter, merge, error classification (60 tests)
│   ├── test_reduce.py              # Reduce node (7 tests)
│   ├── test_hitl.py                # Review/feedback routing + nodes (8 tests)
│   ├── test_session_manager.py     # SessionStore lifecycle (14 tests)
│   └── test_storage.py             # InputStore + OutputStore (14 tests)
│
└── data/                           # Runtime storage (gitignored, see DATA_ROOT)
    ├── input/{domain}/{source}/source_specs.md
    ├── output/{domain}/{source}/{session_id}_{timestamp}.json
    └── sessions/checkpoints.db
```

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (for Python dependencies)
- Node.js 18+ and npm (for the React frontend)

### 1. Install dependencies

```bash
# Python
uv sync

# Frontend
cd client && npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your LLM credentials.

**DeepSeek** (default):
```ini
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here
```

**Azure OpenAI**:
```ini
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

**Storage root** (optional, defaults to `./data`):
```ini
DATA_ROOT=/path/to/data
```

### 3. Start the backend

```bash
uv run uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### 4. Start the frontend

```bash
cd client && npm run dev
```

Open http://localhost:5173 in your browser.

## Web UI Workflow

### 1. Set Up the Input Store

- Go to **Domains** → create a domain (e.g. `sales` or `inventory`)
- Click a domain → edit **domain instructions** (optional LLM guidance for this domain)
- Create a **source** (e.g. `monthly-export`) → upload/paste the `source_specs.md` file

### 2. Run an Extraction

- Go to **Sessions** → click **+ New Session**
- Select a domain and source from the tree view
- Click **Start Extraction** → watch the live progress bar (chunking → extracting → reducing)
- When complete, the session is persisted as "draft"

### 3. Review & Iterate

- On the **Review** page, inspect results across four tabs:
  - **Summary** — file format, encoding, delimiter, naming convention
  - **Fields** — table of all extracted fields (group, index, name, type, description)
  - **Warnings** — any warnings from the extraction process
  - **Raw JSON** — the full extraction output

- Choose an action:
  - **Approve** — saves the result to the **Output Store**, summarizes any accumulated feedback into `domain_instructions.md` (via LLM), and marks the session as approved
  - **Re-run with Feedback** — opens a markdown editor for detailed instructions; feedback is appended and the extraction re-runs with the new instructions injected into the prompt
  - **Delete** — removes the session

### 4. Browse Outputs

- Go to **Outputs** → browse the output store by domain and source
- Click any output file to view its extracted metadata and field list

## Session States

| State | Description |
|-------|-------------|
| `created` | Session exists but extraction has not started |
| `in_progress` | Extraction is running (SSE streaming active) |
| `draft` | Extraction complete, awaiting human review |
| `approved` | User approved; result saved to output store, feedback summarized |
| `failed` | Extraction encountered an error |

## Storage

All data is stored under `DATA_ROOT` (default: `./data`). The structure mirrors the two-tier domain/source hierarchy:

```
data/
├── input/
│   └── {domain}/
│       ├── domain_instructions.md      # Domain-specific LLM guidance
│       └── {source}/
│           └── source_specs.md         # Specification file (input to graph)
│
├── output/
│   └── {domain}/
│       └── {source}/
│           └── {session_id}_{timestamp}.json   # Approved results only
│
└── sessions/
    ├── checkpoints.db                  # SQLite (AsyncSqliteSaver checkpoints)
    └── {session_id}/
        └── metadata.json               # Session metadata + feedback rounds
```

## CLI Usage (Stateless Extraction)

The original CLI is preserved and usable independently:

```bash
# From a file
uv run main.py path/to/specification.md

# From stdin
cat spec.md | uv run main.py

# With domain-specific instructions
uv run main.py spec.md --instructions-file custom_rules.md
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--llm-provider {deepseek,azure_openai}` | LLM backend | `LLM_PROVIDER` env var or `deepseek` |
| `--lines-per-chunk N` | Lines per chunk | `LINES_PER_CHUNK` env var or `500` |
| `--overlap-lines N` | Overlapping lines between chunks | `OVERLAP_LINES` env var or `50` |
| `--instructions-file PATH` | File with domain-specific instructions (overrides domain store) | none |

### API Stateless Endpoint

```bash
curl -X POST "http://localhost:8000/api/extract?content=your+spec+text"
```

## Output Schema

```json
{
  "file_metadata": {
    "file_format": "Tab-delimited",
    "encoding": "ANSI",
    "delimiter": "Tab",
    "naming_convention": "yyyyMMddhhmm_CUSTOMER.TXT"
  },
  "fields": [
    {
      "field_group": "header",
      "field_index": 0,
      "field_name": "File Name",
      "data_type": "string (50)",
      "description": "The name of this request file excluding path."
    },
    {
      "field_group": "content",
      "field_index": 0,
      "field_name": "Customer ID",
      "data_type": "integer (10)",
      "description": "The customerId property of the customer object."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `file_metadata.file_format` | `string | null` | File format (e.g. Tab-delimited, CSV, Fixed-width) |
| `file_metadata.encoding` | `string | null` | File encoding (e.g. ANSI, UTF-8) |
| `file_metadata.delimiter` | `string | null` | Delimiter (e.g. Tab, Comma, 0x09) |
| `file_metadata.naming_convention` | `string | null` | File naming pattern |
| `fields[]` | `array` | List of field definitions |
| `fields[].field_group` | `string` | `header` or `content` |
| `fields[].field_index` | `integer | null` | 0-based position in the group |
| `fields[].field_name` | `string` | Name of the field |
| `fields[].data_type` | `string` | Type and length (e.g. `string (50)`) |
| `fields[].description` | `string` | Full description of the field's purpose |

## Running Tests

```bash
uv run pytest tests/ -v
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent | LangGraph |
| LLM | DeepSeek / Azure OpenAI (via LangChain) |
| API Server | FastAPI + Uvicorn |
| Checkpoints | AsyncSqliteSaver (SQLite + aiosqlite) |
| Storage | File-based (JSON, Markdown) |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS 4 |
