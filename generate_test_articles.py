#!/usr/bin/env python3
"""
Generate sample articles for testing and display in results page.
"""
import sys
from pathlib import Path
from datetime import datetime
import json
from arxiv_paper_pulse.article_generator import generate_article


# Sample papers to test with (well-known papers that should exist)
TEST_PAPERS = [
    {
        "id": "1706.03762",
        "name": "Attention Is All You Need (Transformers)"
    },
    {
        "id": "1506.01497",
        "name": "Faster R-CNN"
    },
    {
    "id": "1409.3215",
    "name": "Sequence to Sequence Learning"
    }
]


def generate_test_articles(output_format="md"):
    """Generate articles for all test papers."""
    results = []
    output_dir = Path("arxiv_paper_pulse/data/articles")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(TEST_PAPERS)} test articles...")
    print(f"Output format: {output_format}")
    print()

    for i, paper in enumerate(TEST_PAPERS, 1):
        paper_id = paper["id"]
        paper_name = paper["name"]

        print(f"[{i}/{len(TEST_PAPERS)}] Generating article for {paper_name} ({paper_id})...")

        try:
            start_time = datetime.now()
            article_path = generate_article(paper_id, output_format=output_format)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            # Find associated image
            article_file = Path(article_path)
            image_dir = Path("arxiv_paper_pulse/data/generated_images")
            # Try to find image by paper ID and timestamp
            images = list(image_dir.glob(f"article_image_{paper_id}_*.png"))
            if not images:
                # Try alternative pattern (without article_image prefix)
                images = list(image_dir.glob(f"*{paper_id}*.png"))
            image_path = str(images[-1]) if images else None

            result = {
                "paper_id": paper_id,
                "paper_name": paper_name,
                "status": "success",
                "article_path": str(article_path),
                "image_path": image_path,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat(),
                "error": None
            }

            print(f"  ✅ Success ({duration:.1f}s)")
            if image_path:
                print(f"     Image: {Path(image_path).name}")
            print()

        except Exception as e:
            result = {
                "paper_id": paper_id,
                "paper_name": paper_name,
                "status": "error",
                "article_path": None,
                "image_path": None,
                "duration_seconds": None,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            print(f"  ❌ Error: {e}")
            print()

        results.append(result)

    return results


def create_results_page(results, output_file="test_results.html"):
    """Create HTML results page showing all articles and images."""
    # Use double braces to escape format placeholders in CSS
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Article Generator Test Results</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: #666;
            font-size: 1.1em;
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }

        .stat {
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 8px;
            flex: 1;
            min-width: 150px;
        }

        .stat-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }

        .stat-value {
            color: #333;
            font-size: 1.8em;
            font-weight: bold;
        }

        .stat-value.success {
            color: #28a745;
        }

        .stat-value.error {
            color: #dc3545;
        }

        .articles {
            display: grid;
            gap: 30px;
        }

        .article-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .article-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.15);
        }

        .article-card.error {
            border-left: 5px solid #dc3545;
        }

        .article-card.success {
            border-left: 5px solid #28a745;
        }

        .article-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }

        .article-title {
            flex: 1;
        }

        .article-title h2 {
            color: #333;
            font-size: 1.8em;
            margin-bottom: 5px;
        }

        .article-title .paper-id {
            color: #666;
            font-size: 0.9em;
            font-family: 'Courier New', monospace;
        }

        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            text-transform: uppercase;
        }

        .status-badge.success {
            background: #d4edda;
            color: #155724;
        }

        .status-badge.error {
            background: #f8d7da;
            color: #721c24;
        }

        .article-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .article-content {
                grid-template-columns: 1fr;
            }
        }

        .article-details {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .detail-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }

        .detail-label {
            color: #666;
            font-weight: 500;
        }

        .detail-value {
            color: #333;
            font-family: 'Courier New', monospace;
            text-align: right;
        }

        .article-image {
            text-align: center;
        }

        .article-image img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .article-image .no-image {
            background: #f8f9fa;
            padding: 60px 20px;
            border-radius: 8px;
            color: #666;
            font-style: italic;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .article-link {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: background 0.3s ease;
        }

        .article-link:hover {
            background: #5568d3;
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Article Generator Test Results</h1>
            <div class="subtitle">Generated articles from arXiv papers with AI-generated images</div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Total Articles</div>
                    <div class="stat-value">{total}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Successful</div>
                    <div class="stat-value success">{success}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Errors</div>
                    <div class="stat-value error">{errors}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Avg Duration</div>
                    <div class="stat-value">{avg_duration}</div>
                </div>
            </div>
        </div>

        <div class="articles">
            {articles_html}
        </div>

        <div class="footer">
            <p>Generated on {timestamp}</p>
            <p>Article Generator Module - arxiv-paper-pulse</p>
        </div>
    </div>
</body>
</html>"""

    # Calculate stats
    total = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = total - success_count
    durations = [r["duration_seconds"] for r in results if r["duration_seconds"]]
    avg_duration = f"{sum(durations)/len(durations):.1f}s" if durations else "N/A"

    # Generate articles HTML
    articles_html = ""
    for result in results:
        if result["status"] == "success":
            card_class = "success"
            status_badge = '<span class="status-badge success">✓ Success</span>'

            # Format duration
            duration = f"{result['duration_seconds']:.1f}s" if result['duration_seconds'] else "N/A"

            # Image HTML
            if result["image_path"] and Path(result["image_path"]).exists():
                img_path = Path(result["image_path"])
                # Use relative path for images
                try:
                    rel_img_path = img_path.relative_to(Path.cwd())
                except ValueError:
                    # If not in same directory tree, use absolute path
                    rel_img_path = img_path
                image_html = f'<img src="file://{img_path.absolute()}" alt="Generated image for {result["paper_name"]}">'
            else:
                image_html = '<div class="no-image">No image generated</div>'

            # Article link
            article_link = ""
            if result["article_path"] and Path(result["article_path"]).exists():
                article_file = Path(result["article_path"])
                try:
                    rel_article_path = article_file.relative_to(Path.cwd())
                    article_link = f'<a href="file://{article_file.absolute()}" class="article-link" target="_blank">View Article</a>'
                except ValueError:
                    article_link = f'<a href="file://{article_file.absolute()}" class="article-link" target="_blank">View Article</a>'

            articles_html += f"""
            <div class="article-card {card_class}">
                <div class="article-header">
                    <div class="article-title">
                        <h2>{result["paper_name"]}</h2>
                        <div class="paper-id">arXiv:{result["paper_id"]}</div>
                    </div>
                    {status_badge}
                </div>

                <div class="article-content">
                    <div class="article-details">
                        <div class="detail-item">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value">Success</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Duration:</span>
                            <span class="detail-value">{duration}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Article:</span>
                            <span class="detail-value">{Path(result["article_path"]).name if result["article_path"] else "N/A"}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Image:</span>
                            <span class="detail-value">{Path(result["image_path"]).name if result["image_path"] else "N/A"}</span>
                        </div>
                        {article_link}
                    </div>
                    <div class="article-image">
                        {image_html}
                    </div>
                </div>
            </div>
            """
        else:
            card_class = "error"
            status_badge = '<span class="status-badge error">✗ Error</span>'

            articles_html += f"""
            <div class="article-card {card_class}">
                <div class="article-header">
                    <div class="article-title">
                        <h2>{result["paper_name"]}</h2>
                        <div class="paper-id">arXiv:{result["paper_id"]}</div>
                    </div>
                    {status_badge}
                </div>

                <div class="error-message">
                    <strong>Error:</strong> {result["error"]}
                </div>
            </div>
            """

    # Format final HTML - replace placeholders manually to avoid CSS brace issues
    final_html = html_content.replace("{total}", str(total))
    final_html = final_html.replace("{success}", str(success_count))
    final_html = final_html.replace("{errors}", str(error_count))
    final_html = final_html.replace("{avg_duration}", avg_duration)
    final_html = final_html.replace("{articles_html}", articles_html)
    final_html = final_html.replace("{timestamp}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Write to file
    output_path = Path(output_file)
    output_path.write_text(final_html, encoding='utf-8')

    return str(output_path)


def main():
    """Main function to generate articles and create results page."""
    print("=" * 60)
    print("Article Generator Test Suite")
    print("=" * 60)
    print()

    # Generate articles
    results = generate_test_articles(output_format="md")

    # Create results page
    print("Creating results page...")
    results_path = create_results_page(results)
    print(f"✅ Results page created: {results_path}")
    print()

    # Save results JSON
    json_path = Path("test_results.json")
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✅ Test results JSON saved: {json_path}")
    print()

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count

    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print()
    print(f"Results page: {results_path}")
    print()

    return str(results_path)


if __name__ == "__main__":
    try:
        results_path = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

