import asyncio

from fastapi import APIRouter, HTTPException

from server.api.schemas import (
    ExtractionResult,
    FeedbackRound,
    OKResponse,
    ReviewData,
    ReviewSubmit,
)
from src.agent import build_interactive_graph
from src.session_manager import SessionStore, get_sqlite_saver
from src.state import AgentState
from src.storage import InputStore
from src.llm import summarize_feedback

router = APIRouter(tags=["Review"])
session_store = SessionStore()
input_store = InputStore()


def _get_meta_and_config(session_id: str):
    meta = session_store.get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Session not found")
    config = session_store.get_langgraph_config(session_id)
    return meta, config


@router.get(
    "/api/sessions/{session_id}/review",
    response_model=ReviewData,
)
async def get_review_data(session_id: str):
    meta, config = _get_meta_and_config(session_id)

    with get_sqlite_saver() as checkpointer:
        graph = build_interactive_graph(checkpointer)

        state = await asyncio.to_thread(graph.get_state, config)

        if state.values is None or len(state.values) == 0:
            raise HTTPException(
                status_code=404,
                detail="Session has no stored state. Run extraction first.",
            )

        values = state.values

        result = ExtractionResult(
            file_metadata=values.get("file_metadata", {}),
            fields=values.get("fields", []),
            warnings=values.get("warnings", []),
            feedback_rounds=[
                FeedbackRound(**fr) for fr in meta.feedback_rounds
            ],
        )

    return ReviewData(
        session_id=session_id,
        domain=meta.domain,
        source=meta.source,
        status=meta.status,
        result=result,
        feedback_rounds=[FeedbackRound(**fr) for fr in meta.feedback_rounds],
    )


@router.post("/api/sessions/{session_id}/review", response_model=OKResponse)
async def submit_review(session_id: str, body: ReviewSubmit):
    meta, config = _get_meta_and_config(session_id)
    decision = body.decision.lower()

    if decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400, detail="Decision must be 'approved' or 'rejected'"
        )

    human_feedback = body.feedback.strip()

    with get_sqlite_saver() as checkpointer:
        graph = build_interactive_graph(checkpointer)

        state = await asyncio.to_thread(graph.get_state, config)

        if decision == "rejected":
            session_store.add_feedback(session_id, human_feedback)
            if human_feedback:
                prev = state.values.get("accumulated_instructions", "") or ""
                combined = f"{prev}\n\n{human_feedback}" if prev else human_feedback
                session_store.set_accumulated_instructions(session_id, combined)

            resume_state: AgentState = {
                "review_decision": "rejected",
                "human_feedback": human_feedback,
            }
            graph.update_state(config, resume_state)
            await asyncio.to_thread(graph.invoke, None, config)
            session_store.update_status(session_id, "draft")

        else:
            resume_state: AgentState = {
                "review_decision": "approved",
                "human_feedback": "",
            }
            graph.update_state(config, resume_state)
            await asyncio.to_thread(graph.invoke, None, config)
            session_store.update_status(session_id, "approved")

    if decision == "approved" and meta.feedback_rounds:
        try:
            existing = input_store.get_instructions(meta.domain)
            summary = summarize_feedback(
                meta.domain, meta.source, meta.feedback_rounds, existing
            )
            input_store.save_instructions(meta.domain, summary)
        except Exception:
            pass

    return OKResponse()
