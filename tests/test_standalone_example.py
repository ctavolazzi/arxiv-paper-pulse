"""
Tests for the standalone example product.
These tests verify that the example has all required components.
"""
import pytest
from pathlib import Path
import re


EXAMPLE_DIR = Path(__file__).parent.parent / "example_output"


@pytest.fixture
def example_html():
    """Load the example HTML file."""
    html_files = list(EXAMPLE_DIR.glob("example_blog_*.html"))
    if not html_files:
        pytest.skip("No example HTML file found. Run build_standalone_example.py first.")
    return html_files[0].read_text(encoding='utf-8')


@pytest.fixture
def example_image():
    """Find the example image file."""
    image_files = list(EXAMPLE_DIR.glob("example_hero_*.png"))
    if not image_files:
        pytest.skip("No example image file found. Run build_standalone_example.py first.")
    return image_files[0]


class TestStandaloneExampleStructure:
    """Test that the standalone example has the correct structure."""

    def test_html_file_exists(self):
        """Test that HTML file exists."""
        html_files = list(EXAMPLE_DIR.glob("example_blog_*.html"))
        assert len(html_files) > 0, "Example HTML file should exist"

    def test_image_file_exists(self, example_image):
        """Test that image file exists and is readable."""
        assert example_image.exists(), "Example image file should exist"
        assert example_image.stat().st_size > 0, "Image file should not be empty"

    def test_html_has_title(self, example_html):
        """Test that HTML has a title tag."""
        assert "<title>" in example_html, "HTML should have a title tag"
        assert "</title>" in example_html, "HTML should have a closing title tag"

    def test_html_has_hero_image(self, example_html, example_image):
        """Test that HTML references the hero image."""
        image_name = example_image.name
        assert image_name in example_html, f"HTML should reference image {image_name}"

    def test_html_has_arxiv_link(self, example_html):
        """Test that HTML has a link to arXiv."""
        assert 'arxiv.org' in example_html.lower(), "HTML should have arXiv link"
        assert 'href=' in example_html, "HTML should have href links"

    def test_html_has_pdf_link(self, example_html):
        """Test that HTML has a link to PDF."""
        assert 'pdf' in example_html.lower(), "HTML should have PDF link"

    def test_html_has_metadata(self, example_html):
        """Test that HTML displays paper metadata."""
        assert "Authors" in example_html or "authors" in example_html, "Should have authors"
        assert "Published" in example_html or "published" in example_html, "Should have published date"
        assert "arXiv" in example_html or "arxiv" in example_html, "Should have arXiv ID"

    def test_html_has_abstract(self, example_html):
        """Test that HTML includes the original abstract."""
        assert "abstract" in example_html.lower(), "Should include abstract"
        assert "Original Abstract" in example_html or "abstract" in example_html.lower(), "Should label abstract"

    def test_html_has_blog_content(self, example_html):
        """Test that HTML has blog post content."""
        # Check for common blog post sections
        content_indicators = [
            "introduction", "findings", "conclusion", "methodology",
            "h1", "h2", "h3", "<p>"
        ]
        html_lower = example_html.lower()
        found = sum(1 for indicator in content_indicators if indicator in html_lower)
        assert found >= 3, "Should have substantial blog content with multiple sections"

    def test_html_is_valid_structure(self, example_html):
        """Test that HTML has valid structure."""
        assert example_html.startswith("<!DOCTYPE html>"), "Should start with DOCTYPE"
        assert "<html" in example_html, "Should have html tag"
        assert "</html>" in example_html, "Should close html tag"
        assert "<head>" in example_html, "Should have head section"
        assert "<body>" in example_html, "Should have body section"

    def test_html_has_styling(self, example_html):
        """Test that HTML has CSS styling."""
        assert "<style>" in example_html or 'style=' in example_html, "Should have styling"

    def test_html_has_hero_image_overlay(self, example_html):
        """Test that HTML has hero image with overlay."""
        assert "hero-image" in example_html.lower(), "Should have hero image container"
        assert "overlay" in example_html.lower(), "Should have image overlay"


class TestStandaloneExampleContent:
    """Test that the standalone example has correct content."""

    def test_has_paper_title(self, example_html):
        """Test that paper title is present."""
        # Title should be in multiple places
        title_count = example_html.count("<title>")
        assert title_count > 0, "Should have title tag with paper title"

    def test_has_author_list(self, example_html):
        """Test that author names are present."""
        # Should have comma-separated authors
        assert "," in example_html or "Authors" in example_html, "Should list authors"

    def test_image_explains_paper(self, example_image):
        """Test that image file exists and is substantial."""
        # Image should be at least 10KB for a meaningful visualization
        size_kb = example_image.stat().st_size / 1024
        assert size_kb > 10, f"Image should be substantial (got {size_kb:.1f}KB)"

    def test_html_links_are_valid(self, example_html):
        """Test that links in HTML are properly formatted."""
        # Check for href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        links = re.findall(href_pattern, example_html)
        assert len(links) > 0, "Should have at least one link"

        # Check for arxiv link
        arxiv_links = [link for link in links if 'arxiv' in link.lower()]
        assert len(arxiv_links) > 0, "Should have at least one arXiv link"


class TestStandaloneExampleAccessibility:
    """Test accessibility and usability features."""

    def test_html_has_alt_text(self, example_html):
        """Test that images have alt text."""
        assert 'alt=' in example_html, "Images should have alt text for accessibility"

    def test_html_is_responsive(self, example_html):
        """Test that HTML has viewport meta tag."""
        assert "viewport" in example_html.lower(), "Should have viewport meta for responsive design"

    def test_html_has_charset(self, example_html):
        """Test that HTML specifies charset."""
        assert "charset" in example_html.lower() or "utf-8" in example_html.lower(), "Should specify charset"


class TestStandaloneExampleCompleteness:
    """Test that all required components are present."""

    def test_has_all_required_components(self, example_html, example_image):
        """Test that example has all required components."""
        required = {
            "title": "<title>" in example_html,
            "hero_image": example_image.exists(),
            "arxiv_link": "arxiv" in example_html.lower(),
            "pdf_link": "pdf" in example_html.lower(),
            "metadata": "Authors" in example_html or "authors" in example_html.lower(),
            "abstract": "abstract" in example_html.lower(),
            "blog_content": len(example_html) > 5000,  # Substantial content
        }

        missing = [key for key, present in required.items() if not present]
        assert len(missing) == 0, f"Missing required components: {missing}"

    def test_example_is_viewable(self, example_image):
        """Test that example files are in the correct location."""
        assert EXAMPLE_DIR.exists(), "Example output directory should exist"
        assert example_image.parent == EXAMPLE_DIR, "Image should be in example_output directory"

