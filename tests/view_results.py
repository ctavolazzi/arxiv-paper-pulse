#!/usr/bin/env python3
"""
View test results in browser with images.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime
import http.server
import socketserver
import webbrowser
import threading
import time
import sys


def run_tests():
    """Skip tests - just show existing artifacts."""
    print("=" * 80)
    print("🧪 Article Generator Test Viewer")
    print("=" * 80)
    print()
    print("ℹ️  Note: Skipping test execution to show results quickly.")
    print("   Live API tests make real Gemini API calls (1-2 minutes per test).")
    print("   To run tests manually: pytest tests/test_article_generator.py -v -m live_api")
    print()

    # Return empty test results
    return type('Result', (), {'returncode': 0, 'stdout': 'Tests skipped - showing existing artifacts', 'stderr': ''})()


def collect_artifacts():
    """Collect generated articles and images."""
    artifacts = {
        'articles': [],
        'images': [],
        'timestamp': datetime.now().isoformat()
    }

    # Collect articles
    article_dir = Path("arxiv_paper_pulse/data/articles")
    if article_dir.exists():
        for article_file in sorted(article_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            artifacts['articles'].append({
                'name': article_file.name,
                'path': str(article_file),
                'size': article_file.stat().st_size,
                'modified': datetime.fromtimestamp(article_file.stat().st_mtime).isoformat()
            })
        for article_file in sorted(article_dir.glob("*.docx"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            artifacts['articles'].append({
                'name': article_file.name,
                'path': str(article_file),
                'size': article_file.stat().st_size,
                'modified': datetime.fromtimestamp(article_file.stat().st_mtime).isoformat()
            })

    # Collect images
    image_dir = Path("arxiv_paper_pulse/data/generated_images")
    if image_dir.exists():
        for image_file in sorted(image_dir.glob("article_image_*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            artifacts['images'].append({
                'name': image_file.name,
                'path': str(image_file),
                'size': image_file.stat().st_size,
                'modified': datetime.fromtimestamp(image_file.stat().st_mtime).isoformat()
            })

    return artifacts


def parse_test_output(output):
    """Parse pytest output to extract test results."""
    results = {
        'summary': {'passed': 0, 'failed': 0, 'skipped': 0},
        'tests': []
    }

    lines = output.split('\n')
    for line in lines:
        if 'PASSED' in line:
            results['summary']['passed'] += 1
            results['tests'].append({
                'nodeid': line.strip(),
                'outcome': 'passed'
            })
        elif 'FAILED' in line:
            results['summary']['failed'] += 1
            results['tests'].append({
                'nodeid': line.strip(),
                'outcome': 'failed'
            })
        elif 'SKIPPED' in line:
            results['summary']['skipped'] += 1
            results['tests'].append({
                'nodeid': line.strip(),
                'outcome': 'skipped'
            })

    return results


def generate_html(results_data, artifacts, test_output=""):
    """Generate HTML results page."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Article Generator Test Results</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .test-results {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .test-item {{
            padding: 15px;
            margin: 10px 0;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .test-item.passed {{
            border-left-color: #28a745;
        }}
        .test-item.failed {{
            border-left-color: #dc3545;
        }}
        .test-item.skipped {{
            border-left-color: #ffc107;
        }}
        .test-name {{
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        .test-status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9em;
            font-weight: bold;
            margin-right: 10px;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .gallery-item {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .gallery-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}
        .gallery-item img {{
            width: 100%;
            height: 250px;
            object-fit: cover;
        }}
        .gallery-item-info {{
            padding: 15px;
        }}
        .gallery-item-info h3 {{
            font-size: 1em;
            margin-bottom: 8px;
            color: #333;
            word-break: break-word;
        }}
        .gallery-item-info p {{
            font-size: 0.85em;
            color: #666;
            margin: 4px 0;
        }}
        .article-list {{
            display: grid;
            gap: 15px;
        }}
        .article-item {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .article-item h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .article-item p {{
            color: #666;
            margin: 5px 0;
        }}
        .article-item a {{
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }}
        .article-item a:hover {{
            text-decoration: underline;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card h3 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .stat-card p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Article Generator Test Results</h1>
            <p>Generated: {artifacts['timestamp']}</p>
        </div>
        <div class="content">
            <div class="section">
                <h2>📊 Test Statistics</h2>
                <div class="stats">
                    <div class="stat-card">
                        <h3>{results_data.get('summary', {}).get('passed', 0)}</h3>
                        <p>Passed</p>
                    </div>
                    <div class="stat-card">
                        <h3>{results_data.get('summary', {}).get('failed', 0)}</h3>
                        <p>Failed</p>
                    </div>
                    <div class="stat-card">
                        <h3>{results_data.get('summary', {}).get('skipped', 0)}</h3>
                        <p>Skipped</p>
                    </div>
                    <div class="stat-card">
                        <h3>{len(artifacts['articles'])}</h3>
                        <p>Articles</p>
                    </div>
                    <div class="stat-card">
                        <h3>{len(artifacts['images'])}</h3>
                        <p>Images</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>✅ Test Results</h2>
                <div class="test-results">
"""

    # Add test results
    if 'tests' in results_data:
        for test in results_data['tests']:
            status = test.get('outcome', 'unknown')
            status_class = status
            status_badge = status.upper()

            html += f"""
                    <div class="test-item {status_class}">
                        <div class="test-name">
                            <span class="test-status status-{status_class}">{status_badge}</span>
                            {test.get('nodeid', 'Unknown test')}
                        </div>
                        {f'<p style="color: #666; margin-top: 8px;">{test.get("call", {}).get("longrepr", "")}</p>' if status == 'failed' else ''}
                    </div>
"""

    html += """
                </div>
            </div>
"""

    # Add images gallery
    if artifacts['images']:
        html += """
            <div class="section">
                <h2>🖼️ Generated Images</h2>
                <div class="gallery">
"""
        for img in artifacts['images']:
            # Convert to relative path for web server
            img_path = img['path'].replace(str(Path.cwd()) + '/', '')
            img_size_kb = img['size'] / 1024
            html += f"""
                    <div class="gallery-item">
                        <img src="{img_path}" alt="{img['name']}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'300\' height=\'250\'%3E%3Ctext x=\'50%25\' y=\'50%25\' text-anchor=\'middle\' dy=\'.3em\'%3EImage not found%3C/text%3E%3C/svg%3E'">
                        <div class="gallery-item-info">
                            <h3>{img['name']}</h3>
                            <p>Size: {img_size_kb:.1f} KB</p>
                            <p>Modified: {img['modified'][:19]}</p>
                        </div>
                    </div>
"""
        html += """
                </div>
            </div>
"""

    # Add articles list
    if artifacts['articles']:
        html += """
            <div class="section">
                <h2>📄 Generated Articles</h2>
                <div class="article-list">
"""
        for article in artifacts['articles']:
            article_path = article['path'].replace(str(Path.cwd()) + '/', '')
            article_size_kb = article['size'] / 1024
            html += f"""
                    <div class="article-item">
                        <h3>{article['name']}</h3>
                        <p>Size: {article_size_kb:.1f} KB</p>
                        <p>Modified: {article['modified'][:19]}</p>
                        <p><a href="{article_path}" target="_blank">View Article →</a></p>
                    </div>
"""
        html += """
                </div>
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""
    return html


def start_server(port=8000):
    """Start HTTP server."""
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    return httpd


def main():
    """Main function."""
    print("=" * 80)
    print("🚀 Article Generator Test Results Viewer")
    print("=" * 80)
    print()

    # Run tests
    test_result = run_tests()

    print()
    print("=" * 80)
    print("📊 Collecting artifacts...")
    print("=" * 80)
    print()

    # Collect artifacts
    artifacts = collect_artifacts()

    print(f"📄 Found {len(artifacts['articles'])} articles")
    for article in artifacts['articles'][:5]:
        print(f"   - {article['name']} ({article['size']/1024:.1f} KB)")

    print()
    print(f"🖼️  Found {len(artifacts['images'])} images")
    for img in artifacts['images'][:5]:
        print(f"   - {img['name']} ({img['size']/1024:.1f} KB)")

    print()
    print("=" * 80)
    print("🎨 Generating results page...")
    print("=" * 80)
    print()

    # Parse test results
    results_data = parse_test_output(test_result.stdout + test_result.stderr)

    # Generate HTML
    html = generate_html(results_data, artifacts, test_result.stdout)

    # Save HTML
    html_file = Path("test_results.html")
    html_file.write_text(html)

    print(f"✅ Results page saved to: {html_file}")
    print()
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"   Tests Passed: {results_data['summary']['passed']}")
    print(f"   Tests Failed: {results_data['summary']['failed']}")
    print(f"   Tests Skipped: {results_data['summary']['skipped']}")
    print(f"   Articles Generated: {len(artifacts['articles'])}")
    print(f"   Images Generated: {len(artifacts['images'])}")
    print()

    # Start server
    print("=" * 80)
    print("🌐 Starting web server on http://localhost:8000")
    print("=" * 80)
    print()

    httpd = start_server(8000)

    # Open browser
    def open_browser():
        time.sleep(2)
        print("🌐 Opening browser...")
        webbrowser.open("http://localhost:8000/test_results.html")
        print("✅ Browser opened!")
        print()
        print("=" * 80)
        print("📝 Server running at http://localhost:8000")
        print("   View results at: http://localhost:8000/test_results.html")
        print("   Press Ctrl+C to stop the server")
        print("=" * 80)
        print()

    threading.Thread(target=open_browser, daemon=True).start()

    # Serve
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("🛑 Server stopped")
        print("=" * 80)
        httpd.shutdown()


if __name__ == "__main__":
    main()

