# Bot Class Testing - Quick Start Guide

A quick reference for running and writing tests for the Bot class.

---

## Running Tests

### Basic Commands
```bash
# Run all bot tests
pytest tests/test_bot.py tests/test_bot_context.py

# Verbose output
pytest tests/test_bot.py tests/test_bot_context.py -v

# Run specific test
pytest tests/test_bot.py::test_bot_initialization

# Run tests matching a pattern
pytest -k "memory" -v
```

### Common Options
```bash
# Stop on first failure
pytest -x

# Show output even for passing tests
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Run in parallel (if pytest-xdist installed)
pytest -n auto
```

---

## Writing New Tests

### Basic Test Template
```python
def test_my_feature(bot_factory):
    """Test description."""
    # Arrange
    bot = bot_factory("TestBot", "Test Role")

    # Act
    result = bot.some_method()

    # Assert
    assert result == expected_value
```

### Test with Custom Config
```python
def test_with_custom_config(bot_factory):
    """Test with custom context limit."""
    bot = bot_factory(
        name="CustomBot",
        context_max_bytes=500,
        history_retention=10
    )

    # Your test code here
    assert bot.context_max_bytes == 500
```

### Test with External Database
```python
def test_external_memory(bot_factory, tmp_path):
    """Test external memory operations."""
    bot = bot_factory()
    external_db = tmp_path / "external.db"

    # Skip permission check for tests
    bot.couple_external_memory(external_db, request_permission=False)

    bot.store_external("key", "value")
    assert bot.retrieve_external("key") == "value"
```

### Test API Interactions
```python
def test_api_call(bot_factory, mock_genai):
    """Test API processing."""
    bot = bot_factory()

    # Clear previous calls
    mock_genai.calls.clear()

    # Make API call
    response = bot.process("Test prompt")

    # Verify call was made
    assert len(mock_genai.calls) == 1
    assert "Test prompt" in mock_genai.calls[0]['contents'][-1]
```

---

## Common Test Patterns

### 1. Testing Context Operations
```python
def test_context_update(bot_factory):
    """Test context file updates."""
    bot = bot_factory(context_max_bytes=5000)  # Large enough

    bot.update_context("# New Content\nTest data")
    content = bot.get_context()

    assert "New Content" in content
    assert "Test data" in content
```

### 2. Testing Database Queries
```python
def test_thought_journal(bot_factory):
    """Test thought recording and retrieval."""
    bot = bot_factory()

    bot.record_thought('reasoning', 'Test thought', tags=['test'])
    thoughts = bot.query_thoughts(filters={'thought_type': 'reasoning'})

    assert len(thoughts) >= 1
    assert thoughts[0]['content'] == 'Test thought'
```

### 3. Testing Snapshots and History
```python
def test_snapshot_creation(bot_factory):
    """Test context snapshot creation."""
    bot = bot_factory(context_max_bytes=100, history_retention=5)

    # Trigger snapshot by exceeding limit
    bot.update_context("X" * 200)

    history = bot.list_context_history()
    assert len(history) >= 1
```

### 4. Testing Error Conditions
```python
def test_error_handling(bot_factory):
    """Test proper error handling."""
    bot = bot_factory()

    # Test that operation fails as expected
    with pytest.raises(ValueError, match="not coupled"):
        bot.store_external("key", "value")
```

### 5. Testing Isolation
```python
def test_bot_isolation(bot_factory):
    """Test multiple bots don't interfere."""
    bot1 = bot_factory("Bot1", "Role1")
    bot2 = bot_factory("Bot2", "Role2")

    bot1.store_internal("key", "value1")
    bot2.store_internal("key", "value2")

    assert bot1.retrieve_internal("key") == "value1"
    assert bot2.retrieve_internal("key") == "value2"
```

---

## Fixtures Reference

### `bot_factory`
Factory for creating test bots with custom configuration.

**Usage**:
```python
def test_example(bot_factory):
    bot = bot_factory("BotName", "Role", context_max_bytes=1000)
```

**Parameters**:
- `name`: Bot name (default: "TestBot")
- `role`: Bot role (default: "Tester")
- `context_max_bytes`: Context size limit
- `history_retention`: Number of snapshots to keep
- Additional config keys as needed

### `mock_genai` (or `dummy_genai`)
Mock Gemini API client that returns predictable responses.

**Usage**:
```python
def test_example(bot_factory, mock_genai):
    bot = bot_factory()
    mock_genai.calls.clear()

    bot.process("Test")

    assert len(mock_genai.calls) == 1
```

