#!/usr/bin/env python3
"""
Run article generator tests and generate results page with browser preview.
"""
import sys
import subprocess
import webbrowser
from pathlib import Path
from time import sleep


def run_pytest():
    """Run pytest tests for article generator."""
    print("=" * 60)
    print("Running pytest tests...")
    print("=" * 60)
    print()

    result = subprocess.run(
        ["pytest", "tests/test_article_generator.py", "-v", "--tb=short"],
        capture_output=False
    )

    print()
    return result.returncode == 0


def generate_results_page():
    """Generate test articles and create results page."""
    print("=" * 60)
    print("Generating test articles...")
    print("=" * 60)
    print()

    result = subprocess.run(
        [sys.executable, "generate_test_articles.py"],
        capture_output=False
    )

    return result.returncode == 0


def open_results_page():
    """Open results page in browser."""
    results_path = Path("test_results.html").resolve()

    if not results_path.exists():
        print(f"❌ Results page not found: {results_path}")
        return False

    print("=" * 60)
    print("Opening results page in browser...")
    print("=" * 60)
    print()

    # Open in browser
    url = f"file://{results_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)

    print("✅ Browser opened!")
    print()
    print("Results page should now be visible in your browser.")
    print()

    return True


def main():
    """Main function to run tests and generate results."""
    print("=" * 60)
    print("Article Generator Test Suite Runner")
    print("=" * 60)
    print()

    # Run pytest tests (unit tests with mocks)
    print("Step 1: Running unit tests (with mocks)...")
    print()
    test_success = run_pytest()
    print()

    if not test_success:
        print("⚠️  Some unit tests failed, but continuing...")
        print()

    # Generate articles and create results page
    print("Step 2: Generating test articles (requires API key)...")
    print()
    results_success = generate_results_page()
    print()

    if not results_success:
        print("❌ Failed to generate articles. Check API key and try again.")
        sys.exit(1)

    # Open results page
    print("Step 3: Opening results page in browser...")
    print()
    open_results_page()

    print("=" * 60)
    print("✅ All done!")
    print("=" * 60)
    print()
    print("Summary:")
    print("- Unit tests: Run with pytest")
    print("- Integration tests: Articles generated")
    print("- Results page: test_results.html")
    print()


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

