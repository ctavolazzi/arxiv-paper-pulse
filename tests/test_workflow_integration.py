import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from arxiv_paper_pulse.core import ArxivSummarizer

class MockArxivPaper:
    """Mock class that mimics the arxiv.Result object structure"""
    def __init__(self, data):
        self.entry_id = data['entry_id']
        self.title = data['title']
        self.published = datetime.strptime(data['published'], "%Y-%m-%dT%H:%M:%SZ")
        self.summary = data['abstract']
        self.authors = []
        self.links = []
        self.pdf_url = f"http://arxiv.org/pdf/{self.entry_id}"
        self.categories = ["cs.AI"]

@pytest.fixture
def mock_paper_data():
    """Generate mock paper data for testing."""
    data = [
        {
            "entry_id": "2401.01234",
            "title": "Test Paper 1: Neural Network Optimization",
            "published": "2023-01-01T00:00:00Z",
            "abstract": "This is a test abstract for paper 1",
        },
        {
            "entry_id": "2401.56789",
            "title": "Test Paper 2: Advanced AI Methods",
            "published": "2023-01-02T00:00:00Z",
            "abstract": "This is a test abstract for paper 2",
        },
        {
            "entry_id": "2401.12345",
            "title": "Test Paper 3: Deep Learning Applications",
            "published": "2023-01-03T00:00:00Z",
            "abstract": "This is a test abstract for paper 3",
        }
    ]
    return [MockArxivPaper(paper) for paper in data]

@pytest.fixture
def mock_ollama_response():
    """Mock response from Ollama."""
    return """1. Key Problem & Research Question: This paper addresses the challenge of optimizing neural networks.

2. Methodology & Approach: The authors used a novel gradient-based technique.

3. Main Findings & Contributions: The approach shows 20% better performance than previous methods.

4. Implications & Significance:
   - This could lead to faster training of large models
   - Industry applications include more efficient deployment on edge devices
   - This may change how we approach model architecture design

5. Limitations & Future Directions: The method has higher memory requirements and future work will focus on reducing this overhead."""

@pytest.fixture
def mock_ollama_synthesis_response():
    """Mock synthesis response from Ollama."""
    return """# Executive Summary

The recent publications in AI research reveal significant advances in neural network optimization, reinforcement learning, and real-world applications. These developments have important implications for both theoretical understanding and practical deployment of AI systems.

## Key Insights

- **Neural network optimization techniques** are showing 20% performance improvements, potentially enabling faster training cycles and more efficient model deployment on edge devices.

- **Advanced AI methods** are increasingly focused on interpretability and robustness, addressing critical concerns for real-world deployment in sensitive domains.

- **Deep learning applications** continue to expand into new domains, with particular growth in healthcare, climate science, and autonomous systems.

## Implications

These findings collectively suggest that AI is maturing beyond performance metrics alone, with greater emphasis on practical deployment considerations and societal impact. Organizations should prepare for both technical integration challenges and ethical governance requirements as these technologies become more pervasive.

## Looking Forward

Watch for emerging research that further addresses memory constraints and energy efficiency, as these remain the primary barriers to widespread deployment of advanced AI systems."""

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

