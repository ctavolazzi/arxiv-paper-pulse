# tests/test_api_endpoints.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from arxiv_paper_pulse.api import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_summarizer():
    """Mock summarizer for API tests"""
    with patch('arxiv_paper_pulse.api.get_summarizer') as mock_get:
        mock_summarizer = Mock()
        mock_summarizer.summarize_papers.return_value = [
            {"title": "Test Paper", "summary": "Test summary", "id": "test1"}
        ]
        mock_get.return_value = mock_summarizer
        yield mock_summarizer


class TestBasicEndpoints:
    """Tests for basic API endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code in [200, 404]  # 404 if no frontend

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "default_model" in data


class TestSummarizeEndpoints:
    """Tests for summarization endpoints"""

    def test_summarize_endpoint(self, client, mock_summarizer):
        """Test summarize endpoint"""
        response = client.post(
            "/api/summarize",
            params={"query": "cat:cs.AI", "max_results": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_summarize_pdf_endpoint(self, client, mock_summarizer):
        """Test PDF summarization endpoint"""
        with patch.object(mock_summarizer, 'gemini_summarize_from_pdf') as mock_pdf:
            mock_pdf.return_value = "PDF summary"

            response = client.post(
                "/api/summarize-pdf",
                params={"paper_id": "2301.12345"}
            )
            assert response.status_code == 200

    def test_summarize_structured_endpoint(self, client, mock_summarizer):
        """Test structured output endpoint"""
        with patch.object(mock_summarizer, 'gemini_summarize') as mock_structured:
            from arxiv_paper_pulse.models import PaperAnalysis, Methodology, Results
            mock_analysis = PaperAnalysis(
                problem_statement="Test",
                methodology=Methodology(approach="test"),
                results=Results(key_findings=[]),
                contributions=[],
                limitations=[],
                future_work=[],
                relevance_score=5
            )
            mock_structured.return_value = mock_analysis

            response = client.post(
                "/api/summarize-structured",
                params={"abstract": "Test abstract"}
            )
            assert response.status_code == 200


class TestAdvancedEndpoints:
    """Tests for advanced API endpoints"""

    def test_analyze_multiple_endpoint(self, client, mock_summarizer):
        """Test multi-paper analysis endpoint"""
        with patch.object(mock_summarizer, 'analyze_multiple_papers') as mock_analyze:
            mock_analyze.return_value = "Comparative analysis"

            response = client.post(
                "/api/analyze-multiple",
                json={"paper_ids": ["2301.12345", "2302.12345"]}
            )
            assert response.status_code == 200

    def test_url_context_endpoint(self, client):
        """Test URL context endpoint"""
        with patch('arxiv_paper_pulse.api.get_summarizer') as mock_get:
            mock_summarizer = Mock()
            mock_summarizer.gemini_summarize_with_url_context.return_value = "URL summary"
            mock_get.return_value = mock_summarizer

            response = client.post(
                "/api/url-context",
                params={"paper_url": "https://arxiv.org/abs/2301.12345"}
            )
            assert response.status_code == 200

    def test_embeddings_generate_endpoint(self, client):
        """Test embeddings generation endpoint"""
        with patch('arxiv_paper_pulse.api.PaperEmbeddings') as mock_embeddings:
            mock_gen = Mock()
            mock_gen.generate_batch_embeddings.return_value = {"paper1": [0.1, 0.2]}
            mock_embeddings.return_value = mock_gen

            response = client.post(
                "/api/embeddings/generate",
                json={"papers": [{"title": "Test", "abstract": "Test"}]}
            )
            assert response.status_code == 200


class TestBatchEndpoints:
    """Tests for batch processing endpoints"""

    def test_batch_submit_endpoint(self, client):
        """Test batch submission endpoint"""
        with patch('arxiv_paper_pulse.api.BatchPaperProcessor') as mock_batch:
            mock_processor = Mock()
            mock_processor.submit_batch.return_value = "batch_id_123"
            mock_batch.return_value = mock_processor

            response = client.post(
                "/api/batch/submit",
                json={"papers": [{"abstract": "Test"}]}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_batch_status_endpoint(self, client):
        """Test batch status endpoint"""
        with patch('arxiv_paper_pulse.api.BatchPaperProcessor') as mock_batch:
            mock_processor = Mock()
            mock_processor.check_batch_status.return_value = {"state": "COMPLETED"}
            mock_batch.return_value = mock_processor

            response = client.get("/api/batch/test_batch_id/status")
            assert response.status_code == 200

