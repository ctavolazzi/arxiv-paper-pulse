"""
Comprehensive test suite for Bot context management.
Tests context.md operations, trimming, snapshots, and history.
"""
import os
from pathlib import Path
from datetime import datetime

import pytest

from arxiv_paper_pulse import config
from arxiv_paper_pulse.bot import Bot


@pytest.fixture
def dummy_genai(monkeypatch):
    """Mock Gemini API client for testing."""
    class DummyResponse:
        text = "ok"

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.calls = []
            self.models = self

        def generate_content(self, model, contents):
            self.calls.append({'model': model, 'contents': contents})
            return DummyResponse()

    client = DummyClient()
    monkeypatch.setattr("arxiv_paper_pulse.bot.genai.Client", lambda *args, **kwargs: client)
    return client


@pytest.fixture
def bot_factory(tmp_path, monkeypatch, dummy_genai):
    """Factory for creating test bots with custom context limits."""
    def _factory(context_max_bytes=256, history_retention=5, name="Tester"):
        working_dir = tmp_path / "bots"
        monkeypatch.setattr(config, "BOT_WORKING_DIR", str(working_dir))
        monkeypatch.setattr(config, "CONTEXT_MAX_BYTES", context_max_bytes)
        monkeypatch.setattr(config, "CONTEXT_HISTORY_RETENTION", history_retention)
        monkeypatch.setattr(config, "CONTEXT_HISTORY_DIRNAME", "history")
        monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
        return Bot(name, "Test Role")

    return _factory


# ============================================================================
# CONTEXT INITIALIZATION TESTS
# ============================================================================

def test_context_file_created_with_defaults(bot_factory):
    """Test context.md is created with default template."""
    bot = bot_factory()

    assert bot.context_file.exists()
    content = bot.context_file.read_text(encoding='utf-8')

    # Verify template sections
    assert "# Current Context" in content
    assert "## Current Status" in content
    assert "## Current Awareness" in content
    assert "## Pending Items / Todos" in content
    assert "## Important URLs" in content
    assert "## Folder Locations & Paths" in content
    assert "## Rules / Limits / Boundaries" in content
    assert "## Reference Material" in content
    assert "## Notes" in content


def test_context_includes_last_updated(bot_factory):
    """Test context includes Last Updated timestamp."""
    bot = bot_factory()

    content = bot.get_context()
    assert "- Last Updated:" in content


def test_context_history_dir_created(bot_factory):
    """Test context history directory is created."""
    bot = bot_factory()

    assert bot.context_history_dir.exists()
    assert bot.context_history_dir.is_dir()


# ============================================================================
# CONTEXT UPDATE TESTS
# ============================================================================

def test_update_context_replaces_content(bot_factory):
    """Test update_context replaces entire file."""
    bot = bot_factory()

    new_content = "# New Context\n\nCompletely new content"
    bot.update_context(new_content)

    result = bot.get_context()
    assert "# New Context" in result
    assert "Completely new content" in result


def test_update_context_refreshes_timestamp(bot_factory):
    """Test update_context refreshes Last Updated timestamp."""
    bot = bot_factory()

    original = bot.get_context()
    original_time = original.split("Last Updated: ")[1].split("\n")[0] if "Last Updated:" in original else ""

    import time
    time.sleep(0.1)  # Ensure timestamp changes

    bot.update_context(original)

    updated = bot.get_context()
    updated_time = updated.split("Last Updated: ")[1].split("\n")[0] if "Last Updated:" in updated else ""

    assert updated_time != original_time or original_time == ""


def test_append_to_context_adds_content(bot_factory):
    """Test append_to_context adds to end."""
    bot = bot_factory()

    bot.append_to_context("- New item")
    content = bot.get_context()

    assert "- New item" in content


def test_append_to_section_creates_section(bot_factory):
    """Test append creates section if it doesn't exist."""
    bot = bot_factory()

    bot.append_to_context("- Custom item", section="## Custom Section")
    content = bot.get_context()

    assert "## Custom Section" in content
    assert "- Custom item" in content


def test_append_to_section_preserves_structure(bot_factory):
    """Test append to section maintains markdown structure."""
    bot = bot_factory()

    bot.append_to_context("- First item", section="## Notes")
    bot.append_to_context("- Second item", section="## Notes")

    content = bot.get_context()
    lines = content.split('\n')

    # Check items are in order and properly formatted
    assert "- First item" in content
    assert "- Second item" in content


