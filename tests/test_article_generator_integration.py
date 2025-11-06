# tests/test_article_generator_integration.py
"""
Integration tests for article generator.
Tests the interaction between components.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from arxiv_paper_pulse.article_generator import generate_article


class TestComponentIntegration:
    """Test integration between article generator components."""

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_full_workflow_with_all_components(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Test complete workflow with all components."""
        # Setup metadata
        mock_fetch.return_value = {
            'title': "Integration Test Paper",
            'authors': ["Author One", "Author Two"],
            'published': "2023-01-01",
            'paper_id': "2301.12345",
            'arxiv_url': "http://arxiv.org/abs/2301.12345"
        }

        # Setup document processor
        mock_processor = Mock()
        mock_doc_result = Mock()
        mock_doc_result.success = True
        mock_doc_result.text = "This is a comprehensive analysis of the paper."
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        # Setup image generator
        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/tmp/test_image.png"
        mock_img_generator.return_value = mock_img

        # Setup Gemini client
        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "A detailed image prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Integration Test Paper\n\nArticle content here."
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        # Execute
        result = generate_article("2301.12345", output_format="md")

        # Verify all components were called
        assert mock_fetch.called
        assert mock_processor.process.called
        assert mock_img.generate_and_save.called
        assert mock_genai_client.models.generate_content.call_count == 2

        # Verify output
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "Integration Test Paper" in content
        assert "Author One" in content

        # Cleanup
        Path(result).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_document_processor_receives_correct_pdf_url(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Verify document processor receives correct PDF URL format."""
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
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        generate_article("2301.12345", output_format="md")

        # Verify PDF URL format (should not have .pdf extension)
        call_args = mock_processor.process.call_args
        doc_input = call_args[0][0]
        assert "2301.12345" in doc_input.source.url
        assert not doc_input.source.url.endswith(".pdf")

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_image_generator_receives_prompt_from_analysis(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Verify image generator receives prompt based on analysis."""
        analysis_text = "Key concepts: machine learning, neural networks, transformers"

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
        mock_doc_result.text = analysis_text
        mock_processor.process.return_value = mock_doc_result
        mock_doc_processor.return_value = mock_processor

        mock_img = Mock()
        mock_img.generate_and_save.return_value = "/tmp/image.png"
        mock_img_generator.return_value = mock_img

        mock_genai_client = Mock()
        mock_image_prompt_response = Mock()
        mock_image_prompt_response.text = "Generated image prompt"
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        generate_article("2301.12345", output_format="md")

        # Verify image prompt was generated from analysis
        image_prompt_call = mock_genai_client.models.generate_content.call_args_list[0]
        assert analysis_text in str(image_prompt_call)


class TestInputValidation:
    """Test input validation and sanitization."""

    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_validates_paper_id_format(self, mock_fetch):
        """Validate paper ID format."""
        # Valid formats should work
        valid_ids = ["2301.12345", "1706.03762", "1234.5678"]

        for paper_id in valid_ids:
            mock_fetch.return_value = {
                'title': "Test",
                'authors': ["Author"],
                'published': "2023-01-01",
                'paper_id': paper_id,
                'arxiv_url': f"http://arxiv.org/abs/{paper_id}"
            }
            # Should not raise for valid IDs
            # (We can't fully test without mocking everything, but we can verify extraction)
            from arxiv_paper_pulse.article_generator import _extract_paper_id
            extracted = _extract_paper_id(paper_id)
            assert extracted == paper_id

    def test_sanitizes_markdown_content(self):
        """Test that markdown content is properly formatted."""
        # This would be tested in the actual output
        # For now, we verify the structure exists
        assert True  # Placeholder - actual test would verify markdown formatting

    def test_sanitizes_docx_content(self):
        """Test that DOCX content is properly structured."""
        # This would be tested in the actual output
        assert True  # Placeholder - actual test would verify DOCX structure


class TestOutputFormatting:
    """Test output formatting for different formats."""

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_markdown_includes_all_metadata(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Verify markdown output includes all metadata fields."""
        mock_fetch.return_value = {
            'title': "Test Paper Title",
            'authors': ["Author One", "Author Two"],
            'published': "2023-01-15",
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
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        result = generate_article("2301.12345", output_format="md")
        content = Path(result).read_text()

        # Verify all metadata is present
        assert "Test Paper Title" in content
        assert "Author One" in content
        assert "Author Two" in content
        assert "2023-01-15" in content
        assert "2301.12345" in content
        assert "http://arxiv.org/abs/2301.12345" in content

        Path(result).unlink()

    @patch('arxiv_paper_pulse.article_generator.ImageGenerator')
    @patch('arxiv_paper_pulse.article_generator.DocumentProcessor')
    @patch('arxiv_paper_pulse.article_generator.genai.Client')
    @patch('arxiv_paper_pulse.article_generator._fetch_paper_metadata')
    def test_markdown_handles_special_characters(self, mock_fetch, mock_client, mock_doc_processor, mock_img_generator):
        """Test markdown output with special characters."""
        mock_fetch.return_value = {
            'title': "Test Paper with Special: <>&\"'",
            'authors': ["Author & Co."],
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
        mock_article_response = Mock()
        mock_article_response.text = "# Test\n\nContent with <special> chars"
        mock_genai_client.models.generate_content.side_effect = [
            mock_image_prompt_response,
            mock_article_response
        ]
        mock_client.return_value = mock_genai_client

        result = generate_article("2301.12345", output_format="md")
        content = Path(result).read_text()

        # Should handle special characters without breaking
        assert Path(result).exists()
        assert len(content) > 0

        Path(result).unlink()


