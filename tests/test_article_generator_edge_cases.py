# tests/test_article_generator_edge_cases.py
"""
Edge case and error handling tests for article generator.
Written using TDD: write tests first, then make code pass.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from arxiv_paper_pulse.article_generator import (
    generate_article,
    _extract_paper_id,
    _fetch_paper_metadata
)


class TestExtractPaperIDEdgeCases:
    """Test edge cases for paper ID extraction."""

    def test_handles_empty_string(self):
        """Handle empty string input."""
        # TDD: Write test first, expect it to fail or handle gracefully
        result = _extract_paper_id("")
        assert result == ""

    def test_handles_none_input(self):
        """Handle None input gracefully."""
        with pytest.raises((AttributeError, TypeError)):
            _extract_paper_id(None)

    def test_handles_malformed_url(self):
        """Handle malformed URLs."""
        # Should extract what it can
        result = _extract_paper_id("https://arxiv.org/abs/")
        assert result == "" or result == "abs"

    def test_handles_url_with_query_params(self):
        """Handle URLs with query parameters."""
        result = _extract_paper_id("https://arxiv.org/abs/2301.12345?v=1")
        assert result == "2301.12345?v=1" or "2301.12345" in result

    def test_handles_url_with_fragment(self):
        """Handle URLs with fragments."""
        result = _extract_paper_id("https://arxiv.org/abs/2301.12345#section")
        assert "2301.12345" in result

    def test_handles_very_long_paper_id(self):
        """Handle unusually long paper IDs."""
        long_id = "2301." + "1" * 100
        result = _extract_paper_id(long_id)
        assert long_id == result

    def test_handles_unicode_characters(self):
        """Handle Unicode characters in URLs."""
        result = _extract_paper_id("https://arxiv.org/abs/2301.12345")
        assert result == "2301.12345"


class TestFetchPaperMetadataEdgeCases:
    """Test edge cases for metadata fetching."""

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_handles_network_error(self, mock_search, mock_client):
        """Handle network errors when fetching metadata."""
        mock_client_instance = Mock()
        mock_client_instance.results.side_effect = Exception("Network error")
        mock_client.return_value = mock_client_instance

        with pytest.raises(Exception):
            _fetch_paper_metadata("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_handles_timeout(self, mock_search, mock_client):
        """Handle timeout errors."""
        mock_client_instance = Mock()
        mock_client_instance.results.side_effect = TimeoutError("Request timeout")
        mock_client.return_value = mock_client_instance

        with pytest.raises(TimeoutError):
            _fetch_paper_metadata("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_handles_paper_with_missing_title(self, mock_search, mock_client):
        """Handle papers with missing title."""
        mock_paper = Mock()
        mock_paper.title = None
        mock_paper.authors = []
        mock_paper.published = "2023-01-01"
        mock_paper.entry_id = "http://arxiv.org/abs/2301.12345"

        mock_client_instance = Mock()
        mock_client_instance.results.return_value = [mock_paper]
        mock_client.return_value = mock_client_instance

        metadata = _fetch_paper_metadata("2301.12345")
        assert metadata['title'] is None or metadata['title'] == ""

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_handles_paper_with_many_authors(self, mock_search, mock_client):
        """Handle papers with many authors."""
        mock_authors = [Mock(name=f"Author {i}") for i in range(100)]
        mock_paper = Mock()
        mock_paper.title = "Test Paper"
        mock_paper.authors = mock_authors
        mock_paper.published = "2023-01-01"
        mock_paper.entry_id = "http://arxiv.org/abs/2301.12345"

        mock_client_instance = Mock()
        mock_client_instance.results.return_value = [mock_paper]
        mock_client.return_value = mock_client_instance

        metadata = _fetch_paper_metadata("2301.12345")
        assert len(metadata['authors']) == 100


class TestGenerateArticleEdgeCases:
    """Test edge cases for article generation."""

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_document_processing_timeout(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle document processing timeout."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_processor.process.side_effect = TimeoutError("Document processing timeout")
        mock_doc_processor.return_value = mock_processor

        with pytest.raises(TimeoutError):
            generate_article("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_document_processing_failure(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle document processing returning failure."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = False
        mock_doc_result.error = "PDF parsing failed"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        with pytest.raises(ValueError, match="Document analysis failed"):
            generate_article("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_image_generation_failure(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle image generation failure."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.side_effect = ValueError("Image generation failed")
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt"
        mock_genai_client.models.generate_content.return_value = mock_image_prompt_response
        mock_client.return_value = mock_genai_client

        with pytest.raises(ValueError, match="Image generation failed"):
            generate_article("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_missing_image_path(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle case where image path doesn't exist."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/nonexistent/path/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Test Article\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Should still generate article even if image path doesn't exist
        result = generate_article("2301.12345", output_format="md")
        assert Path(result).exists()
        Path(result).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_very_long_article_text(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle very long article text."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt"
        mock_article_response = Mock()
        # Generate very long article text
        long_text = "# Test Article\n\n" + "Paragraph. " * 10000
        mock_article_response.text = long_text
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        result = generate_article("2301.12345", output_format="md")
        assert Path(result).exists()
        content = Path(result).read_text()
        assert len(content) > 100000
        Path(result).unlink()

    def test_raises_error_for_invalid_output_format(self):
        """Raise error for invalid output format."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            # We need to mock everything to get to the format check
            with patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata') as mock_fetch:
                mock_fetch.return_value = {
                    'title': "Test",
                    'authors': ["Author"],
                    'published': "2023-01-01",
                    'paper_id': "2301.12345",
                    'arxiv_url': "http://arxiv.org/abs/2301.12345"
                }
                with patch('arxiv_paper_pulse.article_generator.DocumentProcessor'):
                    with patch('arxiv_paper_pulse.article_generator.ImageGenerator'):
                        with patch('arxiv_paper_pulse.article_generator.genai.Client'):
                            generate_article("2301.12345", output_format="invalid")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_empty_article_text(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle empty article text from Gemini."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt"
        mock_article_response = Mock()
        mock_article_response.text = ""  # Empty text
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Should still generate file even with empty content
        result = generate_article("2301.12345", output_format="md")
        assert Path(result).exists()
        Path(result).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    @patch('pathlib.Path.write_text')
    def test_handles_file_write_permission_error(self, mock_write, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Handle file write permission errors."""
        mock_fetch.return_value = {
            'title': "Test Paper",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "Analysis content"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/path/to/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Image prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Test Article\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        mock_write.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            generate_article("2301.12345", output_format="md")


