# Map-Reduce Specification Extractor

A LangGraph agent that reads data specification documents (which can be very large), splits them into chunks, processes the chunks in parallel using the **Map-Reduce** pattern, and outputs structured JSON with file-level and field-level metadata.

Powered by DeepSeek-V3 via `langchain-deepseek`.

## Project Structure

```text
lg-01/
├── pyproject.toml      # Project metadata & dependency declarations
├── langgraph.json      # LangGraph Studio/CLI config file
├── .env.example        # Environment variables template
├── .gitignore          # Version control file exclusions
├── main.py             # CLI runner for spec extraction
└── src/                # Agent core logic package
    ├── __init__.py     # Package initialization
    ├── state.py        # Graph state definition (AgentState, MapState)
    ├── nodes.py        # Pydantic models, splitter, LLM extraction & reduction nodes
    └── agent.py        # Graph assembly with Map-Reduce fanout (Send API)
```

---

## Setup Instructions

### Prerequisites
1. **Python**: Python 3.13+
2. **uv**: Install with `pip install uv`

### 1. Synchronize Dependencies
```bash
uv sync
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` and set your DeepSeek API key:
```ini
DEEPSEEK_API_KEY=your_actual_deepseek_api_key
```

---

## Running the Extractor

```bash
uv run main.py path/to/specification.md
```

Or pipe from stdin:
```bash
cat spec.md | uv run main.py
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--max-parallelism N` | Max parallel LLM calls | `MAX_PARALLELISM` env var or unlimited |
| `--chunk-size N` | Max characters per chunk | `CHUNK_SIZE_LIMIT` env var or 6000 |

### Output

Structured JSON printed to stdout:

```json
{
  "file_metadata": {
    "file_format": "Tab-delimited",
    "encoding": "UTF-8",
    "delimiter": "Tab",
    "naming_convention": "yyyyMMddhhmm_CUSTOMER.TXT"
  },
  "fields": [
    {
      "field_group": "header",
      "field_index": 0,
      "field_name": "Record Type",
      "data_type": "string (1)",
      "description": "Record type identifier: H=Header"
    }
  ]
}
```
