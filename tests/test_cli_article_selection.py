import json
import sys
from pathlib import Path
import pytest

from arxiv_paper_pulse.cli import main
from arxiv_paper_pulse.core import ArxivSummarizer

@pytest.fixture
def mock_fetch_raw_data(monkeypatch):
    """Mock the fetch_raw_data method to return known test data."""
    def mock_fetch(self, force_pull=False):
        return [
            {
                "entry_id": "2401.01234",
                "title": "Test Paper 1: Neural Network Optimization",
                "published": "2023-01-01T00:00:00Z",
                "url": "http://arxiv.org/abs/2401.01234",
                "abstract": "This is a test abstract for paper 1",
                "query": self.query.lower(),
                "id": "unique_id_1"
            },
            {
                "entry_id": "2401.56789",
                "title": "Test Paper 2: Advanced AI Methods",
                "published": "2023-01-02T00:00:00Z",
                "url": "http://arxiv.org/abs/2401.56789",
                "abstract": "This is a test abstract for paper 2",
                "query": self.query.lower(),
                "id": "unique_id_2"
            },
            {
                "entry_id": "2401.12345",
                "title": "Test Paper 3: Deep Learning Applications",
                "published": "2023-01-03T00:00:00Z",
                "url": "http://arxiv.org/abs/2401.12345",
                "abstract": "This is a test abstract for paper 3",
                "query": self.query.lower(),
                "id": "unique_id_3"
            }
        ]

    monkeypatch.setattr(ArxivSummarizer, "fetch_raw_data", mock_fetch)

@pytest.fixture
def mock_summarize_selected_papers(monkeypatch):
    """Mock the summarize_selected_papers method to avoid actual summarization."""
    def mock_summarize(self, selected_papers, force_pull=False):
        # Add a mock summary to each paper
        for paper in selected_papers:
            paper["summary"] = f"Summary of {paper['title']}"
        return selected_papers

    monkeypatch.setattr(ArxivSummarizer, "summarize_selected_papers", mock_summarize)

def test_cli_select_all_articles(monkeypatch, tmp_path, mock_fetch_raw_data, mock_summarize_selected_papers, capsys):
    """Test selecting all articles via the 'all' keyword."""
    # Set up temporary directories
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)
    temp_briefing = tmp_path / "briefings"
    temp_briefing.mkdir(exist_ok=True)

    # Override config paths
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))
    monkeypatch.setattr("arxiv_paper_pulse.config.BRIEFING_DIR", str(temp_briefing))

    # Simulate CLI arguments and user input
    # First: query, Second: max results, Third: article selection
    inputs = iter(["cat:cs.AI", "3", "all"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Simulate CLI command
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-pulse"])

    # Run the CLI
    main()

    # Check the output
    captured = capsys.readouterr()
    output = captured.out

    # Verify all articles are listed
    assert "1. Test Paper 1: Neural Network Optimization" in output
    assert "2. Test Paper 2: Advanced AI Methods" in output
    assert "3. Test Paper 3: Deep Learning Applications" in output

    # Verify all articles were processed
    assert "Proceeding with summarization of 3 articles" in output

def test_cli_select_specific_articles(monkeypatch, tmp_path, mock_fetch_raw_data, mock_summarize_selected_papers, capsys):
    """Test selecting specific articles by number."""
    # Set up temporary directories
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)
    temp_briefing = tmp_path / "briefings"
    temp_briefing.mkdir(exist_ok=True)

    # Override config paths
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))
    monkeypatch.setattr("arxiv_paper_pulse.config.BRIEFING_DIR", str(temp_briefing))

    # Simulate CLI arguments and user input
    # First: query, Second: max results, Third: article selection (articles 1 and 3)
    inputs = iter(["cat:cs.AI", "3", "1,3"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Simulate CLI command
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-pulse"])

    # Run the CLI
    main()

    # Check the output
    captured = capsys.readouterr()
    output = captured.out

    # Verify all articles are listed
    assert "1. Test Paper 1: Neural Network Optimization" in output
    assert "2. Test Paper 2: Advanced AI Methods" in output
    assert "3. Test Paper 3: Deep Learning Applications" in output

    # Verify only selected articles were processed (2 out of 3)
    assert "Proceeding with summarization of 2 articles" in output

    # Since we're mocking the summarize_selected_papers method, we can't directly check
    # which papers were selected, but we can verify the correct count

def test_cli_invalid_selection(monkeypatch, tmp_path, mock_fetch_raw_data, mock_summarize_selected_papers, capsys):
    """Test providing an invalid article selection (should default to all)."""
    # Set up temporary directories
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)
    temp_briefing = tmp_path / "briefings"
    temp_briefing.mkdir(exist_ok=True)

    # Override config paths
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))
    monkeypatch.setattr("arxiv_paper_pulse.config.BRIEFING_DIR", str(temp_briefing))

    # Simulate CLI arguments and user input
    # First: query, Second: max results, Third: invalid article selection
    inputs = iter(["cat:cs.AI", "3", "invalid input"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Simulate CLI command
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-pulse"])

    # Run the CLI
    main()

    # Check the output
    captured = capsys.readouterr()
    output = captured.out

    # Verify that an error message was shown
    assert "Invalid selection format. Using all articles." in output

    # Verify all articles were processed (fallback behavior)
    assert "Proceeding with summarization of 3 articles" in output

def test_cli_out_of_range_selection(monkeypatch, tmp_path, mock_fetch_raw_data, mock_summarize_selected_papers, capsys):
    """Test selecting articles with out-of-range numbers."""
    # Set up temporary directories
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)
    temp_briefing = tmp_path / "briefings"
    temp_briefing.mkdir(exist_ok=True)

    # Override config paths
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))
    monkeypatch.setattr("arxiv_paper_pulse.config.BRIEFING_DIR", str(temp_briefing))

    # Simulate CLI arguments and user input
    # First: query, Second: max results, Third: out-of-range article selection
    inputs = iter(["cat:cs.AI", "3", "1,4,5"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Simulate CLI command
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-pulse"])

    # Run the CLI
    main()

    # Check the output
    captured = capsys.readouterr()
    output = captured.out

    # Only article 1 should be processed (as 4,5 are out of range)
    assert "Proceeding with summarization of 1 articles" in output