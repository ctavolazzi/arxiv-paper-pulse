import arxiv
import subprocess
import json
from pathlib import Path
from datetime import datetime
from . import config
from .utils import get_unique_id, get_installed_ollama_models  # Externalized functions

class ArxivSummarizer:
    """
    Fetches and summarizes arXiv papers using a local Ollama model.
    Implements daily caching for summaries and briefing files with date and time.
    Raw data is always pulled fresh from arXiv.
    """

    def __init__(self, max_results=10, model=config.DEFAULT_MODEL, query="cat:cs.AI"):
        self.max_results = max_results
        self.model = model
        self.query = query
        self._ensure_directories()
        self._set_default_model()
        self.initialize_briefing_file()

    def _ensure_directories(self):
        Path(config.RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.SUMMARY_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.BRIEFING_DIR).mkdir(parents=True, exist_ok=True)

    def _set_default_model(self):
        installed = get_installed_ollama_models()  # Using the externalized function
        if not installed:
            print("No Ollama models detected. Please install one manually.")
            return
        if self.model not in installed:
            print(f"Configured model '{self.model}' not found. Using '{installed[0]}' as default.")
            self.model = installed[0]
        else:
            print(f"Using default model: {self.model}")

    def pull_model(self):
        try:
            print(f"Pulling Ollama model: {self.model}...")
            result = subprocess.run(["ollama", "pull", self.model],
                                    capture_output=True, text=True, check=True)
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error pulling model {self.model}: {e.stderr.strip()}")

    def _today_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _create_file_path(self, directory: Path, suffix: str) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return directory / f"{timestamp}_{suffix}.json"

    def _latest_file(self, directory: Path, suffix: str) -> Path:
        today_prefix = self._today_str()
        files = list(directory.glob(f"{today_prefix}_*{suffix}.json"))
        return sorted(files)[-1] if files else None

    def initialize_briefing_file(self):
        """
        Creates a new Markdown briefing file with a date and timestamp in its filename.
        Sets up the document with proper formatting and headers.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.briefing_file = Path(config.BRIEFING_DIR) / f"{timestamp}_briefing.md"

        search_query = self.query.replace(":", "_").replace(" ", "_")
        current_date = datetime.now().strftime("%Y-%m-%d")

        with open(self.briefing_file, "w") as f:
            f.write(f"# ArXiv Research Briefing: {search_query}\n\n")
            f.write(f"**Date:** {current_date}\n\n")
            f.write(f"**Search Query:** `{self.query}`\n\n")
            f.write("## Articles\n\n")

        print(f"Initialized briefing report at: {self.briefing_file}")

    def update_briefing_report(self, paper):
        """
        Appends a well-formatted section for a single paper to the briefing file,
        ensuring proper markdown formatting with article details and summary.
        """
        import re

        def remove_think_tags(text):
            return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        # Make a proper URL if it's just an ID
        if paper['url'].startswith("http"):
            url = paper['url']
        else:
            # Convert arXiv ID to URL
            paper_id = paper['url'].split('/')[-1]
            url = f"https://arxiv.org/abs/{paper_id}"

        # Create a well-formatted markdown section for the paper
        with open(self.briefing_file, "a") as f:
            # Article header with title and link
            f.write(f"### [{paper['title']}]({url})\n\n")

            # Publication date
            f.write(f"**Published:** {paper['published']}\n\n")

            # Clean and format the summary
            summary = remove_think_tags(paper['summary'])

            # Extract or create bullet points for key insights
            f.write("#### Key Insights:\n\n")

            # Check if the summary already has numbered points
            if re.search(r"\d+\.\s+", summary):
                # If it has numbered sections, try to extract them
                sections = re.split(r"(\d+\.\s+[^\n]+)", summary)
                sections = [s for s in sections if s.strip()]

                for section in sections:
                    if re.match(r"\d+\.\s+", section):
                        # Convert numbered points to bullet points
                        point = re.sub(r"^\d+\.\s+", "- **", section.strip()) + "**\n"
                        f.write(f"{point}\n")
                    else:
                        # Add the content as regular text with indentation
                        paragraphs = section.strip().split("\n")
                        for p in paragraphs:
                            if p.strip():
                                f.write(f"  {p}\n\n")
            else:
                # If no numbered sections, just add the summary as is
                f.write(f"{summary}\n\n")

            # Add a separator
            f.write("---\n\n")

        print(f"Updated briefing report with paper: {paper['title']}")

    def generate_final_briefing(self):
        """
        Reads the accumulated article summaries from the briefing file, passes them to the local LLM
        to generate a final comprehensive briefing that focuses on broader implications and insights.
        The final synthesis is then appended to the same file with proper formatting.
        """
        import re
        print("Creating final comprehensive briefing...")

        with open(self.briefing_file, "r") as f:
            content = f.read()

        # Use the new synthesis prompt from config
        synthesis_prompt = config.SYNTHESIS_PROMPT.format(content)
        final_synthesis = self.ollama_summarize(synthesis_prompt)
        final_synthesis = re.sub(r"<think>.*?</think>", "", final_synthesis, flags=re.DOTALL)

        with open(self.briefing_file, "a") as f:
            f.write("\n## Executive Summary\n\n")
            f.write(final_synthesis)
            f.write("\n\n---\n\n")
            f.write("*This briefing was automatically generated using ArXiv Paper Pulse and a local Ollama model.*\n")

        print(f"Final comprehensive briefing appended to: {self.briefing_file}")
        print(f"Open it with your favorite markdown viewer or text editor at: {self.briefing_file}")

    def fetch_raw_data(self, force_pull=False):
        """
        Always fetches fresh data from arXiv, saves it (including the search query in lowercase), and returns it.
        """
        raw_dir = Path(config.RAW_DATA_DIR)
        print("Fetching new data from arXiv...")
        search = arxiv.Search(query=self.query, max_results=self.max_results,
                              sort_by=arxiv.SortCriterion.SubmittedDate)
        client = arxiv.Client()
        papers = list(client.results(search))

        data = []
        for paper in papers:
            paper_data = {
                "entry_id": paper.entry_id,
                "title": paper.title,
                "published": str(paper.published),
                "url": paper.entry_id,  # Backup using the entry_id as URL
                "abstract": paper.summary,
                "query": self.query.lower()  # Store the search term in lowercase
            }
            paper_data["id"] = get_unique_id(paper_data)
            data.append(paper_data)

        file_path = self._create_file_path(raw_dir, "raw")
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Saved raw data to {file_path}")
        return data

    def summarize_papers(self, force_pull=False):
        """
        If today's summaries exist and force_pull is False, load and return them.
        Otherwise, generate summaries from raw data, updating both the JSON summary file and
        the persistent Markdown briefing file as each paper is processed.
        """
        summary_dir = Path(config.SUMMARY_DIR)
        summary_file_path = self._create_file_path(summary_dir, "summary")
        summaries = []
        if not force_pull:
            existing = self._latest_file(summary_dir, "summary")
            if existing:
                print(f"Loading summaries from {existing}")
                with open(existing, "r") as f:
                    return json.load(f)
        raw_data = self.fetch_raw_data(force_pull=force_pull)
        for i, paper in enumerate(raw_data, start=1):
            print(f"Summarizing paper {i}/{len(raw_data)}: {paper['title']}")
            paper["summary"] = self.ollama_summarize(paper["abstract"])
            summaries.append(paper)
            with open(summary_file_path, "w") as f:
                json.dump(summaries, f, indent=4)
            self.update_briefing_report(paper)
        print(f"Saved summaries to {summary_file_path}")
        self.generate_final_briefing()
        return summaries

    def summarize_selected_papers(self, selected_papers, force_pull=False):
        """
        Summarize only the selected papers from the raw data.
        Updates both the JSON summary file and the briefing file as each paper is processed.
        """
        summary_dir = Path(config.SUMMARY_DIR)
        summary_file_path = self._create_file_path(summary_dir, "summary")
        summaries = []

        # Initialize a new briefing file
        self.initialize_briefing_file()

        for i, paper in enumerate(selected_papers, start=1):
            print(f"Summarizing paper {i}/{len(selected_papers)}: {paper['title']}")
            # Only summarize if not already present in paper dict
            if "summary" not in paper:
                paper["summary"] = self.ollama_summarize(paper["abstract"])
            summaries.append(paper)
            with open(summary_file_path, "w") as f:
                json.dump(summaries, f, indent=4)
            self.update_briefing_report(paper)

        print(f"Saved summaries to {summary_file_path}")
        self.generate_final_briefing()
        return summaries

    def ollama_summarize(self, text):
        prompt = config.SUMMARY_PROMPT.format(text)
        try:
            result = subprocess.run(["ollama", "run", self.model, prompt],
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr.strip()}"