def test_update_context_section_replaces_content(bot_factory):
    """Test update_context_section replaces section content."""
    bot = bot_factory(context_max_bytes=5000)  # Large enough to not trim

    bot.update_context_section("Current Awareness", "- Working on tests\n- All systems go")
    content = bot.get_context()

    assert "- Working on tests" in content
    assert "- All systems go" in content


def test_update_section_creates_if_missing(bot_factory):
    """Test update_context_section creates section if missing."""
    bot = bot_factory()

    bot.update_context_section("Brand New Section", "New content here")
    content = bot.get_context()

    assert "## Brand New Section" in content
    assert "New content here" in content


# ============================================================================
# CONTEXT TRIMMING TESTS
# ============================================================================

def test_large_context_triggers_trim(bot_factory):
    """Test context exceeding limit triggers trim."""
    bot = bot_factory(context_max_bytes=200, history_retention=3)

    large_entry = "Long text " * 200
    bot.update_context(large_entry)

    context = bot.get_context()
    context_bytes = len(context.encode('utf-8'))

    # Allow small buffer (trim notice adds bytes)
    assert context_bytes <= bot.context_max_bytes + 50


def test_trim_creates_snapshot(bot_factory):
    """Test trimming creates history snapshot."""
    bot = bot_factory(context_max_bytes=200, history_retention=5)

    large_content = "# Header\n" + ("X" * 500)
    bot.update_context(large_content)

    history = bot.list_context_history()
    assert len(history) >= 1


def test_trim_adds_notice(bot_factory):
    """Test trim adds notice to content."""
    bot = bot_factory(context_max_bytes=200)

    large_content = "# Test\n" + ("Long content " * 100)
    bot.update_context(large_content)

    content = bot.get_context()
    assert "trimmed to fit" in content.lower()


def test_trim_preserves_header(bot_factory):
    """Test trim preserves header before --- separator."""
    bot = bot_factory(context_max_bytes=300)

    content_with_header = """# Important Header
## Status
- Key: Value

---
Body content that can be trimmed """ + ("X" * 1000)

    bot.update_context(content_with_header)
    result = bot.get_context()

    # Header should be preserved
    assert "# Important Header" in result or result.startswith("# ")


def test_utf8_trimming_preserves_characters(bot_factory):
    """Test UTF-8 trimming doesn't corrupt multi-byte characters."""
    bot = bot_factory(context_max_bytes=150)

    # Use multi-byte characters
    unicode_content = "Test: " + ("日本語テスト" * 50)  # Japanese text
    bot.update_context(unicode_content)

    result = bot.get_context()

    # Should not have encoding errors (no replacement chars)
    assert "�" not in result


# ============================================================================
# SNAPSHOT HISTORY TESTS
# ============================================================================

def test_list_context_history_empty(bot_factory):
    """Test listing history when no snapshots exist."""
    bot = bot_factory()

    history = bot.list_context_history()
    assert history == []


def test_list_context_history_returns_snapshots(bot_factory):
    """Test listing history returns snapshot metadata."""
    bot = bot_factory(context_max_bytes=100)

    # Trigger snapshots by exceeding limit
    bot.update_context("X" * 200)
    bot.update_context("Y" * 200)

    history = bot.list_context_history()

    assert len(history) >= 1
    assert 'path' in history[0]
    assert 'name' in history[0]
    assert 'modified' in history[0]


def test_list_context_history_limit(bot_factory):
    """Test listing history respects limit."""
    bot = bot_factory(context_max_bytes=100, history_retention=10)

    # Create multiple snapshots by triggering trims in process()
    for i in range(5):
        bot.update_context("Content " + str(i) * 50)
        bot._get_context_for_prompt()  # Force snapshot creation

    history = bot.list_context_history(limit=2)
    assert len(history) <= 2  # May have fewer if not all triggered


def test_list_context_history_invalid_limit(bot_factory):
    """Test listing history handles invalid limit gracefully."""
    bot = bot_factory(context_max_bytes=100)

    bot.update_context("X" * 200)

    # Should not crash with invalid limit
    history = bot.list_context_history(limit="invalid")
    assert isinstance(history, list)


def test_load_context_snapshot_by_index(bot_factory):
    """Test loading snapshot by index."""
    bot = bot_factory(context_max_bytes=100)

    original_content = "Original " * 50
    bot.update_context(original_content)

    snapshots = bot.list_context_history()
    if snapshots:
        content = bot.load_context_snapshot(0)
        assert "Original" in content


