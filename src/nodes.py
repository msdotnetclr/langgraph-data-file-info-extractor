import os
import re
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from langchain_deepseek import ChatDeepSeek

from src.state import AgentState


# ---------------------------------------------------------------------------
# 1. Pydantic Output Schemas
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    field_group: str = Field(description="The group of the field, either 'header' or 'content'")
    field_index: Optional[int] = Field(None, description="The position or offset of the field in the group (0-indexed)")
    field_name: str = Field(description="The name of the field")
    data_type: str = Field(description="The data type and length/precision of the field (e.g., 'string (50)', 'integer', 'datetime')")
    description: str = Field(description="Detailed explanation of the field's purpose and usage")


class ExtractedMetadata(BaseModel):
    file_format: Optional[str] = Field(None, description="The file format, e.g., 'Tab-delimited', 'CSV', 'Fixed-width'")
    encoding: Optional[str] = Field(None, description="The file encoding, e.g., 'ANSI', 'UTF-8'")
    delimiter: Optional[str] = Field(None, description="The file delimiter, e.g., 'Tab', '0x09', 'Comma'")
    naming_convention: Optional[str] = Field(None, description="The naming convention pattern of the file, e.g., 'yyyyMMddhhmm_CUSTOMER.TXT'")
    fields: List[ExtractedField] = Field(default_factory=list, description="List of fields extracted from this chunk")


class FileMetadata(BaseModel):
    file_format: Optional[str] = Field(None, description="Format of the file")
    encoding: Optional[str] = Field(None, description="Encoding of the file")
    delimiter: Optional[str] = Field(None, description="Delimiter character or description")
    naming_convention: Optional[str] = Field(None, description="Naming convention pattern of the file")


class SpecificationMetadata(BaseModel):
    file_metadata: FileMetadata = Field(description="File-level metadata properties")
    fields: List[ExtractedField] = Field(description="Complete list of field-level metadata entries")


# ---------------------------------------------------------------------------
# 2. Overlapping Line-Based Splitter
# ---------------------------------------------------------------------------

def split_text_into_chunks(
    text: str,
    lines_per_chunk: int = 500,
    overlap_lines: int = 50,
) -> List[str]:
    """
    Split text into overlapping chunks by line count.
    Each chunk (except possibly the last) has `lines_per_chunk` lines.
    Adjacent chunks overlap by `overlap_lines` lines so that no field
    definition is ever cut at a chunk boundary.
    """
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    chunks: List[str] = []
    start = 0
    while start < len(lines):
        end = min(start + lines_per_chunk, len(lines))
        chunks.append("\n".join(lines[start:end]))
        if end >= len(lines):
            break
        start = end - overlap_lines
    return chunks


# =====================================================================
# 3. LangGraph Nodes
# =====================================================================

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

    return ChatDeepSeek(model="deepseek-chat", temperature=0)


llm = _create_llm()
llm_structured = llm.with_structured_output(ExtractedMetadata)


def split_specification(state: AgentState):
    raw_text = state["raw_specification"]
    chunks = split_text_into_chunks(raw_text)
    return {
        "chunks": chunks,
        "current_chunk_index": 0,
        "partial_fields": [],
        "warnings": [],
    }


def _field_is_complete(f: Dict[str, Any]) -> bool:
    return bool(
        f.get("field_name")
        and f.get("data_type")
        and f.get("description")
        and f.get("field_index") is not None
    )


def _build_context_from_previous(partial_fields: List[Dict[str, Any]]) -> str:
    if not partial_fields:
        return "No fields have been extracted yet. This is the first chunk."

    last = partial_fields[-1]
    last_group = last.get("field_group", "content")
    last_index = last.get("field_index", "unknown")
    last_name = last.get("field_name", "unknown")

    recent = partial_fields[-10:]
    recent_summary = []
    incomplete_warnings = []
    for f in recent:
        complete = _field_is_complete(f)
        marker = "" if complete else " [INCOMPLETE - re-extract if seen]"
        recent_summary.append(
            f"  [{f.get('field_group','')}] idx={f.get('field_index','?')} "
            f"name='{f.get('field_name','')}' type='{f.get('data_type','')}'{marker}"
        )
        if not complete:
            missing = []
            if not f.get("field_name"):
                missing.append("field_name")
            if not f.get("data_type"):
                missing.append("data_type")
            if f.get("field_index") is None:
                missing.append("field_index")
            if not f.get("description"):
                missing.append("description")
            incomplete_warnings.append(
                f"  WARNING: '{f.get('field_name','?')}' is missing: {', '.join(missing)}"
            )

    parts = [
        f"{len(partial_fields)} fields have been extracted so far.",
        f"The LAST extracted field was '{last_name}' "
        f"(group: {last_group}, index: {last_index}).",
        f"Continue extraction starting from the NEXT field after this one.",
        f"IMPORTANT: Do NOT re-extract fields that are already COMPLETE in the extracted list.",
    ]
    if incomplete_warnings:
        parts.append(
            "HOWEVER, some previously-extracted fields are INCOMPLETE "
            "(shown with [INCOMPLETE] above). If you see their full definition "
            "in this chunk, RE-EXTRACT them with complete information."
        )
        parts.extend(incomplete_warnings)

    parts.append(f"Last {len(recent)} extracted fields:")
    parts.extend(recent_summary)

    return "\n".join(parts)


def _make_key(f: Dict[str, Any]):
    idx = f.get("field_index")
    if idx is not None:
        return (f.get("field_group"), idx)
    return (
        f.get("field_group"),
        f.get("field_name", "").strip().lower(),
    )


