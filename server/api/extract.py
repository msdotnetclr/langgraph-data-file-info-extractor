import asyncio
import json
import os
import tempfile

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from server.api.schemas import SessionInfo
from src.agent import build_interactive_graph, build_graph
from src.session_manager import SessionStore, get_sqlite_saver
from src.state import AgentState
from src.storage import InputStore

router = APIRouter(tags=["Extract"])
session_store = SessionStore()
input_store = InputStore()


async def event_generator(session_id: str):
    meta = session_store.get(session_id)
    if meta is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
        return

    domain = meta.domain
    source = meta.source

    if not input_store.domain_exists(domain):
        yield f"data: {json.dumps({'type': 'error', 'message': f'Domain {domain} not found'})}\n\n"
        return
    if not input_store.source_exists(domain, source):
        yield f"data: {json.dumps({'type': 'error', 'message': f'Source {source} not found'})}\n\n"
        return

    spec_file = str(input_store._source_path(domain, source) / "source_specs.md")
    if not input_store.has_spec(domain, source):
        yield f"data: {json.dumps({'type': 'error', 'message': 'No source_specs.md found for this source'})}\n\n"
        return

    domain_instructions = input_store.get_instructions(domain)

    checkpointer = get_sqlite_saver()
    graph = build_interactive_graph(checkpointer)
    config = session_store.get_langgraph_config(session_id)

    initial_state: AgentState = {
        "spec_file": spec_file,
        "spec_file_size": 0,
        "chunk_ranges": [],
        "current_chunk_index": 0,
        "partial_fields": [],
        "extracted_data": [],
        "file_metadata": {},
        "fields": [],
        "domain_instructions": domain_instructions,
        "warnings": [],
        "session_id": session_id,
        "domain": domain,
        "source": source,
        "review_decision": "",
        "human_feedback": "",
        "feedback_rounds": [],
        "approved": False,
        "status": "in_progress",
    }

    session_store.update_status(session_id, "in_progress")

    total_chunks = 0

    try:
        async for event in graph.astream(initial_state, config, stream_mode="updates"):
            node_name = list(event.keys())[0]
            node_data = event[node_name]

            if node_name == "split_specification":
                total_chunks = len(node_data.get("chunk_ranges", []))
                yield f"data: {json.dumps({'type': 'status', 'phase': 'chunking', 'chunks': total_chunks})}\n\n"
                await asyncio.sleep(0)

            elif node_name == "extract_next_chunk":
                idx = node_data.get("current_chunk_index", 0)
                yield f"data: {json.dumps({'type': 'progress', 'phase': 'extracting', 'chunk': min(idx + 1, total_chunks), 'total': total_chunks})}\n\n"
                await asyncio.sleep(0)

            elif node_name == "reduce_results":
                yield f"data: {json.dumps({'type': 'status', 'phase': 'reducing'})}\n\n"
                await asyncio.sleep(0)

            elif node_name == "review_results":
                session_store.update_status(session_id, "draft")
                yield f"data: {json.dumps({'type': 'complete', 'session_id': session_id, 'status': 'draft'})}\n\n"
                return

    except Exception as e:
        session_store.update_status(session_id, "failed")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/api/sessions/{session_id}/start")
async def start_extraction(session_id: str):
    meta = session_store.get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        event_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/extract")
async def extract_stateless(
    content: str = Query("", alias="content"),
    domain: str = Query(""),
    instructions_file: str = Query(""),
):
    graph = build_graph()

    if content.strip():
        fd, spec_file = tempfile.mkstemp(suffix=".txt", prefix="extract_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        raise HTTPException(status_code=400, detail="No content provided")

    domain_instructions = ""
    if domain and input_store.domain_exists(domain):
        domain_instructions = input_store.get_instructions(domain)

    if instructions_file:
        try:
            with open(instructions_file, "r", encoding="utf-8") as f:
                domain_instructions = f.read().strip()
        except Exception:
            pass

    initial_state: AgentState = {
        "spec_file": spec_file,
        "spec_file_size": 0,
        "chunk_ranges": [],
        "current_chunk_index": 0,
        "partial_fields": [],
        "extracted_data": [],
        "file_metadata": {},
        "fields": [],
        "domain_instructions": domain_instructions,
        "warnings": [],
    }

    try:
        result = graph.invoke(initial_state)
    except Exception as e:
        try:
            os.unlink(spec_file)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    try:
        os.unlink(spec_file)
    except OSError:
        pass

    return {
        "file_metadata": result.get("file_metadata", {}),
        "fields": result.get("fields", []),
        "warnings": result.get("warnings", []),
    }