### `tmp_path`
Pytest built-in fixture providing temporary directory.

**Usage**:
```python
def test_example(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("data")
    assert test_file.exists()
```

---

## Assertion Examples

### Basic Assertions
```python
assert value == expected
assert value is not None
assert "substring" in string
assert value > 0
assert isinstance(obj, ClassName)
```

### Collection Assertions
```python
assert len(collection) == 5
assert item in collection
assert all(x > 0 for x in numbers)
assert any(x == "target" for x in items)
```

### Exception Assertions
```python
# Test that exception is raised
with pytest.raises(ValueError):
    function_that_should_fail()

# Test exception message
with pytest.raises(ValueError, match="expected message"):
    function_that_should_fail()
```

### File Assertions
```python
assert path.exists()
assert path.is_file()
assert path.read_text() == "expected content"
assert path.stat().st_size > 0
```

---

## Debugging Tests

### Print Debugging
```bash
# Show print statements
pytest -s tests/test_bot.py::test_my_feature
```

### Interactive Debugging
```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --trace
```

### Verbose Output
```bash
# Show test names and status
pytest -v

# Show even more detail
pytest -vv

# Show local variables on failure
pytest -l
```

### Test Markers (if configured)
```python
# In test file:
@pytest.mark.slow
def test_expensive_operation():
    pass

# Run only fast tests:
pytest -m "not slow"
```

---

## Common Issues & Solutions

### Issue: Test fails intermittently
**Solution**: Ensure test isolation - check for:
- Shared state between tests
- Timing dependencies (use fixed timestamps)
- File system race conditions

### Issue: Mock not working
**Solution**: Check monkeypatch target:
```python
# Import path must match how it's imported in source
monkeypatch.setattr("arxiv_paper_pulse.bot.genai.Client", MockClient)
```

### Issue: Database locked error
**Solution**: Ensure proper cleanup:
```python
# Use tmp_path for isolated databases
bot = bot_factory()  # Creates isolated DB automatically
```

### Issue: Context size tests failing
**Solution**: Remember trim notice adds bytes:
```python
# Allow buffer for trim notice
assert len(content.encode('utf-8')) <= bot.context_max_bytes + 50
```

---

## Best Practices Checklist

- [ ] Test names clearly describe what is being tested
- [ ] Each test tests one thing
- [ ] Tests are independent (can run in any order)
- [ ] Use fixtures for common setup
- [ ] Mock external dependencies (APIs, network)
- [ ] Clean up resources after tests (use tmp_path)
- [ ] Include docstrings explaining test purpose
- [ ] Test both success and failure cases
- [ ] Test edge cases (empty, None, large values)
- [ ] Keep tests simple and readable

---

## Quick Test Creation Workflow

1. **Identify what to test**: Feature, bug fix, or edge case
2. **Write test name**: `test_<component>_<behavior>_<expected>`
3. **Set up fixtures**: Use `bot_factory` for isolated bot
4. **Arrange**: Prepare test data and state
5. **Act**: Call the method/function being tested
6. **Assert**: Verify expected behavior
7. **Run**: `pytest tests/test_bot.py::test_your_new_test -v`
8. **Debug**: Use `-s`, `-l`, or `--pdb` if needed
9. **Refine**: Adjust assertions, add edge cases
10. **Document**: Add clear docstring

---

## Example: Full Test Development

```python
def test_context_section_update_preserves_other_sections(bot_factory):
    """
    Test that updating one section doesn't affect others.

    This is a regression test for a bug where updating the
    "Current Awareness" section would corrupt the "Notes" section.
    """
    # Arrange: Create bot with large context limit
    bot = bot_factory(context_max_bytes=10000)

    # Set up initial sections
    bot.update_context_section("Current Awareness", "- Initial awareness")
    bot.update_context_section("Notes", "- Important note")

    # Act: Update only one section
    bot.update_context_section("Current Awareness", "- Updated awareness")

    # Assert: Both sections have correct content
    content = bot.get_context()
    assert "- Updated awareness" in content
    assert "- Important note" in content
    assert "- Initial awareness" not in content
```

---

## Resources

- **Full Documentation**: `BOT_TEST_PROTOCOL.md`
- **Test Summary**: `TEST_SUMMARY.md`
- **Source Code**: `arxiv_paper_pulse/bot.py`
- **Pytest Docs**: https://docs.pytest.org/

---

**Happy Testing!** 🧪✨

