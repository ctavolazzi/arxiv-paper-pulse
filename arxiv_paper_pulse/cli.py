import argparse
import sys
import json
from pathlib import Path
from .core import ArxivSummarizer
from . import config

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and summarize arXiv papers using Google's Gemini API"
    )
    parser.add_argument("--max_results", type=int, default=10, help="Number of papers to fetch (default: 10)")
    parser.add_argument("--pull", action="store_true", help="Force pull new data from arXiv")
    parser.add_argument("--query", type=str, default=None, help="Search query for arXiv (default: 'cat:cs.AI')")

    # Advanced Gemini API features
    parser.add_argument("--pdf", action="store_true", help="Process full PDF papers instead of abstracts only")
    parser.add_argument("--structured", action="store_true", help="Use structured JSON output")
    parser.add_argument("--caching", action="store_true", help="Enable context caching for cost optimization")
    parser.add_argument("--model", type=str, default=None, help=f"Model to use (default: auto-select or {config.DEFAULT_MODEL})")
    parser.add_argument("--url-context", action="store_true", help="Use URL context tool for direct paper access")
    parser.add_argument("--grounding", action="store_true", help="Enable Google Search grounding for real-world context")
    parser.add_argument("--batch", action="store_true", help="Use batch processing API (async, cost-efficient)")
    parser.add_argument("--analyze-multiple", action="store_true", help="Analyze multiple papers together in one request")
    parser.add_argument("--briefing-format", type=str, choices=["executive", "technical", "visual"],
                       default="executive", help="Briefing format style")
    parser.add_argument("--streaming", action="store_true", help="Use streaming responses")

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

    # Initialize summarizer with feature flags
    summarizer = ArxivSummarizer(
        max_results=args.max_results,
        query=args.query,
        model=args.model,
        use_caching=args.caching if args.caching else None
    )
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

    if args.analyze_multiple and len(selected_papers) > 1:
        # Multi-paper analysis
        print("Analyzing multiple papers together...")
        result = summarizer.analyze_multiple_papers(selected_papers, use_structured_output=args.structured)
        print("=" * 80)
        print("Comparative Analysis:")
        print("=" * 80)
        if args.structured and hasattr(result, 'model_dump'):
            print(json.dumps(result.model_dump(), indent=2))
        else:
            print(result)
    elif args.batch:
        # Batch processing
        from .batch_processor import BatchPaperProcessor
        processor = BatchPaperProcessor(model=args.model)
        batch_id = processor.submit_batch(selected_papers)
        print(f"Batch job submitted: {batch_id}")
        print("Use --batch-status <batch_id> to check status later")
    elif args.url_context:
        # URL context processing
        print("Processing papers using URL context...")
        for paper in selected_papers:
            summary = summarizer.gemini_summarize_with_url_context(
                paper.get('url', paper.get('entry_id', '')),
                use_grounding=args.grounding
            )
            paper["summary"] = summary
        summaries = selected_papers
    else:
        # Standard processing
        if args.pdf:
            print("Processing full PDF papers...")
            for paper in selected_papers:
                paper["summary"] = summarizer.gemini_summarize_from_pdf(
                    paper,
                    use_streaming=args.streaming,
                    use_pdf=True
                )
            summaries = selected_papers
        else:
            summaries = summarizer.summarize_selected_papers(selected_papers, force_pull=force_pull)

            # Apply structured output if requested
            if args.structured:
                for paper in summaries:
                    if "summary" in paper and isinstance(paper["summary"], str):
                        analysis = summarizer.gemini_summarize(
                            paper.get("abstract", ""),
                            use_structured_output=True
                        )
                        paper["structured_analysis"] = analysis.model_dump() if hasattr(analysis, 'model_dump') else str(analysis)

    # Display results
    for paper in summaries:
        print("=" * 80)
        print("Title:", paper["title"])
        print("Published:", paper["published"])
        print("URL:", paper["url"])

        if args.structured and "structured_analysis" in paper:
            print("\nStructured Analysis:")
            print(json.dumps(paper["structured_analysis"], indent=2))
        else:
            print("\nSummary:", paper.get("summary", "N/A"))

        print("=" * 80)

    # Generate final briefing if not in batch mode
    if not args.batch:
        summarizer.generate_final_briefing(
            use_structured_output=args.structured,
            format_type=args.briefing_format
        )

if __name__ == "__main__":
    main()
