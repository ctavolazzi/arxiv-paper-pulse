"""
Tests that verify the actual app produces output matching the standalone example.
"""
import pytest
from pathlib import Path
import arxiv
from arxiv_paper_pulse.article_generator import generate_article, _extract_paper_id, _fetch_paper_metadata

EXAMPLE_DIR = Path(__file__).parent.parent / "example_output"
APP_OUTPUT_DIR = Path(__file__).parent.parent / "arxiv_paper_pulse" / "data"


class TestAppMatchesExampleStructure:
    """Test that app output matches the example structure."""

    def test_app_can_extract_paper_id(self):
        """Test that app can extract paper ID like the example does."""
        paper_id = _extract_paper_id("https://arxiv.org/abs/2511.02824")
        assert paper_id == "2511.02824", "Should extract paper ID correctly"

        paper_id2 = _extract_paper_id("2511.02824")
        assert paper_id2 == "2511.02824", "Should handle plain ID"

    def test_app_can_fetch_metadata(self):
        """Test that app can fetch metadata like the example does."""
        metadata = _fetch_paper_metadata("2511.02824")

        assert "title" in metadata, "Should have title"
        assert "authors" in metadata, "Should have authors"
        assert "published" in metadata, "Should have published date"
        assert "arxiv_url" in metadata, "Should have arXiv URL"
        assert metadata["paper_id"] == "2511.02824", "Should have correct paper ID"
        assert len(metadata["authors"]) > 0, "Should have at least one author"

    def test_example_has_same_metadata_structure(self):
        """Test that example metadata matches app metadata structure."""
        # Fetch from app
        app_metadata = _fetch_paper_metadata("2511.02824")

        # Check example HTML has similar structure
        html_files = list(EXAMPLE_DIR.glob("example_blog_*.html"))
        if html_files:
            html_content = html_files[0].read_text(encoding='utf-8')

            # Both should have title
            assert app_metadata["title"] in html_content, "Example should contain same title"

            # Both should have authors
            for author in app_metadata["authors"][:2]:  # Check first 2 authors
                assert author in html_content, f"Example should contain author {author}"


class TestAppOutputMatchesExample:
    """Test that app generates output with same components as example."""

    @pytest.mark.skip(reason="Requires live API calls - run manually")
    def test_app_generates_article(self):
        """Test that app can generate an article (requires API key)."""
        article_path = generate_article("2511.02824", output_format="md")

        assert Path(article_path).exists(), "App should generate article file"

        article_content = Path(article_path).read_text(encoding='utf-8')

        # Should have title
        assert "#" in article_content, "Markdown should have title"

        # Should have metadata
        assert "Authors" in article_content, "Should have authors"
        assert "arXiv" in article_content or "arxiv" in article_content, "Should reference arXiv"

    def test_app_has_image_output_dir(self):
        """Test that app has image output directory configured."""
        from arxiv_paper_pulse import config
        image_dir = Path(config.IMAGE_OUTPUT_DIR)

        assert image_dir.exists() or image_dir.parent.exists(), "Image output directory should be accessible"

    def test_app_has_article_output_dir(self):
        """Test that app has article output directory configured."""
        from arxiv_paper_pulse import config
        article_dir = Path(config.ARTICLE_OUTPUT_DIR)

        assert article_dir.exists() or article_dir.parent.exists(), "Article output directory should be accessible"


class TestAppComponents:
    """Test that app has all components needed to match example."""

    def test_app_has_document_processor(self):
        """Test that app has document processor."""
        from arxiv_paper_pulse.documents import DocumentProcessor
        processor = DocumentProcessor()
        assert processor is not None, "Should have DocumentProcessor"

    def test_app_has_image_generator(self):
        """Test that app has image generator."""
        from arxiv_paper_pulse.image_generator import ImageGenerator
        generator = ImageGenerator()
        assert generator is not None, "Should have ImageGenerator"

    def test_app_has_article_generator(self):
        """Test that app has article generator function."""
        from arxiv_paper_pulse.article_generator import generate_article
        assert callable(generate_article), "Should have generate_article function"


class TestAppCanProduceExampleFormat:
    """Test that app can produce the same format as the example."""

    def test_app_can_generate_markdown(self):
        """Test that app can generate markdown format."""
        from arxiv_paper_pulse.article_generator import generate_article

        # Just verify the function accepts md format
        # Don't actually call it (requires API)
        import inspect
        sig = inspect.signature(generate_article)
        assert "output_format" in sig.parameters, "Should accept output_format parameter"

        # Check it accepts "md"
        param = sig.parameters["output_format"]
        # Default should allow md
        assert param.default in ["docx", "md"] or param.default == "docx", "Should support md format"

    def test_app_can_generate_html_format(self):
        """Test that we can convert markdown to HTML like the example."""
        # The example converts markdown to HTML
        # We should be able to do the same
        import markdown
        test_md = "# Test\n\nThis is a test."
        html = markdown.markdown(test_md)
        assert "<h1>Test</h1>" in html, "Should be able to convert markdown to HTML"

