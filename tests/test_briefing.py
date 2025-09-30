import json
import re
from pathlib import Path
import pytest
from datetime import datetime

from arxiv_paper_pulse.core import ArxivSummarizer
from arxiv_paper_pulse import config

@pytest.fixture
def mock_ollama_summarize(monkeypatch):
    """Mock the Ollama summarization to return a known result."""
    def mock_summarize(self, text):
        return """1. Key Problem & Research Question: This paper addresses the challenge of optimizing neural networks.

2. Methodology & Approach: The authors used a novel gradient-based technique.

3. Main Findings & Contributions: The approach shows 20% better performance than previous methods.

4. Implications & Significance:
   - This could lead to faster training of large models
   - Industry applications include more efficient deployment on edge devices
   - This may change how we approach model architecture design

5. Limitations & Future Directions: The method has higher memory requirements and future work will focus on reducing this overhead."""

    monkeypatch.setattr(ArxivSummarizer, "ollama_summarize", mock_summarize)

@pytest.fixture
def mock_paper_data():
    """Generate mock paper data for testing."""
    return [
        {
            "entry_id": "2401.01234",
            "title": "Test Paper 1: Neural Network Optimization",
            "published": "2023-01-01T00:00:00Z",
            "url": "http://arxiv.org/abs/2401.01234",
            "abstract": "This is a test abstract for paper 1",
            "query": "test query",
            "id": "unique_id_1"
        },
        {
            "entry_id": "2401.56789",
            "title": "Test Paper 2: Advanced AI Methods",
            "published": "2023-01-02T00:00:00Z",
            "url": "http://arxiv.org/abs/2401.56789",
            "abstract": "This is a test abstract for paper 2",
            "query": "test query",
            "id": "unique_id_2"
        }
    ]

@pytest.fixture
def setup_test_dirs(tmp_path, monkeypatch):
    """Set up temporary directories for testing."""
    # Create temp dirs
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

    return {"raw": temp_raw, "summary": temp_summary, "briefing": temp_briefing}

def test_initialize_briefing_file(setup_test_dirs):
    """Test that a briefing file is correctly initialized."""
    summarizer = ArxivSummarizer(query="test:query")
    summarizer.initialize_briefing_file()

    # Check that the file was created
    assert summarizer.briefing_file.exists()

    # Check the content of the file
    content = summarizer.briefing_file.read_text()
    assert "# ArXiv Research Briefing:" in content
    assert "**Date:**" in content
    assert "**Search Query:** `test:query`" in content
    assert "## Articles" in content

def test_update_briefing_report(setup_test_dirs, mock_ollama_summarize, mock_paper_data):
    """Test that a paper summary is correctly added to the briefing file."""
    summarizer = ArxivSummarizer(query="test:query")
    summarizer.initialize_briefing_file()

    # Mock a paper with a summary
    paper = mock_paper_data[0]
    paper["summary"] = summarizer.ollama_summarize(paper["abstract"])

    # Update the briefing with the paper
    summarizer.update_briefing_report(paper)

    # Check the content of the updated file
    content = summarizer.briefing_file.read_text()
    assert paper["title"] in content
    assert "**Published:**" in content
    assert "#### Key Insights:" in content
    assert "- **Key Problem & Research Question:" in content, "Bullet points were not formatted correctly"
    assert "---" in content, "Separator not found in briefing"

def test_generate_final_briefing(setup_test_dirs, mock_ollama_summarize, mock_paper_data):
    """Test that a final briefing synthesis is correctly generated."""
    summarizer = ArxivSummarizer(query="test:query")
    summarizer.initialize_briefing_file()

    # Add multiple papers to the briefing
    for paper in mock_paper_data:
        paper["summary"] = summarizer.ollama_summarize(paper["abstract"])
        summarizer.update_briefing_report(paper)

    # Generate the final briefing
    summarizer.generate_final_briefing()

    # Check the content of the final briefing
    content = summarizer.briefing_file.read_text()
    assert "## Executive Summary" in content
    assert "*This briefing was automatically generated using ArXiv Paper Pulse and a local Ollama model.*" in content

def test_summarize_selected_papers(setup_test_dirs, mock_ollama_summarize, mock_paper_data):
    """Test the summarize_selected_papers method."""
    summarizer = ArxivSummarizer(query="test:query")

    # Summarize only selected papers
    summaries = summarizer.summarize_selected_papers(mock_paper_data, force_pull=True)

    # Check that summaries were generated correctly
    assert len(summaries) == len(mock_paper_data)
    for paper in summaries:
        assert "summary" in paper
        assert paper["summary"].startswith("1. Key Problem & Research Question")

    # Check that the briefing file was created and updated
    assert summarizer.briefing_file.exists()
    content = summarizer.briefing_file.read_text()
    assert "## Executive Summary" in content

    # Check that the summary JSON was saved
    summary_dir = Path(config.SUMMARY_DIR)
    summary_files = list(summary_dir.glob("*_summary.json"))
    assert len(summary_files) == 1

    # Verify the content of the summary file
    with open(summary_files[0], "r") as f:
        saved_summaries = json.load(f)
    assert len(saved_summaries) == len(mock_paper_data)
    assert all("summary" in paper for paper in saved_summaries)

def test_markdown_formatting(setup_test_dirs, mock_ollama_summarize, mock_paper_data):
    """Test that the markdown formatting in the briefing file is correct."""
    summarizer = ArxivSummarizer(query="test:query")
    summarizer.initialize_briefing_file()

    # Add a paper to the briefing
    paper = mock_paper_data[0]
    paper["summary"] = summarizer.ollama_summarize(paper["abstract"])
    summarizer.update_briefing_report(paper)

    # Check the markdown formatting
    content = summarizer.briefing_file.read_text()

    # Check heading levels
    assert re.search(r"^# ArXiv Research Briefing:", content, re.MULTILINE), "Main heading not found"
    assert re.search(r"^## Articles", content, re.MULTILINE), "Articles section heading not found"
    assert re.search(r"^### \[.*\]", content, re.MULTILINE), "Paper title heading not found"
    assert re.search(r"^#### Key Insights:", content, re.MULTILINE), "Key Insights heading not found"

    # Check link formatting
    assert re.search(r"\[.*\]\(http.*\)", content), "Paper title link not formatted correctly"

    # Check bullet point formatting
    assert re.search(r"- \*\*.*\*\*", content), "Bullet points not formatted correctly"