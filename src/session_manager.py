import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver

from src.storage import DATA_ROOT

SESSIONS_ROOT = DATA_ROOT / "sessions"
CHECKPOINT_DB = SESSIONS_ROOT / "checkpoints.db"


def get_sqlite_saver() -> SqliteSaver:
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(CHECKPOINT_DB))


class SessionMeta:
    def __init__(
        self,
        session_id: str,
        domain: str,
        source: str,
        status: str = "created",
        created_at: Optional[str] = None,
        last_modified_at: Optional[str] = None,
        feedback_rounds: Optional[list[dict]] = None,
        accumulated_instructions: str = "",
    ):
        self.session_id = session_id
        self.domain = domain
        self.source = source
        self.status = status
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.last_modified_at = last_modified_at or now
        self.feedback_rounds = feedback_rounds or []
        self.accumulated_instructions = accumulated_instructions

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "domain": self.domain,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "last_modified_at": self.last_modified_at,
            "feedback_rounds": self.feedback_rounds,
            "accumulated_instructions": self.accumulated_instructions,
        }

    @staticmethod
    def from_dict(data: dict) -> "SessionMeta":
        return SessionMeta(**data)


class SessionStore:
    @staticmethod
    def _session_dir(session_id: str) -> Path:
        return SESSIONS_ROOT / session_id

    @staticmethod
    def _metadata_file(session_id: str) -> Path:
        return SessionStore._session_dir(session_id) / "metadata.json"

    def create(
        self,
        domain: str,
        source: str,
        session_id: Optional[str] = None,
    ) -> SessionMeta:
        sid = session_id or str(uuid.uuid4())
        return SessionMeta(
            session_id=sid,
            domain=domain,
            source=source,
            status="created",
        )

    def persist_meta(self, meta: SessionMeta) -> None:
        self._save_meta(meta)

    def get(self, session_id: str) -> Optional[SessionMeta]:
        file = self._metadata_file(session_id)
        if not file.exists():
            return None
        return SessionMeta.from_dict(json.loads(file.read_text(encoding="utf-8")))

    def update_status(self, session_id: str, status: str) -> Optional[SessionMeta]:
        meta = self.get(session_id)
        if meta is None:
            return None
        meta.status = status
        meta.last_modified_at = datetime.now(timezone.utc).isoformat()
        self._save_meta(meta)
        return meta

    def add_feedback(
        self,
        session_id: str,
        feedback_text: str,
    ) -> Optional[SessionMeta]:
        meta = self.get(session_id)
        if meta is None:
            return None
        meta.feedback_rounds.append({
            "round": len(meta.feedback_rounds) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feedback_text": feedback_text,
            "decision": "rejected",
        })
        meta.last_modified_at = datetime.now(timezone.utc).isoformat()
        self._save_meta(meta)
        return meta

    def set_accumulated_instructions(
        self, session_id: str, instructions: str
    ) -> Optional[SessionMeta]:
        meta = self.get(session_id)
        if meta is None:
            return None
        meta.accumulated_instructions = instructions
        meta.last_modified_at = datetime.now(timezone.utc).isoformat()
        self._save_meta(meta)
        return meta

    def list_sessions(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> list[SessionMeta]:
        if not SESSIONS_ROOT.exists():
            return []
        sessions = []
        for d in sorted(SESSIONS_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not d.is_dir():
                continue
            mf = d / "metadata.json"
            if not mf.exists():
                continue
            try:
                meta = SessionMeta.from_dict(json.loads(mf.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError):
                continue
            if status and meta.status != status:
                continue
            if domain and meta.domain != domain:
                continue
            sessions.append(meta)
        return sessions

    def delete(self, session_id: str) -> bool:
        path = self._session_dir(session_id)
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def get_langgraph_config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def _save_meta(self, meta: SessionMeta) -> None:
        path = self._session_dir(meta.session_id)
        path.mkdir(parents=True, exist_ok=True)
        self._metadata_file(meta.session_id).write_text(
            json.dumps(meta.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
