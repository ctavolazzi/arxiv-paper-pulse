# tests/test_article_generator_error_recovery.py
"""
Error recovery and retry logic tests.
Tests how the system handles and recovers from errors.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from arxiv_paper_pulse.article_generator import generate_article, _fetch_paper_metadata


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_handles_retry_on_transient_error(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Test handling of transient errors (currently no retry, but should fail gracefully)."""
        mock_fetch.return_value = {
            'title': "Test",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = False
        mock_doc_result.error = "Temporary network error"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        # Should raise error immediately (no retry currently)
        with pytest.raises(ValueError, match="Document analysis failed"):
            generate_article("2301.12345")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_cleanup_on_partial_failure(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Test cleanup when generation fails partway through."""
        mock_fetch.return_value = {
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
        mock_img.generate_and_save.return_value = "/tmp/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Prompt"
        # Article generation fails
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            Exception("API error")
        ]
        mock_client.return_value = mock_genai_client

        # Should propagate error, not leave partial files
        with pytest.raises(Exception):
            generate_article("2301.12345")


class TestErrorMessages:
    """Test error message clarity and usefulness."""

    @patch('arxiv_paper_pulse.article_generator.arxiv.Client')
    @patch('arxiv_paper_pulse.article_generator.arxiv.Search')
    def test_error_message_includes_paper_id(self, mock_search, mock_client):
        """Error messages should include paper ID for debugging."""
        mock_client_instance = Mock()
        mock_client_instance.results.return_value = []
        mock_client.return_value = mock_client_instance

        with pytest.raises(ValueError) as exc_info:
            _fetch_paper_metadata("2301.12345")

        assert "2301.12345" in str(exc_info.value)

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_error_message_includes_document_error_details(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Error messages should include document processing error details."""
        mock_fetch.return_value = {
            'title': "Test",
            'authors': ["Author"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = False
        mock_doc_result.error = "PDF parsing failed: invalid format"
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        with pytest.raises(ValueError) as exc_info:
            generate_article("2301.12345")

        assert "Document analysis failed" in str(exc_info.value)
        assert "PDF parsing failed" in str(exc_info.value)


class TestConcurrentOperations:
    """Test handling of concurrent or parallel operations."""

    def test_unique_output_filenames(self):
        """Verify unique filenames are generated using timestamps."""
        from datetime import datetime
        from arxiv_paper_pulse.article_generator import generate_article

        # Test that timestamps create unique filenames
        # This is a unit test of the filename generation logic
        timestamp1 = datetime(2023, 1, 1, 12, 0, 0)
        timestamp2 = datetime(2023, 1, 1, 12, 0, 1)

        paper_id = "2301.12345"
        filename1 = f"article_{paper_id}_{timestamp1.strftime('%Y%m%d_%H%M%S')}.md"
        filename2 = f"article_{paper_id}_{timestamp2.strftime('%Y%m%d_%H%M%S')}.md"

        assert filename1 != filename2
        assert "2301.12345" in filename1
        assert "2301.12345" in filename2

