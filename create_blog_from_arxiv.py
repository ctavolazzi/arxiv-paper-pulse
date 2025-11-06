#!/usr/bin/env python3
"""
End-to-end program that takes an ArXiv article URL and produces a complete blog post.

This is the main program that users will run to generate blog posts from arXiv papers.
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import webbrowser
import http.server
import socketserver
import threading
import time

from build_standalone_example import (
    fetch_arxiv_paper,
    analyze_paper,
    generate_image_prompt,
    generate_featured_image,
    generate_blog_post,
    build_html_page
)


def extract_paper_id(url_or_id: str) -> str:
    """Extract paper ID from URL or return as-is if already an ID."""
    if 'arxiv.org' in url_or_id:
        paper_id = url_or_id.split('/')[-1].replace('.pdf', '').replace('.abs', '')
    else:
        paper_id = url_or_id
    return paper_id


def main():
    """Main function to create blog post from arXiv URL."""
    parser = argparse.ArgumentParser(
        description="Generate a blog post from an arXiv paper URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_blog_from_arxiv.py https://arxiv.org/abs/2511.02824
  python create_blog_from_arxiv.py 2511.02824
  python create_blog_from_arxiv.py https://arxiv.org/abs/2511.02824 --open
        """
    )

    parser.add_argument(
        "url_or_id",
        help="arXiv paper URL (e.g., https://arxiv.org/abs/2511.02824) or paper ID (e.g., 2511.02824)"
    )

    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated blog post in browser automatically"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8004,
        help="Port for local web server (default: 8004)"
    )

    args = parser.parse_args()

    # Extract paper ID
    paper_id = extract_paper_id(args.url_or_id)
    paper_url = f"https://arxiv.org/abs/{paper_id}"

    print("=" * 80)
    print("ARXIV PAPER BLOG GENERATOR")
    print("=" * 80)
    print()
    print(f"Paper: {paper_url}")
    print()

    try:
        # Step 1: Fetch paper
        metadata = fetch_arxiv_paper(paper_id)
        print()

        # Step 2: Analyze paper
        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
        analysis_text = analyze_paper(pdf_url)
        print()

        # Step 3: Generate image prompt
        image_prompt = generate_image_prompt(analysis_text, metadata)
        print()

        # Step 4: Generate featured image
        image_path = generate_featured_image(image_prompt, paper_id)
        print()

        # Step 5: Generate blog post
        blog_content = generate_blog_post(metadata, analysis_text)
        print()

        # Step 6: Build HTML page
        html_file = build_html_page(metadata, blog_content, image_path, analysis_text)
        print()

        print("=" * 80)
        print("✅ BLOG POST GENERATED SUCCESSFULLY")
        print("=" * 80)
        print(f"📄 HTML File: {html_file}")
        print(f"🖼️  Image: {Path(image_path).name}")
        print()

        # Optionally open in browser
        if args.open:
            print(f"🌐 Starting web server on port {args.port}...")
            html_path = Path(html_file)
            output_dir = html_path.parent

            # Change to output directory for server
            os.chdir(output_dir)

            # Start server
            Handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("", args.port), Handler)

            def open_browser():
                time.sleep(1)
                url = f'http://localhost:{args.port}/{html_path.name}'
                print(f"🌐 Opening: {url}")
                webbrowser.open(url)

            threading.Thread(target=open_browser, daemon=True).start()

            print(f"🌐 Server running at http://localhost:{args.port}")
            print(f"   View article: http://localhost:{args.port}/{html_path.name}")
            print("   Press Ctrl+C to stop")
            print()

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print('\n🛑 Server stopped')
                httpd.shutdown()
        else:
            file_path = Path(html_file).absolute()
            print(f"📂 Open this file in your browser:")
            print(f"   file://{file_path}")
            print()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())

