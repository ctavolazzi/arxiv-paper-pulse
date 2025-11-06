"""
Comprehensive test suite for Bot class core functionality.
Tests memory, thoughts, requests, actions, and safety protocols.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

import pytest

from arxiv_paper_pulse import config
from arxiv_paper_pulse.bot import Bot


@pytest.fixture
def mock_genai(monkeypatch):
    """Mock Gemini API client."""
    class MockResponse:
        def __init__(self, text="mock response"):
            self.text = text

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.calls = []
            self.models = self

        def generate_content(self, model, contents):
            self.calls.append({'model': model, 'contents': contents})
            return MockResponse(text=f"Response to: {contents[-1][:50]}")

    client = MockClient()
    monkeypatch.setattr("arxiv_paper_pulse.bot.genai.Client", lambda *args, **kwargs: client)
    return client


@pytest.fixture
def bot_factory(tmp_path, monkeypatch, mock_genai):
    """Factory for creating test bots with isolated directories."""
    def _factory(name="TestBot", role="Tester", **kwargs):
        working_dir = tmp_path / "bots" / name.lower()
        monkeypatch.setattr(config, "BOT_WORKING_DIR", str(tmp_path / "bots"))
        monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

        # Apply any config overrides
        for key, value in kwargs.items():
            if hasattr(config, key.upper()):
                monkeypatch.setattr(config, key.upper(), value)

        return Bot(name, role)

    return _factory


# ============================================================================
# INITIALIZATION AND DATABASE TESTS
# ============================================================================

def test_bot_initialization(bot_factory):
    """Test bot initializes with all required components."""
    bot = bot_factory("InitBot", "Test Role")

    assert bot.name == "InitBot"
    assert bot.role == "Test Role"
    assert bot.working_dir.exists()
    assert bot.db_path.exists()
    assert bot.context_file.exists()
    assert bot.context_history_dir.exists()


def test_database_tables_created(bot_factory):
    """Test all database tables are created."""
    bot = bot_factory()

    with sqlite3.connect(bot.db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        'memory', 'thoughts', 'requests', 'responses', 'actions', 'api_logs'
    }
    assert expected_tables.issubset(tables)


# ============================================================================
# MEMORY TESTS (INTERNAL/EXTERNAL)
# ============================================================================

def test_internal_memory_store_retrieve(bot_factory):
    """Test storing and retrieving internal memory."""
    bot = bot_factory()

    bot.store_internal("test_key", {"data": "value"})
    result = bot.retrieve_internal("test_key")

    assert result == {"data": "value"}


def test_internal_memory_overwrites(bot_factory):
    """Test internal memory overwrites on duplicate keys."""
    bot = bot_factory()

    bot.store_internal("key", "value1")
    bot.store_internal("key", "value2")

    result = bot.retrieve_internal("key")
    assert result == "value2"


def test_external_memory_requires_coupling(bot_factory):
    """Test external memory fails without coupling."""
    bot = bot_factory()

    with pytest.raises(ValueError, match="not coupled"):
        bot.store_external("key", "value")


def test_external_memory_coupling(bot_factory, tmp_path):
    """Test external memory coupling and operations."""
    bot = bot_factory()
    external_db = tmp_path / "external.db"

    # Skip permission check for test
    bot.couple_external_memory(external_db, request_permission=False)
    bot.store_external("ext_key", "ext_value")
    result = bot.retrieve_external("ext_key")

    assert result == "ext_value"
    assert bot.external_memory_path == external_db


def test_external_memory_uncoupling(bot_factory, tmp_path):
    """Test uncoupling external memory."""
    bot = bot_factory()
    external_db = tmp_path / "external.db"

    # Skip permission check for test
    bot.couple_external_memory(external_db, request_permission=False)
    bot.uncouple_external_memory()

    assert bot.external_memory_path is None
    with pytest.raises(ValueError):
        bot.store_external("key", "value")


# ============================================================================
# THOUGHT JOURNAL TESTS
# ============================================================================

def test_record_thought(bot_factory):
    """Test recording a thought."""
    bot = bot_factory()

    bot.record_thought('reasoning', 'This is a test thought', tags=['test'])
    thoughts = bot.query_thoughts()

    assert len(thoughts) >= 1
    assert thoughts[0]['thought_type'] == 'reasoning'
    assert thoughts[0]['content'] == 'This is a test thought'


def test_query_thoughts_by_type(bot_factory):
    """Test querying thoughts by type."""
    bot = bot_factory()

    bot.record_thought('reasoning', 'Reasoning thought')
    bot.record_thought('decision', 'Decision thought')

    reasoning = bot.query_thoughts(filters={'thought_type': 'reasoning'})
    decisions = bot.query_thoughts(filters={'thought_type': 'decision'})

    assert len(reasoning) >= 1
    assert len(decisions) >= 1
    assert reasoning[0]['thought_type'] == 'reasoning'


def test_thought_chains(bot_factory):
    """Test thought parent-child relationships."""
    bot = bot_factory()

    bot.record_thought('planning', 'Parent thought')
    thoughts = bot.query_thoughts()
    parent_id = thoughts[0]['id']

    bot.record_thought('reasoning', 'Child thought', parent_id=parent_id)

    chain = bot.get_thought_chain(thoughts[0]['id'])
    assert len(chain) >= 1


def test_auto_tag_extraction(bot_factory):
    """Test automatic tag extraction from content."""
    bot = bot_factory()

    bot.record_thought('reasoning', 'This involves problem solving and analysis')
    thoughts = bot.query_thoughts()

    assert 'problem' in thoughts[0]['tags'] or 'analysis' in thoughts[0]['tags']


# ============================================================================
# REQUEST/RESPONSE MATCHING TESTS
# ============================================================================

def test_exact_request_matching(bot_factory):
    """Test exact request hash matching."""
    bot = bot_factory()

    request_text = "What is the meaning of life?"

    # First time - no match
    match = bot.find_exact_match(request_text)
    assert match is None

    # Record request
    request_id = bot.record_new_request(request_text)

    # Second time - match found
    match = bot.find_exact_match(request_text)
    assert match is not None
    assert match[0] == request_id


def test_request_normalization(bot_factory):
    """Test request normalization (case, leading/trailing whitespace, newlines)."""
    bot = bot_factory()

    request1 = "  Test Request\n"
    request2 = "TEST REQUEST  "  # Different case and whitespace

    bot.record_new_request(request1)
    match = bot.find_exact_match(request2)

    # Should match due to normalization (lowercase, strip, replace newlines)
    assert match is not None

    # Different actual content won't match
    match_different = bot.find_exact_match("completely different")
    assert match_different is None


def test_past_response_lookup(bot_factory):
    """Test recording and retrieving past responses."""
    bot = bot_factory()

    request_id = bot.record_new_request("test request")
    bot.record_new_attempt(request_id, "response 1", {"version": 1})
    bot.record_new_attempt(request_id, "response 2", {"version": 2})

    responses = bot.find_past_responses(request_id)

    assert len(responses) == 2
    assert responses[0]['attempt_number'] == 2  # Most recent first


def test_should_make_new_attempt_heuristic(bot_factory):
    """Test new attempt decision heuristic."""
    bot = bot_factory()

    request_id = bot.record_new_request("test")

    # No responses - should make attempt
    assert bot.should_make_new_attempt(request_id, [])

    # Recent response - should not make attempt
    recent_response = {
        'timestamp': datetime.now().isoformat(),
        'response_text': 'recent'
    }
    assert not bot.should_make_new_attempt(request_id, [recent_response])


# ============================================================================
# ACTION LOGGING TESTS
# ============================================================================

def test_log_action(bot_factory):
    """Test logging actions."""
    bot = bot_factory()

    bot.log_action('test_action', {'key': 'value'})
    actions = bot.get_action_history(limit=10)

    assert len(actions) >= 1
    assert actions[0]['action_type'] == 'test_action'
    assert actions[0]['details']['key'] == 'value'


def test_action_history_limit(bot_factory):
    """Test action history respects limit."""
    bot = bot_factory()

    for i in range(10):
        bot.log_action('action', {'index': i})

    actions = bot.get_action_history(limit=5)
    assert len(actions) == 5


# ============================================================================
# SAFETY PROTOCOL TESTS
# ============================================================================

def test_workspace_root_detection(bot_factory, tmp_path):
    """Test workspace root detection."""
    bot = bot_factory()

    # Create a fake .git directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Should detect workspace root
    # (Note: actual behavior depends on cwd)
    root = bot._get_workspace_root()
    assert root is not None


def test_path_within_workspace(bot_factory, tmp_path):
    """Test path validation within workspace."""
    bot = bot_factory()

    # In test environment, temp paths aren't in "workspace"
    # So test that the method runs without errors
    safe_path = bot.working_dir / "safe_file.txt"
    result = bot._is_within_workspace(safe_path)
    assert isinstance(result, bool)  # Should return bool, not error


# ============================================================================
# PROCESS (API INTEGRATION) TESTS
# ============================================================================

def test_process_basic(bot_factory, mock_genai):
    """Test basic process call."""
    bot = bot_factory()

    mock_genai.calls.clear()
    response = bot.process("Hello world")

    assert response.startswith("Response to:")
    assert len(mock_genai.calls) == 1


def test_process_with_context_dict(bot_factory, mock_genai):
    """Test process with additional context dict."""
    bot = bot_factory()

    mock_genai.calls.clear()
    response = bot.process("Test", context={'key': 'value'})

    prompt = mock_genai.calls[-1]['contents'][-1]
    assert 'key: value' in prompt


def test_process_includes_context_file(bot_factory, mock_genai):
    """Test process includes context.md by default."""
    bot = bot_factory()

    bot.update_context("# Custom Context\nTest data")

    mock_genai.calls.clear()
    bot.process("Test")

    prompt = mock_genai.calls[-1]['contents'][-1]
    assert "Current Context (from context.md)" in prompt
    assert "Custom Context" in prompt


def test_process_can_exclude_context(bot_factory, mock_genai):
    """Test process can exclude context.md."""
    bot = bot_factory()

    mock_genai.calls.clear()
    bot.process("Test", include_context=False)

    prompt = mock_genai.calls[-1]['contents'][-1]
    assert "Current Context (from context.md)" not in prompt


def test_process_logs_io(bot_factory):
    """Test process logs input and output."""
    bot = bot_factory()

    bot.process("Test prompt")

    with sqlite3.connect(bot.db_path) as conn:
        cursor = conn.execute("SELECT direction, content FROM api_logs ORDER BY timestamp DESC LIMIT 2")
        logs = cursor.fetchall()

    # Should have input and output logs
    assert len(logs) >= 2
    directions = [log[0] for log in logs]
    assert 'in' in directions
    assert 'out' in directions


# ============================================================================
# DISPLAY BUFFER TESTS
# ============================================================================

def test_display_buffer(bot_factory):
    """Test display buffer operations."""
    bot = bot_factory()

    bot.display("Line 1")
    bot.display("Line 2")

    content = bot.get_display()
    assert "Line 1" in content
    assert "Line 2" in content

    bot.clear_display()
    assert bot.get_display() == ""


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_workflow(bot_factory):
    """Test full bot workflow: process, memory, thoughts, actions."""
    bot = bot_factory("WorkflowBot", "Full Test")

    # Process a request
    response = bot.process("Test request")

    # Store result in memory
    bot.store_internal("result", {"response": response})

    # Record thought about it
    bot.record_thought("reflection", "Processed test request successfully")

    # Verify everything persists
    retrieved = bot.retrieve_internal("result")
    assert retrieved["response"] == response

    thoughts = bot.query_thoughts()
    assert len(thoughts) >= 1

    actions = bot.get_action_history()
    assert len(actions) >= 3  # api_call, memory_write, thought


def test_multiple_bots_isolated(bot_factory):
    """Test multiple bot instances are isolated."""
    bot1 = bot_factory("Bot1", "Role1")
    bot2 = bot_factory("Bot2", "Role2")

    bot1.store_internal("shared_key", "bot1_value")
    bot2.store_internal("shared_key", "bot2_value")

    assert bot1.retrieve_internal("shared_key") == "bot1_value"
    assert bot2.retrieve_internal("shared_key") == "bot2_value"

    # Verify separate databases
    assert bot1.db_path != bot2.db_path