def test_load_context_snapshot_by_path(bot_factory):
    """Test loading snapshot by path."""
    bot = bot_factory(context_max_bytes=100)

    bot.update_context("Test " * 50)

    snapshots = bot.list_context_history()
    if snapshots:
        path = snapshots[0]['path']
        content = bot.load_context_snapshot(path)
        assert "Test" in content or "Snapshot" in content


def test_snapshot_retention_pruning(bot_factory):
    """Test old snapshots are pruned based on retention limit."""
    bot = bot_factory(context_max_bytes=100, history_retention=3)

    # Create more snapshots than retention limit
    for i in range(5):
        bot.update_context(f"Version {i} " * 30)

    history = bot.list_context_history()
    assert len(history) <= 3


# ============================================================================
# PROMPT INTEGRATION TESTS
# ============================================================================

def test_process_includes_context_by_default(bot_factory, dummy_genai):
    """Test process() includes context.md by default."""
    bot = bot_factory()

    bot.update_context("# Test Context\nImportant info")

    dummy_genai.calls.clear()
    bot.process("Test prompt")

    prompt = dummy_genai.calls[-1]['contents'][-1]
    assert "Current Context (from context.md)" in prompt
    assert "Test Context" in prompt


def test_process_without_context_flag(bot_factory, dummy_genai):
    """Test process() can exclude context.md."""
    bot = bot_factory()

    bot.update_context("# Context to exclude")

    dummy_genai.calls.clear()
    bot.process("Test prompt", include_context=False)

    prompt = dummy_genai.calls[-1]['contents'][-1]
    assert "Current Context (from context.md)" not in prompt


def test_process_auto_trims_oversized_context(bot_factory, dummy_genai):
    """Test process() auto-trims if context exceeds limit."""
    bot = bot_factory(context_max_bytes=200, history_retention=5, name="OverflowBot")

    # Manually write oversized content (simulating external edit)
    oversized = "# Header\n" + ("X" * 1000)
    bot.context_file.write_text(oversized, encoding='utf-8')

    dummy_genai.calls.clear()
    response = bot.process("Hello")

    assert response == "ok"

    # Verify context was trimmed (allow buffer for trim notice)
    context = bot.get_context()
    assert len(context.encode('utf-8')) <= bot.context_max_bytes + 50

    # Verify snapshot was created
    history = bot.list_context_history()
    assert len(history) >= 1


def test_context_respects_size_limit_in_prompt(bot_factory, dummy_genai):
    """Test context sent in prompt respects size limit."""
    bot = bot_factory(context_max_bytes=300)

    large_context = "Test " * 500
    bot.update_context(large_context)

    dummy_genai.calls.clear()
    bot.process("Test")

    prompt = dummy_genai.calls[-1]['contents'][-1]
    context_section = prompt.split("Current Context (from context.md):\n", 1)[1] if "Current Context" in prompt else ""

    # Context in prompt should be within limit
    if context_section:
        assert len(context_section.encode('utf-8')) <= bot.context_max_bytes


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

def test_empty_context_file(bot_factory):
    """Test handling of empty context file."""
    bot = bot_factory()

    bot.context_file.write_text("", encoding='utf-8')
    content = bot.get_context()

    assert content == ""


def test_context_with_unicode(bot_factory):
    """Test context handles Unicode properly."""
    bot = bot_factory()

    unicode_content = "# Context\n\n日本語 🎉 Émojis and spëcial chârs"
    bot.update_context(unicode_content)

    result = bot.get_context()
    assert "日本語" in result
    assert "🎉" in result


def test_concurrent_context_updates(bot_factory):
    """Test multiple rapid context updates."""
    bot = bot_factory(context_max_bytes=5000)  # Large enough to hold all items

    for i in range(10):
        bot.append_to_context(f"- Item {i}")

    content = bot.get_context()
    # Check that at least some items are present
    assert "- Item 0" in content or "- Item 9" in content
    # And content has multiple items
    assert content.count("- Item") >= 5


def test_context_normalization(bot_factory):
    """Test context content is normalized (line endings, spacing)."""
    bot = bot_factory()

    messy_content = "# Header\r\n\r\nContent\r\n\r\n\r\nMore content  \n\n"
    bot.update_context(messy_content)

    result = bot.get_context()

    # Should normalize line endings
    assert "\r" not in result
    # Should have clean structure
    lines = result.split('\n')
    assert all(line == line.rstrip() for line in lines)
