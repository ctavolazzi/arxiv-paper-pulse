# tests/test_article_generator.py
"""
Test suite for article generator module.
Follows TDD principles: fast, isolated, mocked, comprehensive.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from arxiv_paper_pulse.article_generator import (
    generate_article,
    _extract_paper_id,
    _fetch_paper_metadata
)


class TestExtractPaperID:
    """Test paper ID extraction from various input formats."""

    def test_extracts_id_from_abs_url(self):
        """Extract ID from arXiv abs URL."""
        assert _extract_paper_id("https://arxiv.org/abs/2301.12345") == "2301.12345"

    def test_extracts_id_from_pdf_url(self):
        """Extract ID from arXiv PDF URL."""
        assert _extract_paper_id("https://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"

    def test_extracts_id_from_plain_id(self):
        """Extract ID from plain ID string."""
        assert _extract_paper_id("2301.12345") == "2301.12345"

    def test_extracts_id_with_version_suffix(self):
        """Extract ID with version suffix."""
        assert _extract_paper_id("https://arxiv.org/abs/2301.12345v1") == "2301.12345v1"

    def test_handles_arxiv_org_in_path(self):
        """Handle various arxiv.org URL formats."""
        assert _extract_paper_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
        assert _extract_paper_id("http://arxiv.org/pdf/1706.03762") == "1706.03762"


class TestFetchPaperMetadata:
    """Test paper metadata fetching with mocks."""

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_fetches_metadata_successfully(self, mock_search, mock_client):
        """Fetch paper metadata returns all required fields."""
        # Setup mocks
        mock_author1 = Mock()
        mock_author1.name = "Author One"
        mock_author2 = Mock()
        mock_author2.name = "Author Two"

        mock_paper = Mock()
        mock_paper.title = "Test Paper Title"
        mock_paper.authors = [mock_author1, mock_author2]
        mock_paper.published = "2023-01-15"
        mock_paper.entry_id = "http://arxiv.org/abs/2301.12345"

        mock_client_instance = Mock()
        mock_client_instance.results.return_value = [mock_paper]
        mock_client.return_value = mock_client_instance

        # Execute
        metadata = _fetch_paper_metadata("2301.12345")

        # Verify
        assert metadata['title'] == "Test Paper Title"
        assert metadata['authors'] == ["Author One", "Author Two"]
        assert metadata['published'] == "2023-01-15"
        assert metadata['paper_id'] == "2301.12345"
        assert metadata['arxiv_url'] == "http://arxiv.org/abs/2301.12345"

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_raises_error_when_paper_not_found(self, mock_search, mock_client):
        """Raise ValueError when paper doesn't exist."""
        mock_client_instance = Mock()
        mock_client_instance.results.return_value = []
        mock_client.return_value = mock_client_instance

        with pytest.raises(ValueError, match="Paper .* not found"):
            _fetch_paper_metadata("9999.99999")

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_handles_empty_authors_list(self, mock_search, mock_client):
        """Handle papers with no authors gracefully."""
        mock_paper = Mock()
        mock_paper.title = "Test Paper"
        mock_paper.authors = []
        mock_paper.published = "2023-01-01"
        mock_paper.entry_id = "http://arxiv.org/abs/2301.12345"

        mock_client_instance = Mock()
        mock_client_instance.results.return_value = [mock_paper]
        mock_client.return_value = mock_client_instance

        metadata = _fetch_paper_metadata("2301.12345")
        assert metadata['authors'] == []


class TestGenerateArticle:
    """Test complete article generation with all external dependencies mocked."""

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_generates_markdown_article(self, mock_fetch_metadata, mock_client, mock_doc_processor, mock_img_generator):
        """Generate markdown article with all dependencies mocked."""
        # Setup mocks
        mock_fetch_metadata.return_value = {
            'title': "Test Paper",
            'authors': ["Author One"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Test analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt text"
        mock_article_response = Mock()
        mock_article_response.text = "# Test Paper\n\nArticle content here."
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Execute
        result_path = generate_article("2301.12345", output_format="md")

        # Verify
        assert result_path.endswith(".md")
        assert Path(result_path).exists()

        content = Path(result_path).read_text()
        assert "Test Paper" in content
        assert "Author One" in content

        # Cleanup
        Path(result_path).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_generates_docx_article(self, mock_fetch_metadata, mock_client, mock_doc_processor, mock_img_generator):
        """Generate DOCX article with all dependencies mocked."""
        # Setup mocks
        mock_fetch_metadata.return_value = {
            'title': "Test Paper",
            'authors': ["Author One"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Test analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt text"
        mock_article_response = Mock()
        mock_article_response.text = "# Test Paper\n\nArticle content here."
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Execute
        result_path = generate_article("2301.12345", output_format="docx")

        # Verify
        assert result_path.endswith(".docx")
        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0

        # Cleanup
        Path(result_path).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_raises_error_for_invalid_output_format(self, mock_fetch_metadata, mock_client, mock_doc_processor, mock_img_generator):
        """Raise ValueError for unsupported output formats."""
        # Setup mocks to get to the format check
        mock_fetch_metadata.return_value = {
            'title': "Test",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Execute with invalid format
        with pytest.raises(ValueError, match="Unsupported output format"):
            generate_article("2301.12345", output_format="invalid")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_document_processing_failure(self, mock_fetch_metadata, mock_client, mock_doc_processor, mock_img_generator):
        """Raise ValueError when document processing fails."""
        mock_fetch_metadata.return_value = {
            'title': "Test",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = False
        mock_doc_result.error = "Processing failed"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        with pytest.raises(ValueError, match="Document analysis failed"):
            generate_article("2301.12345", output_format="md")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_creates_output_directory_if_missing(self, mock_fetch_metadata, mock_client, mock_doc_processor, mock_img_generator):
        """Create output directory if it doesn't exist."""
        # Setup mocks
        mock_fetch_metadata.return_value = {
            'title': "Test",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Execute
        result = generate_article("2301.12345", output_format="md")

        # Verify directory was created (implied by successful file creation)
        assert Path(result).parent.exists()

        # Cleanup
        Path(result).unlink()