@pytest.mark.integration
def test_full_workflow_with_mocks(setup_test_dirs, mock_paper_data, mock_ollama_response, mock_ollama_synthesis_response):
    """
    Test the full workflow from paper selection to briefing generation, using mocks.

    This is a comprehensive integration test that verifies:
    1. Paper data fetching
    2. Paper selection
    3. Summarization
    4. Briefing generation
    5. Final synthesis
    """
    # Mock arxiv client and ollama calls
    with patch('arxiv.Client') as mock_client, \
         patch('subprocess.run') as mock_subprocess:

        # Mock the arxiv search results
        mock_search_results = MagicMock()
        mock_search_results.results.return_value = mock_paper_data
        mock_client.return_value = mock_search_results

        # Mock subprocess.run to return our mock responses
        def mock_run_subprocess(args, **kwargs):
            # For ollama list command
            if args[0] == "ollama" and args[1] == "list":
                return MagicMock(stdout="NAME        ID      SIZE  MODIFIED\nllama2      latest 3.8 GB 7 hours ago\n",
                               stderr="", returncode=0)
            # For paper summarization
            elif len(args) == 3 and args[0] == "ollama" and args[1] == "run":
                mock_response = mock_ollama_response

                # If this is the synthesis prompt, use the synthesis response
                if "Article Summaries:" in args[2]:
                    mock_response = mock_ollama_synthesis_response

                return MagicMock(stdout=mock_response, stderr="", returncode=0)
            return MagicMock(stdout="", stderr="", returncode=0)

        mock_subprocess.side_effect = mock_run_subprocess

        # Create the summarizer
        summarizer = ArxivSummarizer(max_results=3, query="test:query")

        # 1. Fetch raw data
        raw_data = summarizer.fetch_raw_data(force_pull=True)
        assert len(raw_data) == 3, "Should fetch 3 papers"

        # 2. Select specific papers (papers 1 and 3)
        selected_papers = [raw_data[0], raw_data[2]]

        # 3. Summarize the selected papers
        summaries = summarizer.summarize_selected_papers(selected_papers)
        assert len(summaries) == 2, "Should summarize 2 papers"

        # 4. Verify that summaries were generated
        assert all("summary" in paper for paper in summaries)
        assert all(paper["summary"] == mock_ollama_response for paper in summaries)

        # 5. Verify that a briefing file was created
        assert summarizer.briefing_file.exists()

        # 6. Read the briefing content
        briefing_content = summarizer.briefing_file.read_text()

        # 7. Verify the briefing structure and content
        assert "# ArXiv Research Briefing" in briefing_content
        assert "**Search Query:** `test:query`" in briefing_content
        assert "## Articles" in briefing_content
        assert "## Executive Summary" in briefing_content

        # 8. Verify that paper titles are in the briefing
        assert "Test Paper 1: Neural Network Optimization" in briefing_content
        assert "Test Paper 3: Deep Learning Applications" in briefing_content
        assert "Test Paper 2: Advanced AI Methods" not in briefing_content  # This one wasn't selected

        # 9. Verify that summaries were added to the briefing
        assert "Key Problem & Research Question" in briefing_content
        assert "Implications & Significance" in briefing_content

        # 10. Verify that the executive summary was added
        assert "Key Insights" in briefing_content
        assert "Neural network optimization techniques" in briefing_content
        assert "Looking Forward" in briefing_content

@pytest.mark.skipif(not os.environ.get("RUN_LIVE_TESTS"), reason="Live tests skipped by default")
def test_live_workflow():
    """
    A real integration test using actual API calls (skipped by default).

    To run this test, set the RUN_LIVE_TESTS environment variable:
    RUN_LIVE_TESTS=1 pytest -xvs tests/test_workflow_integration.py::test_live_workflow
    """
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_raw = temp_path / "raw"
        temp_raw.mkdir()
        temp_summary = temp_path / "summaries"
        temp_summary.mkdir()
        temp_briefing = temp_path / "briefings"
        temp_briefing.mkdir()

        # Override config paths for this test
        with patch("arxiv_paper_pulse.config.RAW_DATA_DIR", str(temp_raw)), \
             patch("arxiv_paper_pulse.config.SUMMARY_DIR", str(temp_summary)), \
             patch("arxiv_paper_pulse.config.BRIEFING_DIR", str(temp_briefing)):

            # Create summarizer with a very limited query to avoid long test times
            summarizer = ArxivSummarizer(max_results=2, query="cat:cs.AI AND ti:neural")

            # Fetch raw data
            raw_data = summarizer.fetch_raw_data(force_pull=True)

            # Make sure we got some papers
            assert len(raw_data) > 0, "No papers found for the test query"

            # Select the first paper only
            selected_papers = [raw_data[0]]

            # Summarize it
            summaries = summarizer.summarize_selected_papers(selected_papers)

            # Verify we got a summary
            assert len(summaries) == 1
            assert "summary" in summaries[0]

            # Verify the briefing file was created
            assert summarizer.briefing_file.exists()

            # Verify the briefing content
            briefing_content = summarizer.briefing_file.read_text()
            assert "# ArXiv Research Briefing" in briefing_content
            assert "## Executive Summary" in briefing_content