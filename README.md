# Data File Info Extractor

A LangGraph agent that reads data specification documents, splits them into overlapping chunks, processes them sequentially with context carry-forward, and extracts structured JSON with file-level and field-level metadata.

Now with a **React web UI** and **human-in-the-loop** review workflow — review extraction results, provide feedback, and iterate until approved. Accumulated feedback is summarized into domain-specific instructions for future extractions.

Supports **DeepSeek** and **Azure OpenAI** as LLM backends.

## State Graph

```
START
  → split_specification       ─── reads spec file, splits into overlapping line ranges
  → extract_next_chunk ⤻       ─── loops: LLM extracts fields per chunk with prior context
  → reduce_results              ─── merges file_metadata, deduplicates & sorts fields
  → review_results              ─── [INTERRUPT — waits for human decision]
        │
        ├── "approved" → store_approved_result → END
        │                     └── writes versioned JSON to output store + updates _manifest.json
        │
        └── "rejected" → incorporate_feedback → split_specification (re-run)
                              └── resets extraction state, injects feedback into domain_instructions
```

The graph is compiled in two variants:

| Variant | Function | Checkpointer | HITL Nodes | Used by |
|---------|----------|-------------|------------|---------|
| **Stateless** | `build_graph()` | none | excluded | CLI (`main.py`), stateless API endpoint |
| **Interactive** | `build_interactive_graph(checkpointer)` | AsyncSqliteSaver | included | Server sessions (SSE + review) |

Both variants share the same core graph (`_build_base_workflow`) via `src/agent.py`. The interactive variant adds the review/feedback/approval nodes and a checkpointer that persists graph state across interrupts.

### AgentState — How Fields Direct the Workflow

The `AgentState` TypedDict in `src/state.py` defines every data field flowing through the graph. Understanding how each field is set and consumed is essential to understanding the workflow:

| Field | Type | Set By | Consumed By | Role |
|-------|------|--------|-------------|------|
| `spec_file` | `str` | Server (extract endpoint) | `split_specification` | Path to the source spec file to extract from |
| `spec_file_size` | `int` | `split_specification` | `extract_next_chunk` | Expected byte size; rechecked on each chunk read to detect mid-flight file changes |
| `chunk_ranges` | `list[(int,int)]` | `split_specification` | `extract_next_chunk`, `should_continue` | Line ranges (start,end) for each chunk; `should_continue` checks if more chunks remain |
| `current_chunk_index` | `int` | `split_specification` (set to 0), `extract_next_chunk` (incremented), `incorporate_feedback` (reset to 0) | `should_continue`, `extract_next_chunk` | Index into `chunk_ranges`; drives the chunk iteration loop |
| `partial_fields` | `list[dict]` | `extract_next_chunk`, `split_specification` (initially `[]`), `incorporate_feedback` (reset to `[]`) | `extract_next_chunk`, `reduce_results` | Accumulated extracted fields across chunks for deduplication and context carry-forward |
| `extracted_data` | `list[dict]` (annotated `operator.add` — auto-concatenated across invocations) | `extract_next_chunk` | `reduce_results` | Per-chunk raw extraction results including file_metadata and fields, aggregated via LangGraph reducer |
| `file_metadata` | `dict` | `reduce_results` | `store_approved_result` | Final merged file-level metadata (format, encoding, delimiter, naming_convention) |
| `fields` | `list[dict]` | `reduce_results` | `store_approved_result` | Final deduplicated and sorted field list |
| `domain_instructions` | `str` | Server (loaded from `domain_instructions.md`), `incorporate_feedback` (appends feedback) | `extract_next_chunk` (injected into LLM prompt) | Domain-specific guidance for the LLM; feedback rounds accumulate here |
| `warnings` | `list[str]` (annotated `operator.add` — auto-concatenated) | `extract_next_chunk`, `reduce_results` | Review UI, `store_approved_result` | Accumulated warnings (chunk failures, field conflicts, duplicates) |
| `session_id` | `str` | Server (session creation) | `store_approved_result` | Ties output version back to the originating session |
| `domain` | `str` | Server (session creation) | `store_approved_result` | Domain name for output store routing |
| `source` | `str` | Server (session creation) | `store_approved_result` | Source name for output store routing |
| `review_decision` | `str` | Server (`graph.update_state` from approve/reject), `review_results` | `after_review_route` | `"approved"` → store output; `"rejected"` → incorporate feedback; empty → wait (interrupt) |
| `human_feedback` | `str` | Server (`graph.update_state` from review form) | `incorporate_feedback` | Free-text feedback appended to `domain_instructions` |
| `approved` | `bool` | `store_approved_result` | (graph terminal marker) | Set to `true` on successful approval |
| `status` | `str` | `store_approved_result` | (graph terminal marker) | Set to `"approved"` on successful approval |

