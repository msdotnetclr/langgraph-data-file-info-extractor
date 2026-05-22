import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _check_api_key():
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()

    if provider == "azure_openai":
        required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"]
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            print(f"ERROR: Azure OpenAI is missing: {', '.join(missing)}", file=sys.stderr)
            print("Set LLM_PROVIDER=azure_openai and configure the Azure variables in .env.", file=sys.stderr)
            sys.exit(1)
        return

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("ERROR: DEEPSEEK_API_KEY is not set.", file=sys.stderr)
        print("Set it in a .env file or as an environment variable.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract file-level and field-level metadata from a data specification document."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to the specification file (markdown or text). Reads from stdin if not provided.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["deepseek", "azure_openai"],
        default=os.getenv("LLM_PROVIDER", "deepseek"),
        help="LLM provider to use (default: LLM_PROVIDER env var or deepseek).",
    )
    parser.add_argument(
        "--lines-per-chunk",
        type=int,
        default=int(os.getenv("LINES_PER_CHUNK", "500")),
        help="Number of lines per text chunk (default: 500).",
    )
    parser.add_argument(
        "--overlap-lines",
        type=int,
        default=int(os.getenv("OVERLAP_LINES", "50")),
        help="Number of overlapping lines between consecutive chunks (default: 50).",
    )
    args = parser.parse_args()

    os.environ["LLM_PROVIDER"] = args.llm_provider
    _check_api_key()

    from src.state import AgentState
    from src.agent import graph

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw_text = f.read()
    else:
        raw_text = sys.stdin.read()

    if not raw_text.strip():
        print("ERROR: Empty input.", file=sys.stderr)
        sys.exit(1)

    state: AgentState = {
        "raw_specification": raw_text,
        "chunks": [],
        "current_chunk_index": 0,
        "partial_fields": [],
        "extracted_data": [],
        "file_metadata": {},
        "fields": [],
    }

    result = graph.invoke(state)

    output = {
        "file_metadata": result.get("file_metadata", {}),
        "fields": result.get("fields", []),
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
