import argparse
import sys
import json
from pathlib import Path
from .core import ArxivSummarizer
from . import config

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and summarize arXiv papers using a local Ollama model"
    )
    parser.add_argument("--max_results", type=int, default=10, help="Number of papers to fetch (default: 10)")
    parser.add_argument("--pull", action="store_true", help="Force pull new data from arXiv")
    parser.add_argument("--query", type=str, default=None, help="Search query for arXiv (default: 'cat:cs.AI')")
    args = parser.parse_args()

    # Prompt for a search query if not provided via command-line.
    if args.query is None:
        user_query = input("Enter a search query (default 'cat:cs.AI'): ").strip()
        args.query = user_query if user_query else "cat:cs.AI"

    # If --max_results wasn't explicitly provided, prompt the user for the number of articles to pull.
    if "--max_results" not in sys.argv:
        user_max = input("Enter number of articles to pull (default 10): ").strip()
        try:
            args.max_results = int(user_max) if user_max else args.max_results
        except ValueError:
            print("Invalid input, using default 10")
            args.max_results = 10

    summarizer = ArxivSummarizer(max_results=args.max_results, query=args.query)
    force_pull = args.pull

    # Retrieve the latest cached raw file.
    cached_raw = summarizer._latest_file(Path(config.RAW_DATA_DIR), "raw")
    if not force_pull and cached_raw:
        with open(cached_raw, "r") as f:
            data = json.load(f)
        # Compare the cached query to the new query (both in lowercase).
        if data and isinstance(data, list) and data[0].get("query", "").lower() == args.query.lower():
            # Same query: ask the user if they want to refresh.
            answer = input("Cached raw data exists for the same query. Do you want to pull new data from arXiv? (y/n): ").strip().lower()
            if answer == "y":
                force_pull = True
        else:
            # Different query: automatically force a new pull.
            print("Cached raw data does not match the new query. Automatically pulling new data.")
            force_pull = True

    # Fetch raw data and display article titles to the user
    raw_data = summarizer.fetch_raw_data(force_pull=force_pull)
    print("\nArticles pulled:")
    for i, paper in enumerate(raw_data, start=1):
        print(f"{i}. {paper['title']}")

    # Allow user to select specific articles
    selected_indices = []
    selection = input("\nEnter article numbers to summarize (comma-separated, or 'all' for all): ").strip().lower()

    if selection == "all":
        selected_indices = list(range(len(raw_data)))
    else:
        try:
            # Parse the comma-separated list of article numbers
            selections = [int(x.strip()) for x in selection.split(',') if x.strip()]
            # Convert to 0-based indices and validate
            selected_indices = [x-1 for x in selections if 1 <= x <= len(raw_data)]
            if not selected_indices:
                print("No valid selections. Using all articles.")
                selected_indices = list(range(len(raw_data)))
        except ValueError:
            print("Invalid selection format. Using all articles.")
            selected_indices = list(range(len(raw_data)))

    # Filter raw_data based on selection
    selected_papers = [raw_data[i] for i in selected_indices]

    # Proceed with summarization only for selected papers
    print(f"\nProceeding with summarization of {len(selected_papers)} articles...")
    summaries = summarizer.summarize_selected_papers(selected_papers, force_pull=force_pull)

    for paper in summaries:
        print("=" * 80)
        print("Title:", paper["title"])
        print("Published:", paper["published"])
        print("URL:", paper["url"])
        print("\nSummary:", paper["summary"])
        print("=" * 80)

if __name__ == "__main__":
    main()
