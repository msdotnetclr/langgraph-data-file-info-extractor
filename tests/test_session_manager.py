import shutil

import pytest

from src.session_manager import SessionStore, SessionMeta, SESSIONS_ROOT

TEST_SESSIONS = SESSIONS_ROOT


@pytest.fixture(autouse=True)
def clean_sessions():
    if TEST_SESSIONS.exists():
        shutil.rmtree(TEST_SESSIONS)
    yield
    if TEST_SESSIONS.exists():
        shutil.rmtree(TEST_SESSIONS)


class TestSessionStore:
    def test_create_session(self):
        store = SessionStore()
        meta = store.create("my-domain", "my-source")
        assert meta.session_id is not None
        assert meta.domain == "my-domain"
        assert meta.source == "my-source"
        assert meta.status == "created"
        assert meta.feedback_rounds == []

    def test_create_session_custom_id(self):
        store = SessionStore()
        meta = store.create("d", "s", session_id="abc-123")
        assert meta.session_id == "abc-123"

    def test_get_session_returns_none_for_missing(self):
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_get_session_after_create(self):
        store = SessionStore()
        created = store.create("d", "s")
        store.persist_meta(created)
        fetched = store.get(created.session_id)
        assert fetched is not None
        assert fetched.domain == "d"
        assert fetched.source == "s"

    def test_update_status(self):
        store = SessionStore()
        meta = store.create("d", "s")
        store.persist_meta(meta)
        updated = store.update_status(meta.session_id, "draft")
        assert updated is not None
        assert updated.status == "draft"

    def test_update_status_missing(self):
        store = SessionStore()
        assert store.update_status("nope", "draft") is None

    def test_add_feedback(self):
        store = SessionStore()
        meta = store.create("d", "s")
        store.persist_meta(meta)
        updated = store.add_feedback(meta.session_id, "Need pipe delimiter")
        assert updated is not None
        assert len(updated.feedback_rounds) == 1
        assert updated.feedback_rounds[0]["feedback_text"] == "Need pipe delimiter"
        assert updated.feedback_rounds[0]["decision"] == "rejected"

    def test_add_multiple_feedback_rounds(self):
        store = SessionStore()
        meta = store.create("d", "s")
        store.persist_meta(meta)
        store.add_feedback(meta.session_id, "Round 1")
        store.add_feedback(meta.session_id, "Round 2")
        fetched = store.get(meta.session_id)
        assert len(fetched.feedback_rounds) == 2
        assert fetched.feedback_rounds[0]["round"] == 1
        assert fetched.feedback_rounds[1]["round"] == 2

    def test_set_accumulated_instructions(self):
        store = SessionStore()
        meta = store.create("d", "s")
        store.persist_meta(meta)
        store.add_feedback(meta.session_id, "Use pipe")
        store.add_feedback(meta.session_id, "ANSI encoding")
        updated = store.set_accumulated_instructions(
            meta.session_id, "Use pipe\nANSI encoding"
        )
        assert updated.accumulated_instructions == "Use pipe\nANSI encoding"

    def test_list_sessions_filter_by_status(self):
        store = SessionStore()
        a = store.create("d1", "s1")
        b = store.create("d2", "s2")
        store.persist_meta(a)
        store.persist_meta(b)
        store.update_status(b.session_id, "draft")

        drafts = store.list_sessions(status="draft")
        assert len(drafts) == 1
        assert drafts[0].session_id == b.session_id

        created = store.list_sessions(status="created")
        assert len(created) == 1
        assert created[0].session_id == a.session_id

    def test_list_sessions_filter_by_domain(self):
        store = SessionStore()
        a = store.create("dom-a", "s1")
        b = store.create("dom-b", "s2")
        c = store.create("dom-a", "s3")
        store.persist_meta(a)
        store.persist_meta(b)
        store.persist_meta(c)

        filtered = store.list_sessions(domain="dom-a")
        assert len(filtered) == 2

    def test_delete_session(self):
        store = SessionStore()
        meta = store.create("d", "s")
        store.persist_meta(meta)
        assert store.delete(meta.session_id) is True
        assert store.get(meta.session_id) is None

    def test_delete_nonexistent(self):
        store = SessionStore()
        assert store.delete("nope") is False

    def test_get_langgraph_config(self):
        store = SessionStore()
        meta = store.create("d", "s")
        config = store.get_langgraph_config(meta.session_id)
        assert config == {
            "configurable": {"thread_id": meta.session_id},
        }
