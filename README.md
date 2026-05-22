# Specification Metadata Extractor

A LangGraph agent that reads data specification documents (potentially very large), splits them into overlapping chunks, processes them **sequentially** with context carry-forward, and outputs structured JSON with file-level and field-level metadata.

Supports **DeepSeek** and **Azure OpenAI** as LLM backends.

## How It Works

```
START → split_specification → extract_next_chunk ⤻ (loop) → reduce_results → END
```

1. **Split** — The document is divided into overlapping chunks (default: 500 lines per chunk, 50-line overlap). The overlap ensures no field definition is ever cut at a chunk boundary.

2. **Extract (sequential loop)** — Each chunk is processed in document order. Before each chunk, the LLM receives the last 10 extracted fields as context — including the last `field_index` — so field numbering continues correctly across chunks. Incomplete fields from previous chunks are flagged and re-extracted when their full definition appears in an overlap zone.

3. **Reduce** — File-level metadata is merged (preferring the most complete value across chunks). Fields are deduplicated, sorted by group and index, and validated against the output schema.

### Handling mid-chunk splits

- **Overlap**: Adjacent chunks share 50 lines. A field that starts near the end of chunk N will appear fully in the overlap zone of chunk N+1.
- **Context**: Each chunk's prompt lists the last 10 extracted fields with completeness markers (`[INCOMPLETE]`). The LLM is instructed to re-extract incomplete fields and stitch descriptions that span chunk boundaries.
- **Merge**: The reducer deduplicates by `(group, index, name)`, falling back to `(group, name)` when an index is missing from the first extraction. Per-attribute best-value picking ensures the most complete version wins.

## Project Structure

```text
lg-01/
├── pyproject.toml      # Dependencies (langgraph, langchain-deepseek, langchain-openai)
├── langgraph.json      # LangGraph Studio/CLI config
├── .env.example        # Environment variables template
├── main.py             # CLI entry point
└── src/
    ├── __init__.py
    ├── state.py        # AgentState definition
    ├── nodes.py        # Pydantic schemas, splitter, LLM nodes, reducer
    └── agent.py        # Graph assembly (sequential loop)
```

## Setup

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)

### 1. Install dependencies
```bash
uv sync
```

### 2. Configure environment
```bash
cp .env.example .env
```

Edit `.env` with your LLM credentials:

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

## Usage

```bash
uv run main.py path/to/specification.md
```

Pipe from stdin:
```bash
cat spec.md | uv run main.py
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--llm-provider {deepseek,azure_openai}` | LLM backend | `LLM_PROVIDER` env var or `deepseek` |
| `--lines-per-chunk N` | Lines per chunk | `LINES_PER_CHUNK` env var or `500` |
| `--overlap-lines N` | Overlapping lines between chunks | `OVERLAP_LINES` env var or `50` |

### Output

Structured JSON printed to stdout:

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

## Output Schema

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