**Key annotation**: Fields annotated with `operator.add` (like `warnings` and `extracted_data`) use LangGraph's built-in reducer mechanism. Instead of overwriting on subsequent graph invocations, new values are concatenated to the existing list. This allows warnings from each chunk and extraction data from each iteration to accumulate naturally without explicit merge logic.

### Chunk Iteration Loop

```
split_specification
    │  Sets: chunk_ranges, current_chunk_index=0, spec_file_size
    ▼
extract_next_chunk
    │  Reads:  chunk_ranges[idx], spec_file_size
    │  Calls:  LLM with structured output (ExtractedMetadata Pydantic model)
    │  Merges: new fields into partial_fields (dedup, conflict detect)
    │  Sets:   partial_fields, extracted_data (list concat), current_chunk_index += 1
    ▼
should_continue
    │  current_chunk_index < len(chunk_ranges) ?
    ├── YES → extract_next_chunk (loop)
    └── NO  → reduce_results
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
│   ├── state.py                    # AgentState TypedDict — all graph fields + reducers
│   ├── agent.py                    # build_graph() + build_interactive_graph()
│   ├── nodes.py                    # All graph nodes (extract, reduce, review, feedback, store)
│   ├── llm.py                      # LLM client, retry, prompt builder, feedback summarizer
│   ├── storage.py                  # InputStore + OutputStore (file-based, versioned)
│   ├── session_manager.py          # SessionStore + AsyncSqliteSaver lifecycle
│   └── tools.py                    # (reserved)
│
├── server/                         # FastAPI backend
│   ├── main.py                     # App with CORS, 6 routers mounted
│   └── api/
│       ├── schemas.py              # Pydantic models (incl. versioning schemas)
│       ├── domains.py              # Domain CRUD + instructions
│       ├── sources.py              # Source CRUD + upload-spec + input-tree
│       ├── sessions.py             # Session CRUD
│       ├── extract.py              # SSE streaming extraction + stateless endpoint
│       ├── review.py               # Review data + submit decision + summarization
│       └── outputs.py              # Output store browser with versioning, diff, chain endpoints
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
│           ├── Outputs.tsx         # Versioned output browser: tree, chain, diff viewer
│           └── NotFound.tsx        # 404 page
│
├── tests/
│   ├── conftest.py                 # Isolates DATA_ROOT to a temp directory
│   ├── test_nodes.py               # Splitter, merge, error classification (59 tests)
│   ├── test_reduce.py              # Reduce node (7 tests)
│   ├── test_hitl.py                # Review/feedback routing + nodes (8 tests)
│   ├── test_session_manager.py     # SessionStore lifecycle (12 tests)
│   └── test_storage.py             # InputStore + OutputStore incl. versioning (34 tests)
│
└── data/                           # Runtime storage (gitignored, see DATA_ROOT)
    ├── input/{domain}/{source}/source_specs.md
    ├── output/{domain}/{source}/   # ← versioned layout (see Storage section)
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
  - **Approve** — saves the result as a new version in the **Output Store**, summarizes any accumulated feedback into `domain_instructions.md` (via LLM), and marks the session as approved
  - **Re-run with Feedback** — opens a markdown editor for detailed instructions; feedback is appended and the extraction re-runs with the new instructions injected into the prompt
  - **Delete** — removes the session

### 4. Browse Outputs

- Go to **Outputs** → browse the output store by domain and source
- Each source displays its version count and latest version number (e.g. `customer v3 (3 versions)`)
- Click a version to view its full content
- The **version chain breadcrumb** shows the lineage: `v1 → v2 (feedback) → v3 LATEST`
- **Compare** two versions to see a structured diff:
  - File metadata changes (old → new table)
  - Fields added (green), removed (red), modified (yellow with per-attribute diff)
  - Warnings added/removed
- Click **Swap** to reverse comparison direction

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
│       ├── domain_instructions.md         # Domain-specific LLM guidance
│       └── {source}/
│           └── source_specs.md            # Specification file (input to graph)
│
├── output/
│   └── {domain}/
│       └── {source}/
│           ├── _manifest.json             # Version registry, latest pointer, lineage
│           ├── v1_{session_id_a}.json     # Version 1 (oldest)
│           ├── v2_{session_id_b}.json     # Version 2 (based on v1)
│           └── v3_{session_id_c}.json     # Version 3 (latest)
│
└── sessions/
    ├── checkpoints.db                     # SQLite (AsyncSqliteSaver checkpoints)
    └── {session_id}/
        └── metadata.json                  # Session metadata + feedback rounds
```

