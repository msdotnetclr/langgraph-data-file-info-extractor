from fastapi import APIRouter, HTTPException

from server.api.schemas import (
    FeedbackRound,
    OKResponse,
    SessionCreate,
    SessionInfo,
)
from src.session_manager import SessionStore

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
store = SessionStore()


@router.get("", response_model=list[SessionInfo])
async def list_sessions(status: str = "", domain: str = ""):
    status_filter = status if status in ("created", "in_progress", "draft", "approved", "failed") else None
    domain_filter = domain if domain else None
    sessions = store.list_sessions(status=status_filter, domain=domain_filter)
    return [
        SessionInfo(
            session_id=s.session_id,
            domain=s.domain,
            source=s.source,
            status=s.status,
            created_at=s.created_at,
            last_modified_at=s.last_modified_at,
            feedback_rounds=[
                FeedbackRound(**fr) for fr in s.feedback_rounds
            ],
            accumulated_instructions=s.accumulated_instructions,
        )
        for s in sessions
    ]


@router.post("", response_model=SessionInfo, status_code=201)
async def create_session(body: SessionCreate):
    meta = store.create(domain=body.domain, source=body.source)
    return SessionInfo(
        session_id=meta.session_id,
        domain=meta.domain,
        source=meta.source,
        status=meta.status,
        created_at=meta.created_at,
        last_modified_at=meta.last_modified_at,
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    meta = store.get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(
        session_id=meta.session_id,
        domain=meta.domain,
        source=meta.source,
        status=meta.status,
        created_at=meta.created_at,
        last_modified_at=meta.last_modified_at,
        feedback_rounds=[FeedbackRound(**fr) for fr in meta.feedback_rounds],
        accumulated_instructions=meta.accumulated_instructions,
    )


@router.delete("/{session_id}", response_model=OKResponse)
async def delete_session(session_id: str):
    deleted = store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return OKResponse()