def _merge_fields(
    existing: List[Dict[str, Any]],
    new_fields: List[Dict[str, Any]],
) -> tuple:
    merged = list(existing)
    warnings: List[str] = []

    for f in new_fields:
        new_key = _make_key(f)
        match_idx = _find_match(merged, f, new_key)

        if match_idx is not None:
            merged[match_idx] = _pick_best_version(merged[match_idx], f)
        else:
            group = f.get("field_group")
            name_lower = f.get("field_name", "").strip().lower()
            if group and name_lower:
                same_name_fields = [
                    ef for ef in merged
                    if ef.get("field_group") == group
                    and ef.get("field_name", "").strip().lower() == name_lower
                ]
                if same_name_fields:
                    base_name = f["field_name"]
                    all_names = {
                        ef.get("field_name")
                        for ef in merged
                        if ef.get("field_group") == group
                    }
                    all_names.add(base_name)
                    counter = 2
                    while True:
                        candidate = f"{base_name}({counter})"
                        if candidate not in all_names:
                            break
                        counter += 1
                    f = dict(f)
                    f["field_name"] = candidate
                    warnings.append(
                        f"Duplicate field name '{base_name}' in group '{group}' "
                        f"at index {f.get('field_index')} — renamed to '{candidate}'"
                    )

            merged.append(f)

    return merged, warnings


def _find_match(
    merged: List[Dict[str, Any]],
    new_field: Dict[str, Any],
    new_key: tuple,
) -> Optional[int]:
    for i, ef in enumerate(merged):
        ek = _make_key(ef)
        if ek == new_key:
            return i
    return None


def _pick_best_version(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> Dict[str, Any]:
    """Return a merged dict taking the most complete value for each key."""
    result: Dict[str, Any] = {}

    for attr in ("field_group", "field_name", "data_type", "description", "field_index"):
        va = a.get(attr)
        vb = b.get(attr)

        if attr == "description":
            result[attr] = vb if len(vb or "") > len(va or "") else va
        elif attr == "field_index":
            result[attr] = vb if vb is not None else va
        elif attr == "field_group":
            result[attr] = vb if vb else va
        elif attr == "field_name":
            result[attr] = va if va else vb
        else:
            result[attr] = vb if vb else va

    return result


def extract_next_chunk(state: AgentState):
    idx = state["current_chunk_index"]
    chunks = state["chunks"]
    partial_fields = state.get("partial_fields", [])
    chunk_text = chunks[idx]

    domain_instructions = state.get("domain_instructions", "").strip()

    context = _build_context_from_previous(partial_fields)

    domain_block = ""
    if domain_instructions:
        domain_block = f"\nDomain-Specific Instructions:\n{domain_instructions}\n"

    prompt = f"""You are an expert data engineer analyzing a file format specification. This is chunk {idx + 1} of {len(chunks)}.{domain_block}

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

    try:
        response = llm_structured.invoke(prompt)

        new_fields = [f.model_dump() for f in response.fields]

        merged_fields, merge_warnings = _merge_fields(partial_fields, new_fields)

        file_meta = {
            "file_format": response.file_format,
            "encoding": response.encoding,
            "delimiter": response.delimiter,
            "naming_convention": response.naming_convention,
        }

        return {
            "partial_fields": merged_fields,
            "extracted_data": [{"file_metadata": file_meta, "fields": new_fields}],
            "current_chunk_index": idx + 1,
            "warnings": merge_warnings,
        }
    except Exception as e:
        print(f"Error in extract_next_chunk (chunk {idx}): {e}")
        return {
            "current_chunk_index": idx + 1,
            "extracted_data": [],
        }


def should_continue(state: AgentState) -> str:
    if state["current_chunk_index"] < len(state["chunks"]):
        return "extract_next_chunk"
    return "reduce_results"


def _value_is_better(incoming: Any, existing: Any) -> bool:
    """Return True if incoming is a more complete value than existing."""
    if incoming is None or (isinstance(incoming, str) and not incoming.strip()):
        return False
    if existing is None or (isinstance(existing, str) and not existing.strip()):
        return True
    if isinstance(incoming, str) and isinstance(existing, str):
        return len(incoming) > len(existing)
    return False


def reduce_results(state: AgentState):
    accumulated = state.get("extracted_data", [])
    partial_fields = state.get("partial_fields", [])

    final_file_meta: Dict[str, Any] = {
        "file_format": None,
        "encoding": None,
        "delimiter": None,
        "naming_convention": None,
    }

    for item in accumulated:
        meta = item.get("file_metadata", {})
        for key in final_file_meta:
            existing = final_file_meta[key]
            incoming = meta.get(key)
            if _value_is_better(incoming, existing):
                final_file_meta[key] = incoming

    header_fields = []
    content_fields = []
    other_fields = []

    for f in partial_fields:
        group = f.get("field_group", "").lower()
        if "header" in group:
            group = "header"
            f["field_group"] = group
            header_fields.append(f)
        elif "content" in group:
            group = "content"
            f["field_group"] = group
            content_fields.append(f)
        else:
            other_fields.append(f)

    def sort_key(x):
        idx = x.get("field_index")
        return idx if idx is not None else 999999

    header_fields.sort(key=sort_key)
    content_fields.sort(key=sort_key)
    other_fields.sort(key=sort_key)

    final_fields = header_fields + content_fields + other_fields

    return {
        "file_metadata": final_file_meta,
        "fields": final_fields,
        "warnings": state.get("warnings", []),
    }