### Output Versioning

Each time a session outcome is approved, it is saved as a new **versioned** output file. The `_manifest.json` file tracks all versions for a source:

```json
{
  "domain": "sales",
  "source": "monthly-export",
  "latest_version": 3,
  "versions": [
    {
      "version": 1,
      "session_id": "abc123...",
      "created_at": "2026-06-01T10:00:00Z",
      "filename": "v1_abc123.json",
      "based_on_version": null,
      "feedback_rounds": 0
    },
    {
      "version": 2,
      "session_id": "def456...",
      "created_at": "2026-06-03T14:30:00Z",
      "filename": "v2_def456.json",
      "based_on_version": 1,
      "feedback_rounds": 2
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `latest_version` | Points to the most recent version — always easy to find |
| `based_on_version` | Links each version to its predecessor, forming a lineage chain |
| `feedback_rounds` | Number of human feedback iterations before this version was approved |

Migration of legacy `{session_id}_{timestamp}.json` files to the versioned layout is automatic — on first access to a source directory, `OutputStore` renames files by mtime order and generates a `_manifest.json`.

### API Endpoints (Versioning)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/outputs/{domain}/{source}/latest` | Returns the latest version with data and metadata |
| `GET` | `/api/outputs/{domain}/{source}/versions/{version}` | Returns a specific version by number |
| `GET` | `/api/outputs/{domain}/{source}/diff?v1=1&v2=3` | Structured diff between two versions |
| `GET` | `/api/outputs/{domain}/{source}/chain?version=3` | Version lineage chain (v1 → v2 → v3) |
| `GET` | `/api/outputs/{domain}/{source}/manifest` | Full `_manifest.json` contents |

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
  ],
  "warnings": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `file_metadata.file_format` | `string \| null` | File format (e.g. Tab-delimited, CSV, Fixed-width) |
| `file_metadata.encoding` | `string \| null` | File encoding (e.g. ANSI, UTF-8) |
| `file_metadata.delimiter` | `string \| null` | Delimiter (e.g. Tab, Comma, 0x09) |
| `file_metadata.naming_convention` | `string \| null` | File naming pattern |
| `fields[]` | `array` | List of field definitions |
| `fields[].field_group` | `string` | `header` or `content` |
| `fields[].field_index` | `integer \| null` | 0-based position in the group |
| `fields[].field_name` | `string` | Name of the field |
| `fields[].data_type` | `string` | Type and length (e.g. `string (50)`) |
| `fields[].description` | `string` | Full description of the field's purpose |

## Running Tests

```bash
uv run pytest tests/ -v
```

Tests use a temporary `DATA_ROOT` directory via `tests/conftest.py` — the real `data/` directory is never touched during test runs.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent | LangGraph |
| LLM | DeepSeek / Azure OpenAI (via LangChain) |
| API Server | FastAPI + Uvicorn |
| Checkpoints | AsyncSqliteSaver (SQLite + aiosqlite) |
| Storage | File-based (JSON, Markdown) — versioned with `_manifest.json` |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS 4 |
