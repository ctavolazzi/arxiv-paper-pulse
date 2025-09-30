import argparse
from .core import ArxivSummarizer
from . import config
from .utils import get_total_available  # Using the externalized function
import feedparser
import urllib.parse

def crawl():
    parser = argparse.ArgumentParser(
        description="Initiate a crawl of arXiv articles and summarize them using a local model"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="cat:cs.AI",
        help="Search query for arXiv (default: 'cat:cs.AI')"
    )
    parser.add_argument(
        "--default",
        type=int,
        default=10,
        help="Default number of articles to crawl (default: 10)"
    )
    args = parser.parse_args()

    total_available = get_total_available(args.query)
    print(f"Total available articles for query '{args.query}': {total_available}")

    all_choice = input("Do you want to crawl all available articles? (y/n): ").strip().lower()
    if all_choice == "y" and total_available is not None:
        num_articles = total_available
    else:
        user_input = input(f"Enter number of articles to crawl (press Enter for default {args.default}): ").strip()
        if user_input:
            try:
                num_articles = int(user_input)
            except ValueError:
                print("Invalid input. Using default value.")
                num_articles = args.default
        else:
            num_articles = args.default

    print(f"Starting crawl for {num_articles} articles...")
    summarizer = ArxivSummarizer(max_results=num_articles, query=args.query)
    summaries = summarizer.summarize_papers(force_pull=True)
    print(f"Crawl complete. Summarized {len(summaries)} articles.\n")
    for paper in summaries:
        print("=" * 80)
        print("Title:", paper["title"])
        print("Published:", paper["published"])
        print("URL:", paper["url"])
        print("\nSummary:", paper["summary"])
        print("=" * 80)

if __name__ == "__main__":
    crawl()
