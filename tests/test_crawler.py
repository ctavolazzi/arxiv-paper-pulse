import sys
from pathlib import Path
import pytest
from arxiv_paper_pulse.crawler import crawl

def test_crawler(monkeypatch, tmp_path, capsys):
    # Set up temporary directories.
    temp_raw = tmp_path / "raw"
    temp_raw.mkdir(exist_ok=True)
    temp_summary = tmp_path / "summaries"
    temp_summary.mkdir(exist_ok=True)

    # Override config paths.
    monkeypatch.setattr("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw))
    monkeypatch.setattr("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary))

    # Simulate interactive input:
    # First input for "Do you want to crawl all available articles?" -> "n"
    # Second input for "Enter number of articles to crawl" -> "5"
    inputs = iter(["n", "5"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Simulate CLI arguments.
    monkeypatch.setattr(sys, "argv", ["arxiv-paper-crawler", "--query", "cat:physics", "--default", "10"])

    # Run the crawler.
    crawl()

    # Capture output to ensure prompts and results appear.
    captured = capsys.readouterr().out
    assert "Total available articles for query" in captured
    assert "Starting crawl for" in captured
    assert "Crawl complete. Summarized" in captured
