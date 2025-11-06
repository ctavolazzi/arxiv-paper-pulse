# tests/test_article_generator_cli.py
"""
Tests for article generator CLI commands.
"""
import pytest
from unittest.mock import patch, Mock
from arxiv_paper_pulse.cli import main_article


class TestArticleGeneratorCLI:
    """Test CLI command for article generation."""

    @patch('arxiv_paper_pulse.article_generator.generate_article')
    def test_cli_generates_article_with_default_format(self, mock_generate_article):
        """CLI generates article with default DOCX format."""
        mock_generate_article.return_value = "/path/to/article.docx"

        result = main_article(['1706.03762'])
        assert result == 0
        mock_generate_article.assert_called_once_with("1706.03762", output_format="docx")

    @patch('arxiv_paper_pulse.article_generator.generate_article')
    def test_cli_generates_article_with_markdown_format(self, mock_generate_article):
        """CLI generates article with markdown format."""
        mock_generate_article.return_value = "/path/to/article.md"

        result = main_article(['1706.03762', '--format', 'md'])
        assert result == 0
        mock_generate_article.assert_called_once_with("1706.03762", output_format="md")

    @patch('arxiv_paper_pulse.article_generator.generate_article')
    def test_cli_handles_generation_error(self, mock_generate_article):
        """CLI handles article generation errors gracefully."""
        mock_generate_article.side_effect = ValueError("Paper not found")

        result = main_article(['9999.99999'])
        assert result == 1
        mock_generate_article.assert_called_once_with("9999.99999", output_format="docx")

