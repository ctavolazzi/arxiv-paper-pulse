# ArXiv Paper Pulse Tests

This directory contains tests for the ArXiv Paper Pulse application. The tests are organized into different modules to allow for modular testing of specific components.

## Test Structure

The test suite is organized into the following modules:

- **test_core.py**: Tests the basic functionality of the ArxivSummarizer class
- **test_briefing.py**: Tests the briefing document generation functionality
- **test_cli_article_selection.py**: Tests the CLI article selection feature
- **test_gui_article_selection.py**: Tests the GUI article selection dialog
- **test_prompt_config.py**: Tests the summary and synthesis prompt configurations
- **test_crawler.py**: Tests the crawler functionality
- **test_gui.py**: Tests the GUI functionality
- **test_import.py**: Tests the basic import functionality
- **test_workflow_integration.py**: Tests the entire workflow from search to briefing generation

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Test Modules

To run specific test modules:

```bash
# Run only the briefing tests
pytest tests/test_briefing.py

# Run only the CLI article selection tests
pytest tests/test_cli_article_selection.py

# Run only the GUI article selection tests
pytest tests/test_gui_article_selection.py
```

### Running Specific Test Functions

To run specific test functions:

```bash
# Run a specific test function
pytest tests/test_briefing.py::test_initialize_briefing_file
```

### Running Tests by Mark

Tests are marked with different categories:

```bash
# Run only integration tests
pytest -m integration

# Run only GUI tests
pytest -m gui
```

### Skipping GUI Tests in Headless Environments

GUI tests are automatically skipped in environments where a display is not available. The GUI tests are marked with `@pytest.mark.gui` to make them easy to identify.

### Live Tests

Some tests that communicate with external services are skipped by default. To run these tests, you need to set the `RUN_LIVE_TESTS` environment variable:

```bash
RUN_LIVE_TESTS=1 pytest tests/test_workflow_integration.py::test_live_workflow
```

## Test Coverage

To get a test coverage report:

```bash
pytest --cov=arxiv_paper_pulse
```

To get a detailed HTML coverage report:

```bash
pytest --cov=arxiv_paper_pulse --cov-report=html
```

This will create a `htmlcov` directory with an HTML coverage report that you can open in your browser.

## Test Configuration

The tests use `conftest.py` to set up common fixtures and configuration. The most important fixtures include:

- **mock_ollama_summarize**: Mocks the Ollama summarization to return a known result
- **mock_paper_data**: Generates mock paper data for testing
- **setup_test_dirs**: Sets up temporary directories for testing
- **mock_fetch_raw_data**: Mocks the fetch_raw_data method to return known test data
- **mock_summarize_selected_papers**: Mocks the summarize_selected_papers method

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a new test file for new features
2. Use appropriate markers (integration, gui, etc.) for tests
3. Make sure tests can run independently
4. Provide descriptive docstrings for each test function
5. Use fixtures to set up and tear down test environments
6. Mock external dependencies when appropriate
7. For GUI tests, add appropriate try/except blocks to handle headless environments