# tests/test_article_generator_api.py
"""
Tests for article generator API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from pathlib import Path
from arxiv_paper_pulse.api import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestArticleGeneratorAPI:
    """Test API endpoints for article generation."""

    @patch('arxiv_paper_pulse.api.generate_article')
    def test_generate_article_endpoint_success(self, mock_generate_article, client):
        """POST /api/generate-article generates article successfully."""
        mock_generate_article.return_value = "/path/to/article.docx"

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024

        with patch('pathlib.Path', return_value=mock_path):
            response = client.post("/api/generate-article", json={
                "paper_id": "1706.03762",
                "output_format": "docx"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["paper_id"] == "1706.03762"
            assert data["output_format"] == "docx"
            assert data["file_exists"] is True
            assert data["file_size"] == 1024
            mock_generate_article.assert_called_once_with("1706.03762", output_format="docx")

    def test_generate_article_endpoint_missing_paper_id(self, client):
        """POST /api/generate-article returns 400 when paper_id is missing."""
        response = client.post("/api/generate-article", json={
            "output_format": "docx"
        })

        assert response.status_code == 400
        assert "paper_id is required" in response.json()["detail"]

    def test_generate_article_endpoint_invalid_format(self, client):
        """POST /api/generate-article returns 400 for invalid output format."""
        response = client.post("/api/generate-article", json={
            "paper_id": "1706.03762",
            "output_format": "invalid"
        })

        assert response.status_code == 400
        assert "output_format must be" in response.json()["detail"]

    @patch('arxiv_paper_pulse.api.generate_article')
    def test_generate_article_endpoint_handles_error(self, mock_generate_article, client):
        """POST /api/generate-article handles generation errors."""
        mock_generate_article.side_effect = ValueError("Paper not found")

        response = client.post("/api/generate-article", json={
            "paper_id": "9999.99999",
            "output_format": "docx"
        })

        assert response.status_code == 400
        assert "Paper not found" in response.json()["detail"]

    def test_list_articles_endpoint(self, client):
        """GET /api/articles lists all generated articles."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.glob') as mock_glob:
                mock_article = Mock()
                mock_article.name = "article_1706.03762.md"
                mock_article.stat.return_value.st_size = 1024
                mock_article.stat.return_value.st_mtime = 1234567890
                mock_glob.return_value = [mock_article]

                response = client.get("/api/articles")

                assert response.status_code == 200
                data = response.json()
                assert "articles" in data
                assert "count" in data

    def test_list_articles_endpoint_empty(self, client):
        """GET /api/articles returns empty list when no articles exist."""
        with patch('pathlib.Path.exists', return_value=False):
            response = client.get("/api/articles")

            assert response.status_code == 200
            data = response.json()
            assert data["articles"] == []

    def test_get_article_endpoint_not_found(self, client):
        """GET /api/articles/{name} returns 404 when article doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            response = client.get("/api/articles/nonexistent.md")

            assert response.status_code == 404
            assert "Article not found" in response.json()["detail"]

    def test_get_article_endpoint_unsupported_format(self, client):
        """GET /api/articles/{name} returns 400 for unsupported format."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.suffix = ".txt"

        with patch('pathlib.Path', return_value=mock_file):
            response = client.get("/api/articles/test.txt")

            assert response.status_code == 400
            assert "Unsupported file format" in response.json()["detail"]

