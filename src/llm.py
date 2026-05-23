import os
import sys
import time


# ---------------------------------------------------------------------------
# 1. Custom Exceptions
# ---------------------------------------------------------------------------


class LLMPermanentError(Exception):
    """Permanent LLM error that cannot be resolved by retrying
    (e.g. authentication failure, invalid model, bad request)."""


class LLMTransientError(Exception):
    """Transient LLM error that may resolve on retry
    (e.g. network timeout, connection issue, rate limit, server error)."""


# ---------------------------------------------------------------------------
# 2. Error Classification
# ---------------------------------------------------------------------------


def classify_llm_error(exc: BaseException) -> str:
    """Classify a caught exception from an LLM invocation.

    Returns one of:
        'permanent'  — auth / config / bad-request.  Do NOT retry.
        'rate_limit' — HTTP 429.  Retry after a wait (respect Retry-After).
        'transient'  — network / timeout / 5xx.  Retry with backoff.
    """
    try:
        import openai
        _openai_available = True
    except ImportError:
        _openai_available = False

    current: BaseException | None = exc
    while current is not None:
        if _openai_available:
            if isinstance(current, (
                openai.AuthenticationError,
                openai.PermissionDeniedError,
                openai.BadRequestError,
                openai.NotFoundError,
                openai.UnprocessableEntityError,
            )):
                return "permanent"
            if isinstance(current, openai.RateLimitError):
                return "rate_limit"
            if isinstance(current, (
                openai.APITimeoutError,
                openai.APIConnectionError,
                openai.InternalServerError,
            )):
                return "transient"

        msg = str(current).lower()
        if any(kw in msg for kw in (
            "401", "unauthorized", "invalid api key", "incorrect api key",
            "authentication", "permission denied", "forbidden",
        )):
            return "permanent"
        if any(kw in msg for kw in (
            "400", "bad request", "invalid request", "not found",
        )):
            return "permanent"
        if any(kw in msg for kw in ("429", "rate limit", "too many requests")):
            return "rate_limit"
        if any(kw in msg for kw in (
            "timeout", "timed out", "connection", "network",
            "503", "502", "500", "internal server error",
            "service unavailable", "server error",
        )):
            return "transient"

        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)

    return "permanent"


def _extract_retry_delay(exc: BaseException) -> float | None:
    """Try to extract a Retry-After delay (in seconds) from response headers."""
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {})
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass
    return None


# ---------------------------------------------------------------------------
# 3. Lazy LLM Client
# ---------------------------------------------------------------------------

_llm = None
_llm_structured_cache: dict = {}


def _create_llm():
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()

    if provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

        if not all([endpoint, api_key, deployment]):
            missing = []
            if not endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not deployment:
                missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
            raise ValueError(
                f"Azure OpenAI is missing required configuration: {', '.join(missing)}"
            )

        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            azure_deployment=deployment,
            temperature=0,
        )

    if provider != "deepseek":
        print(f"Warning: unknown LLM_PROVIDER '{provider}', falling back to deepseek")

    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(model="deepseek-chat", temperature=0)


def get_llm():
    """Lazy accessor for the base LLM instance."""
    global _llm
    if _llm is None:
        _llm = _create_llm()
    return _llm


def get_llm_structured(schema_cls):
    """Lazy accessor for a structured-output LLM bound to *schema_cls*."""
    key = id(schema_cls)
    if key not in _llm_structured_cache:
        _llm_structured_cache[key] = get_llm().with_structured_output(schema_cls)
    return _llm_structured_cache[key]


# ---------------------------------------------------------------------------
# 4. Retry Wrapper
# ---------------------------------------------------------------------------


def invoke_with_retry(llm_structured, prompt: str, max_retries: int = 3):
    """Invoke the LLM with structured output, retrying transient errors
    with exponential backoff.  Permanent errors propagate immediately."""
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return llm_structured.invoke(prompt)
        except Exception as exc:
            last_exc = exc
            error_type = classify_llm_error(exc)

            if error_type == "permanent":
                raise LLMPermanentError(str(exc)) from exc

            if attempt >= max_retries:
                raise LLMTransientError(
                    f"LLM invocation failed after {max_retries + 1} attempts: {exc}"
                ) from exc

            if error_type == "rate_limit":
                delay = _extract_retry_delay(exc) or (2 ** attempt)
            else:
                delay = 2 ** attempt

            print(
                f"[retry {attempt + 1}/{max_retries}] LLM error: {exc}",
                file=sys.stderr,
            )
            print(f"  waiting {delay:.1f}s before next attempt ...", file=sys.stderr)
            time.sleep(delay)


# ---------------------------------------------------------------------------
# 5. Prompt Builder
# ---------------------------------------------------------------------------


def build_extraction_prompt(
    idx: int,
    total_chunks: int,
    chunk_text: str,
    domain_instructions: str,
    context: str,
) -> str:
    domain_block = ""
    if domain_instructions:
        domain_block = f"\nDomain-Specific Instructions:\n{domain_instructions}\n"

    return f"""You are an expert data engineer analyzing a file format specification. This is chunk {idx + 1} of {total_chunks}.{domain_block}

    Previous extraction context:
    {context}

    Specification Chunk:
    ---
    {chunk_text}
    ---

    Instructions:
    1. Extract file-level metadata (format, encoding, delimiter, naming convention) if mentioned in THIS chunk. If the context shows an incomplete or missing file-level value, re-extract it fully from this chunk.
    2. Extract all fields from THIS chunk. For each field:
       - 'field_group': Must be either 'header' or 'content'.
       - 'field_index': The exact 0-based offset/index from the specification (e.g., Tab Offset, Field Position). Use the explicit index from the source — do NOT renumber or continue from the previous chunk.
       - 'field_name': The exact field name.
       - 'data_type': The data type with max length/precision if defined (e.g., 'string (50)').
       - 'description': Full field description details.

    CRITICAL - Handling partial / cross-chunk information:
    - Adjacent chunks overlap by 50 lines. If a field definition starts near the end of one chunk, it will appear fully in the overlap zone of the next chunk.
    - If a field in the previous context is marked [INCOMPLETE], and you see its FULL definition in THIS chunk, RE-EXTRACT it with ALL available information (name, type, index, complete description). Do NOT skip an incomplete field.
    - If a field's DESCRIPTION starts in one chunk and continues here (runs across the chunk boundary), stitch it together: include the full description from beginning to end.
    - If file-level metadata appears partially in context, re-extract it completely from this chunk.
    - Do NOT re-extract fields that are already COMPLETE (have name, type, index, and description) in the extracted list.
    """
