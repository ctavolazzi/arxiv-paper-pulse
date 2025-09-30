import json
from pathlib import Path
import pytest
import sys

from arxiv_paper_pulse.core import ArxivSummarizer
from arxiv_paper_pulse.cli import main

# Override the production directories with temporary ones during tests.
@pytest.fixture(autouse=True)
def use_temp_data_dirs(tmp_path, monkeypatch):
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir()
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir()

    # Override the configuration variables in the config module.
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))

    return {"raw": temp_raw, "summary": temp_summary}

def test_fetch_raw_data_force_pull():
    summarizer = ArxivSummarizer(max_results=2)
    data = summarizer.fetch_raw_data(force_pull=True)
    assert isinstance(data, list)
    # Verify that each paper has a unique "id" set by the utils function.
    for paper in data:
        assert "id" in paper and paper["id"]
    # Verify that a raw data file was created in the temporary raw directory.
    raw_dir = Path(__import__("arxiv_paper_pulse.config").config.RAW_DATA_DIR)
    raw_files = list(raw_dir.glob("*_raw.json"))
    assert len(raw_files) >= 1

def test_summarize_papers_force_pull():
    summarizer = ArxivSummarizer(max_results=1)
    summaries = summarizer.summarize_papers(force_pull=True)
    assert isinstance(summaries, list)
    # Verify that each summary has a unique "id" field.
    for paper in summaries:
        assert "id" in paper and paper["id"]
    # Verify that a summary file was created in the temporary summary directory.
    summary_dir = Path(__import__("arxiv_paper_pulse.config").config.SUMMARY_DIR)
    summary_files = list(summary_dir.glob("*_summary.json"))
    assert len(summary_files) >= 1

def test_cached_behavior():
    summarizer = ArxivSummarizer(max_results=1)
    # Force pull to create fresh data.
    data_first = summarizer.fetch_raw_data(force_pull=True)
    # Now, without force_pull, cached data should be loaded.
    data_second = summarizer.fetch_raw_data(force_pull=False)
    assert data_first == data_second

    # And for summaries as well.
    summaries_first = summarizer.summarize_papers(force_pull=True)
    summaries_second = summarizer.summarize_papers(force_pull=False)
    assert summaries_first == summaries_second

def test_custom_query(tmp_path, monkeypatch):
    # Test that a custom query is stored and used properly.
    custom_query = "cat:math"
    summarizer = ArxivSummarizer(max_results=1, query=custom_query)
    assert summarizer.query == custom_query
    data = summarizer.fetch_raw_data(force_pull=True)
    assert isinstance(data, list)

def test_cli_custom_query(monkeypatch, tmp_path):
    # Simulate interactive CLI behavior:
    # First input: search query
    # Second input: max results
    # Third input: response for cached data prompt
    # Fourth input: article selection
    inputs = iter(["cat:physics", "10", "n", "all"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Set up temporary directories.
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))

    # Simulate CLI arguments (no query provided and no --pull flag).
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-pulse"])
    main()
