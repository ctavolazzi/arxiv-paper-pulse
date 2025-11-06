# Bot Class Testing Protocol

## Overview
Comprehensive testing guidelines and protocols for the Bot class and related functionality. This document provides recommendations for testing strategy, mock patterns, test organization, and continuous integration.

---

## Testing Philosophy

### Core Principles
1. **Isolation**: Each test should be independent and not rely on external state
2. **Reproducibility**: Tests should produce the same results on every run
3. **Coverage**: Test all critical paths, edge cases, and error conditions
4. **Speed**: Unit tests should be fast; integration tests can be slower
5. **Clarity**: Test names and structure should clearly communicate intent

### Test Pyramid
```
        /\
       /  \      E2E Tests (Expensive, Slow, Comprehensive)
      /    \
     /------\    Integration Tests (Moderate, Real Components)
    /        \
   /----------\  Unit Tests (Fast, Isolated, Many)
```

- **70%** Unit tests (fast, isolated, mocked dependencies)
- **20%** Integration tests (multiple components, limited mocking)
- **10%** End-to-end tests (full system, real APIs when possible)

---

## Test Organization

### Directory Structure
```
tests/
├── test_bot.py                 # Core Bot functionality
├── test_bot_context.py         # Context management
├── test_bot_memory.py          # Memory operations (future)
├── test_bot_safety.py          # Safety protocols (future)
├── test_bot_integration.py     # Integration tests (future)
├── conftest.py                 # Shared fixtures
└── BOT_TEST_PROTOCOL.md        # This document
```

### Test File Naming
- `test_<module>.py` for unit tests
- `test_<module>_integration.py` for integration tests
- `test_<feature>_e2e.py` for end-to-end tests

### Test Function Naming
```python
def test_<component>_<behavior>_<expected_result>():
    """Clear description of what is being tested."""
```

Examples:
- `test_internal_memory_store_retrieve()`
- `test_context_exceeds_limit_triggers_trim()`
- `test_process_without_context_flag_excludes_file()`

---

## Mocking Strategy

### When to Mock
- External API calls (Gemini API)
- File system operations (for speed)
- Network requests
- Time-dependent operations
- Random/non-deterministic behavior

### When NOT to Mock
- Core logic and algorithms
- Data structures and transformations
- Database operations (use temp databases)
- Path operations (use temp directories)

### Mock Patterns

#### 1. API Client Mocking
```python
@pytest.fixture
def mock_genai(monkeypatch):
    """Mock Gemini API client."""
    class MockClient:
        def __init__(self, *args, **kwargs):
            self.calls = []
            self.models = self

        def generate_content(self, model, contents):
            self.calls.append({'model': model, 'contents': contents})
            return MockResponse(text="mock response")

    client = MockClient()
    monkeypatch.setattr("arxiv_paper_pulse.bot.genai.Client",
                       lambda *args, **kwargs: client)
    return client
```

#### 2. Configuration Mocking
```python
@pytest.fixture
def bot_factory(tmp_path, monkeypatch):
    """Factory for creating isolated test bots."""
    def _factory(name="TestBot", **config_overrides):
        monkeypatch.setattr(config, "BOT_WORKING_DIR", str(tmp_path / "bots"))
        monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

        for key, value in config_overrides.items():
            monkeypatch.setattr(config, key.upper(), value)

        return Bot(name, "Test Role")

    return _factory
```

#### 3. Time Mocking (for timestamp testing)
```python
from datetime import datetime
from unittest.mock import patch

def test_timestamp_behavior():
    fixed_time = datetime(2025, 1, 1, 12, 0, 0)
    with patch('arxiv_paper_pulse.bot.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        # Test code here
```

---

## Test Fixtures

### Essential Fixtures

#### `bot_factory` - Configurable Bot Creation
```python
@pytest.fixture
def bot_factory(tmp_path, monkeypatch, mock_genai):
    """Factory for creating test bots with custom config."""
    def _factory(name="TestBot", role="Tester", **kwargs):
        # Setup isolated environment
        working_dir = tmp_path / "bots" / name.lower()
        monkeypatch.setattr(config, "BOT_WORKING_DIR", str(tmp_path / "bots"))

        # Apply config overrides
        for key, value in kwargs.items():
            if hasattr(config, key.upper()):
                monkeypatch.setattr(config, key.upper(), value)

        return Bot(name, role)

    return _factory
```

#### `temp_db` - Isolated Database
```python
@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    # Setup database
    yield db_path
    # Cleanup
    db_path.unlink(missing_ok=True)
```

### Fixture Scopes
- `function` (default): New fixture per test function
- `class`: Shared across test class
- `module`: Shared across test file
- `session`: Shared across entire test run

```python
@pytest.fixture(scope="session")
def shared_resource():
    """Expensive setup, shared across all tests."""
    resource = expensive_setup()
    yield resource
    resource.cleanup()
```

---

## Test Coverage Guidelines

### Critical Test Categories

#### 1. Initialization Tests
- [ ] Bot creates with default parameters
- [ ] Working directory is created
- [ ] Database is initialized with all tables
- [ ] Context file is created with template
- [ ] Context history directory exists

#### 2. Memory Tests
- [ ] Store and retrieve internal memory
- [ ] Store and retrieve external memory
- [ ] External memory requires coupling
- [ ] Memory persists across bot instances
- [ ] Memory handles complex data types (dict, list, etc.)
- [ ] Memory overwrites on duplicate keys

#### 3. Context Management Tests
- [ ] Context file created with default template
- [ ] Update context replaces content
- [ ] Append to context adds content
- [ ] Update section replaces section content
- [ ] Large context triggers trim
- [ ] Trim creates snapshot
- [ ] Snapshot history is maintained
- [ ] Snapshot retention pruning works
- [ ] Last Updated timestamp refreshes
- [ ] UTF-8 characters preserved during trim

