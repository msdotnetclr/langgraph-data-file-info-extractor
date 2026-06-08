import shutil

import pytest

from src.nodes import (
    after_review_route,
    incorporate_feedback,
)
from src.state import AgentState
from src.session_manager import SESSIONS_ROOT
from langgraph.graph import END

TEST_SESSIONS = SESSIONS_ROOT


@pytest.fixture(autouse=True)
def clean_sessions():
    if TEST_SESSIONS.exists():
        shutil.rmtree(TEST_SESSIONS)
    yield
    if TEST_SESSIONS.exists():
        shutil.rmtree(TEST_SESSIONS)


class TestAfterReviewRoute:
    def test_approved_routes_to_store(self):
        state: AgentState = {"review_decision": "approved"}
        assert after_review_route(state) == "store_approved_result"

    def test_rejected_routes_to_feedback(self):
        state: AgentState = {"review_decision": "rejected"}
        assert after_review_route(state) == "incorporate_feedback"

    def test_capitalization_variants(self):
        assert after_review_route({"review_decision": "Approved"}) == "store_approved_result"
        assert after_review_route({"review_decision": "REJECTED"}) == "incorporate_feedback"

    def test_empty_decision_routes_to_end(self):
        assert after_review_route({"review_decision": ""}) is END
        assert after_review_route({"review_decision": "unknown"}) is END


class TestIncorporateFeedback:
    def test_appends_feedback_to_existing_instructions(self):
        state: AgentState = {
            "domain_instructions": "# Original\nUse tab delimiter",
            "human_feedback": "The delimiter is actually pipe",
        }
        result = incorporate_feedback(state)
        assert "Original" in result["domain_instructions"]
        assert "pipe" in result["domain_instructions"]
        assert result["current_chunk_index"] == 0
        assert result["partial_fields"] == []

    def test_no_feedback_preserves_original(self):
        state: AgentState = {
            "domain_instructions": "# Original\nUse tab delimiter",
            "human_feedback": "",
        }
        result = incorporate_feedback(state)
        assert result["domain_instructions"] == "# Original\nUse tab delimiter"

    def test_feedback_only_no_prior_instructions(self):
        state: AgentState = {
            "domain_instructions": "",
            "human_feedback": "Use ANSI encoding",
        }
        result = incorporate_feedback(state)
        assert "ANSI encoding" in result["domain_instructions"]

    def test_resets_extraction_state(self):
        state: AgentState = {
            "domain_instructions": "orig",
            "human_feedback": "test",
            "current_chunk_index": 5,
            "partial_fields": [{"name": "foo"}],
            "extracted_data": [{"some": "data"}],
            "file_metadata": {"encoding": "UTF-8"},
            "fields": [{"name": "bar"}],
            "review_decision": "rejected",
        }
        result = incorporate_feedback(state)
        assert result["current_chunk_index"] == 0
        assert result["partial_fields"] == []
        assert result["extracted_data"] == []
        assert result["file_metadata"] == {}
        assert result["fields"] == []
        assert result["review_decision"] == ""
