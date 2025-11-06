#!/usr/bin/env python3
"""
Test script for article generator module.
"""
import sys
from arxiv_paper_pulse.article_generator import generate_article

def test_article_generator():
    """Test article generator with a sample arXiv paper."""
    # Using a recent popular paper as test - Attention Is All You Need
    paper_id = "1706.03762"  # Transformers paper
    # Or use URL format:
    # paper_url = "https://arxiv.org/abs/1706.03762"

    print(f"Testing article generator with paper: {paper_id}")
    print("This will:")
    print("1. Fetch paper metadata")
    print("2. Download and analyze PDF")
    print("3. Generate image prompt")
    print("4. Generate image")
    print("5. Write article text")
    print("6. Create DOCX file")
    print()

    try:
        # Generate DOCX article
        output_path = generate_article(paper_id, output_format="docx")
        print(f"✅ Success! Article generated at: {output_path}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_article_generator())