#### 4. Thought Journal Tests
- [ ] Record thought stores in database
- [ ] Query thoughts by type
- [ ] Query thoughts by tags
- [ ] Thought chains (parent-child relationships)
- [ ] Auto-tag extraction

#### 5. Request/Response Tests
- [ ] Exact request matching (hash-based)
- [ ] Request normalization (case, whitespace)
- [ ] Record new request
- [ ] Find past responses
- [ ] New attempt heuristic
- [ ] Multiple attempts tracked

#### 6. API Integration Tests
- [ ] Process basic prompt
- [ ] Process with context dict
- [ ] Process includes context file by default
- [ ] Process can exclude context file
- [ ] Process logs input/output
- [ ] Process handles errors gracefully

#### 7. Safety Protocol Tests
- [ ] Workspace root detection
- [ ] Path within workspace validation
- [ ] External path permission checking
- [ ] Permission file parsing

#### 8. Action Logging Tests
- [ ] Log action stores in database
- [ ] Action history retrieval
- [ ] Action history respects limit
- [ ] Batch reflection works

---

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_bot.py

# Run specific test function
pytest tests/test_bot.py::test_bot_initialization

# Run tests matching pattern
pytest -k "memory"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=arxiv_paper_pulse --cov-report=html
```

### Test Markers
```python
# Mark slow tests
@pytest.mark.slow
def test_expensive_operation():
    pass

# Mark integration tests
@pytest.mark.integration
def test_full_workflow():
    pass

# Mark tests requiring external services
@pytest.mark.requires_api
def test_real_gemini_call():
    pass
```

Run specific markers:
```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

### Environment-Specific Tests
```bash
# Skip tests requiring real API
pytest -m "not requires_api"

# Run only unit tests
pytest tests/test_bot.py tests/test_bot_context.py
```

---

## Continuous Integration (CI) Recommendations

### GitHub Actions Example
```yaml
name: Bot Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=arxiv_paper_pulse --cov-report=xml
      env:
        GEMINI_API_KEY: test-key

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

---

## Test Data Management

### Temporary Directories
```python
def test_with_temp_data(tmp_path):
    """Use tmp_path for file operations."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("data")
    assert test_file.exists()
    # Automatic cleanup after test
```

### Test Fixtures Data
```python
@pytest.fixture
def sample_context():
    """Provide sample context data."""
    return """# Test Context
## Status
- Active

## Notes
- Test note
"""

def test_with_sample_context(sample_context):
    # Use sample_context
    pass
```

---

## Performance Testing

### Timing Tests
```python
import time

def test_process_performance(bot_factory):
    """Test process completes within time limit."""
    bot = bot_factory()

    start = time.time()
    bot.process("Test prompt")
    duration = time.time() - start

    assert duration < 1.0  # Should complete in under 1 second
```

### Memory Profiling
```python
import tracemalloc

def test_memory_usage(bot_factory):
    """Test memory usage is reasonable."""
    tracemalloc.start()

    bot = bot_factory()
    for i in range(1000):
        bot.store_internal(f"key_{i}", f"value_{i}")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 10 * 1024 * 1024  # Less than 10MB
```

---

## Debugging Failed Tests

### Verbose Output
```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Stop on first failure
pytest -x
```

### Logging in Tests
```python
import logging

def test_with_logging(caplog):
    """Capture log output."""
    with caplog.at_level(logging.DEBUG):
        bot.process("test")

    assert "Processing" in caplog.text
```

---

## Best Practices

### DO:
✅ Use descriptive test names
✅ Test one thing per test function
✅ Use fixtures for common setup
✅ Mock external dependencies
✅ Clean up resources after tests
✅ Write tests before fixing bugs
✅ Keep tests simple and readable
✅ Test edge cases and error conditions

### DON'T:
❌ Rely on test execution order
❌ Use hardcoded paths or credentials
❌ Skip cleanup operations
❌ Test multiple unrelated things in one test
❌ Ignore flaky tests
❌ Mock core business logic
❌ Write tests that depend on external services
❌ Leave commented-out test code

---

## Test Maintenance

### Regular Review
- Review test coverage monthly
- Update tests when requirements change
- Remove obsolete tests
- Refactor duplicated test code into fixtures

### Test Quality Metrics
- **Coverage**: Aim for >80% code coverage
- **Speed**: Unit tests should complete in <1s each
- **Flakiness**: Fix or remove flaky tests immediately
- **Clarity**: Tests should be self-documenting

---

## Troubleshooting Common Issues

### Issue: Tests fail due to missing API key
**Solution**: Mock the API client or set `GEMINI_API_KEY=test-key`

### Issue: Tests fail intermittently
**Solution**: Check for:
- Timing dependencies (use fixed time in tests)
- File system race conditions (use temp directories)
- Order dependencies (ensure test isolation)

### Issue: Tests are slow
**Solution**:
- Use mocks instead of real operations
- Use temp directories (in-memory if possible)
- Parallelize test execution: `pytest -n auto`

### Issue: Test database conflicts
**Solution**: Use `tmp_path` fixture and unique paths per test

---

## Future Testing Enhancements

### To Be Added:
- [ ] Property-based testing (Hypothesis)
- [ ] Mutation testing (Mutmut)
- [ ] Load testing for concurrent operations
- [ ] Chaos testing for resilience
- [ ] Visual regression testing for HTML output
- [ ] Contract testing for API interfaces

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Testing Best Practices (Google)](https://testing.googleblog.com/)
- [Python Testing with pytest (Book)](https://pragprog.com/titles/bopytest/)

---

**Last Updated**: 2025-11-06
**Maintained By**: Development Team

