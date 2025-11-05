import arxiv
import json
import io
import httpx
import time
from pathlib import Path
from datetime import datetime
from . import config
from .utils import get_unique_id
from .models import PaperAnalysis, Methodology, Results, ComparativeAnalysis
from google import genai
from google.genai import types

class ArxivSummarizer:
    """
    Fetches and summarizes arXiv papers using Google's Gemini API.
    Implements daily caching for summaries and briefing files with date and time.
    Raw data is always pulled fresh from arXiv.
    """

    def __init__(self, max_results=10, model=None, query="cat:cs.AI", use_caching=None):
        self.max_results = max_results
        # Auto-select model if not specified and auto-selection enabled
        if model is None:
            if config.AUTO_MODEL_SELECTION:
                self.model = self._select_optimal_model(query, max_results)
            else:
                self.model = config.DEFAULT_MODEL
        else:
            self.model = model
        self.query = query
        self.use_caching = use_caching if use_caching is not None else config.USE_CONTEXT_CACHING
        self._cached_contexts = {}  # Store cache names/URIs
        self._ensure_directories()
        self._initialize_gemini()
        self.initialize_briefing_file()

    def _select_optimal_model(self, query, max_results):
        """
        Automatically select optimal model based on task characteristics.

        Args:
            query: Search query (indicates domain complexity)
            max_results: Number of papers (indicates volume)

        Returns:
            Selected model name
        """
        # For high volume (50+ papers), use fast model
        if max_results >= 50:
            return config.MODELS["fast"]

        # For complex queries or deep analysis, use pro model
        complex_keywords = ["survey", "review", "comprehensive", "analysis", "theoretical"]
        if any(keyword in query.lower() for keyword in complex_keywords):
            return config.MODELS["deep"]

        # Default to balanced model
        return config.MODELS["balanced"]

    def _ensure_directories(self):
        Path(config.RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.SUMMARY_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.BRIEFING_DIR).mkdir(parents=True, exist_ok=True)

    def _initialize_gemini(self):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment. Please set it in your .env file.")
        # Client can auto-detect from GEMINI_API_KEY env var, but we pass it explicitly for clarity
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        print(f"Using Gemini model: {self.model}")

    def download_and_process_pdf(self, paper):
        """
        Download PDF from arXiv and upload to Gemini File API.

        Args:
            paper: Paper dict with 'entry_id' or 'url' field

        Returns:
            Uploaded file object from Gemini File API
        """
        # Extract arXiv ID from entry_id or url
        if 'entry_id' in paper:
            paper_id = paper['entry_id'].split('/')[-1]
        elif 'url' in paper:
            # Handle both full URLs and IDs
            if 'arxiv.org' in paper['url']:
                paper_id = paper['url'].split('/')[-1].replace('.pdf', '').replace('.abs', '')
            else:
                paper_id = paper['url']
        else:
            raise ValueError("Paper must have 'entry_id' or 'url' field")

        # Construct PDF URL
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

        print(f"Downloading PDF from {pdf_url}...")
        try:
            # Download PDF
            response = httpx.get(pdf_url, timeout=60.0)
            response.raise_for_status()
            pdf_data = response.content

            if len(pdf_data) > 50 * 1024 * 1024:  # 50MB limit for File API
                raise ValueError(f"PDF too large ({len(pdf_data) / 1024 / 1024:.2f}MB). File API limit is 50MB.")

            # Upload to Gemini File API
            pdf_io = io.BytesIO(pdf_data)
            uploaded_file = self.client.files.upload(
                file=pdf_io,
                config=dict(mime_type='application/pdf')
            )

            # Wait for file to be processed
            self._wait_for_file_processing(uploaded_file)

            print(f"PDF uploaded successfully: {uploaded_file.name}")
            return uploaded_file

        except httpx.HTTPError as e:
            raise Exception(f"Failed to download PDF: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")

    def _wait_for_file_processing(self, uploaded_file, max_wait_time=300):
        """
        Wait for file to be processed by Gemini API.

        Args:
            uploaded_file: File object from upload
            max_wait_time: Maximum time to wait in seconds (default 5 minutes)
        """
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            file_info = self.client.files.get(name=uploaded_file.name)

            if file_info.state == 'ACTIVE':
                return file_info
            elif file_info.state == 'FAILED':
                raise Exception(f"File processing failed: {uploaded_file.name}")

            # File is still processing
            elapsed = int(time.time() - start_time)
            print(f"File processing... ({elapsed}s elapsed)")
            time.sleep(5)

        raise TimeoutError(f"File processing timeout after {max_wait_time}s")

    def create_cached_context(self, content, ttl_seconds=None):
        """
        Create a cached context for frequently accessed content.

        Args:
            content: Content to cache (file, text, or list of contents)
            ttl_seconds: Time to live in seconds (default from config)

        Returns:
            Cache object with name/uri
        """
        if not self.use_caching:
            return None

        ttl = ttl_seconds or config.CACHE_TTL_SECONDS
        ttl_str = f"{ttl}s"

        try:
            cache = self.client.caches.create(
                model=self.model,
                contents=content if isinstance(content, list) else [content],
                ttl=ttl_str
            )
            print(f"Created cached context: {cache.name} (TTL: {ttl_str})")
            return cache
        except Exception as e:
            print(f"Failed to create cache: {e}")
            return None

    def _get_cache_key(self, paper):
        """Generate cache key from paper identifier"""
        paper_id = paper.get("id") or paper.get("entry_id") or paper.get("url", "")
        return f"{paper_id}_{self.model}"

    def get_or_create_cache(self, paper, content):
        """
        Get existing cache or create new one for a paper.

        Args:
            paper: Paper dict
            content: Content to cache (file or text)

        Returns:
            Cache object or None
        """
        if not self.use_caching:
            return None

        cache_key = self._get_cache_key(paper)

        # Check if we already have a cache for this paper
        if cache_key in self._cached_contexts:
            try:
                # Try to get the existing cache
                cache_name = self._cached_contexts[cache_key]
                cache = self.client.caches.get(name=cache_name)
                if cache.state == 'ACTIVE':
                    print(f"Using existing cache: {cache_name}")
                    return cache
            except Exception:
                # Cache expired or invalid, create new one
                pass

        # Create new cache
        cache = self.create_cached_context(content)
        if cache:
            self._cached_contexts[cache_key] = cache.name

        return cache

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

    def generate_final_briefing(self, use_structured_output=False, format_type="executive"):
        """
        Reads the accumulated article summaries from the briefing file, passes them to the local LLM
        to generate a final comprehensive briefing that focuses on broader implications and insights.
        The final synthesis is then appended to the same file with proper formatting.

        Args:
            use_structured_output: If True, generate structured JSON briefing
            format_type: Briefing format - "executive", "technical", or "visual"
        """
        import re
        print(f"Creating final comprehensive briefing (format: {format_type})...")

        with open(self.briefing_file, "r") as f:
            content = f.read()

        # Enhanced synthesis with system instruction based on format
        if format_type == "executive":
            system_instruction = """You are an executive research analyst creating comprehensive briefings from multiple research papers.
Your role is to synthesize information across papers to identify:
- Cross-cutting themes and patterns
- Emerging trends and contradictions
- Broader implications for industry and society
- Actionable insights for decision-makers

Write in a clear, executive-friendly format with well-organized sections and bullet points."""
            temperature = 0.8
        elif format_type == "technical":
            system_instruction = """You are a technical research analyst creating detailed technical briefings.
Your role is to provide:
- In-depth technical analysis of methodologies
- Comparative evaluation of approaches
- Technical strengths and limitations
- Research gaps and technical opportunities

Write in a technical format suitable for researchers and engineers."""
            temperature = 0.7
        else:  # visual
            system_instruction = """You are a research analyst creating visually-oriented briefings with structured data.
Your role is to organize information as:
- Comparison tables
- Trend charts descriptions
- Categorical breakdowns
- Timeline information

Format for easy visualization and data extraction."""
            temperature = 0.75

        config_params = {
            "system_instruction": system_instruction,
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40
        }

        # Add structured output if requested
        if use_structured_output:
            from .models import ComparativeAnalysis
            config_params["response_mime_type"] = "application/json"
            # Generate schema without additionalProperties
            schema = ComparativeAnalysis.model_json_schema()
            # Clean the schema recursively to remove additionalProperties
            def clean_schema(obj):
                if isinstance(obj, dict):
                    obj.pop('additionalProperties', None)
                    for v in obj.values():
                        clean_schema(v)
                elif isinstance(obj, list):
                    for item in obj:
                        clean_schema(item)
            clean_schema(schema)
            config_params["response_schema"] = schema

        gen_config = types.GenerateContentConfig(**config_params)

        synthesis_prompt = config.SYNTHESIS_PROMPT.format(content)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=synthesis_prompt,
                config=gen_config
            )

            if use_structured_output:
                # Parse structured output
                if hasattr(response, 'parsed') and response.parsed:
                    structured_data = response.parsed
                else:
                    import json
                    structured_data = json.loads(response.text)

                # Write structured briefing
                briefing_json_path = self.briefing_file.with_suffix('.json')
                with open(briefing_json_path, "w") as f:
                    json.dump(structured_data.model_dump() if hasattr(structured_data, 'model_dump') else structured_data,
                             f, indent=2)
                print(f"Structured briefing saved to: {briefing_json_path}")

                # Also create markdown version from structured data
                final_synthesis = self._format_structured_briefing(structured_data)
            else:
                final_synthesis = response.text.strip()

        except Exception as e:
            final_synthesis = f"Error generating synthesis: {str(e)}"

        final_synthesis = re.sub(r"<think>.*?</think>", "", final_synthesis, flags=re.DOTALL)

        with open(self.briefing_file, "a") as f:
            f.write(f"\n## Executive Summary ({format_type.capitalize()})\n\n")
            f.write(final_synthesis)
            f.write("\n\n---\n\n")
            f.write("*This briefing was automatically generated using ArXiv Paper Pulse and Google's Gemini API.*\n")

        print(f"Final comprehensive briefing appended to: {self.briefing_file}")
        print(f"Open it with your favorite markdown viewer or text editor at: {self.briefing_file}")

    def _format_structured_briefing(self, structured_data):
        """Format structured briefing data as markdown."""
        from .models import ComparativeAnalysis

        if isinstance(structured_data, dict):
            structured_data = ComparativeAnalysis(**structured_data)

        sections = []

        if structured_data.common_themes:
            sections.append("### Common Themes\n\n")
            for theme in structured_data.common_themes:
                sections.append(f"- {theme}\n")

        if structured_data.emerging_patterns:
            sections.append("\n### Emerging Patterns\n\n")
            for pattern in structured_data.emerging_patterns:
                sections.append(f"- {pattern}\n")

        if structured_data.conflicting_findings:
            sections.append("\n### Conflicting Findings\n\n")
            for conflict in structured_data.conflicting_findings:
                sections.append(f"- ⚠️ {conflict}\n")

        if structured_data.complementary_insights:
            sections.append("\n### Complementary Insights\n\n")
            for insight in structured_data.complementary_insights:
                sections.append(f"- {insight}\n")

        if structured_data.research_gaps:
            sections.append("\n### Research Gaps\n\n")
            for gap in structured_data.research_gaps:
                sections.append(f"- 📋 {gap}\n")

        return "\n".join(sections) if sections else "Structured analysis complete."

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
        """Summarize text using Gemini API (kept old name for compatibility)"""
        return self.gemini_summarize(text)

    def gemini_summarize_from_pdf(self, paper, use_streaming=False, use_pdf=True):
        """
        Summarize paper from PDF using Gemini API File API with optional caching.

        Args:
            paper: Paper dict with entry_id/url
            use_streaming: If True, returns a generator for streaming responses
            use_pdf: If True, download and process PDF; if False, use abstract only

        Returns:
            str: The summary text, or generator if use_streaming=True
        """
        if not use_pdf:
            return self.gemini_summarize(paper.get("abstract", ""), use_streaming=use_streaming)

        try:
            # Download and upload PDF
            uploaded_file = self.download_and_process_pdf(paper)

            # System instruction for PDF analysis
            system_instruction = """You are an expert scientific research analyst specializing in AI and physics papers.
Your role is to provide comprehensive, insightful analyses that help readers understand:
- The core problems and their significance
- Methodological approaches and innovations
- Key findings and contributions
- Real-world implications and applications
- Limitations and future research directions

Focus on clarity, depth, and practical relevance. Write in a professional yet accessible tone.
Analyze the full paper including figures, tables, and equations when available."""

            gen_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                top_p=0.95,
                top_k=40
            )

            prompt = "Analyze this research paper and provide a comprehensive analysis covering:\n\n1. Key Problem & Research Question\n2. Methodology & Approach\n3. Main Findings & Contributions\n4. Implications & Significance\n5. Limitations & Future Directions"

            # Use caching if enabled
            if self.use_caching:
                cache = self.get_or_create_cache(paper, uploaded_file)
                if cache and hasattr(cache, 'uri'):
                    # Use cached content URI in generate_content config
                    contents = [uploaded_file, prompt]  # Keep file for first run
                    # Cache will be used automatically on subsequent calls
                else:
                    contents = [uploaded_file, prompt]
            else:
                contents = [uploaded_file, prompt]

            if use_streaming:
                response_stream = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=gen_config
                )
                return response_stream
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=gen_config
                )
                return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            print(f"PDF summarization failed: {error_msg}, falling back to abstract")
            # Fallback to abstract-based summarization
            return self.gemini_summarize(paper.get("abstract", ""), use_streaming=use_streaming)

    def gemini_summarize(self, text, use_streaming=False, use_structured_output=False):
        """
        Summarize text using Gemini API with advanced features.

        Args:
            text: The text to summarize (paper abstract)
            use_streaming: If True, returns a generator for streaming responses
            use_structured_output: If True, return structured JSON using PaperAnalysis schema

        Returns:
            str or PaperAnalysis: The summary text, structured analysis, or generator if use_streaming=True
        """
        # System instruction for better guidance (moved from prompt template)
        system_instruction = """You are an expert scientific research analyst specializing in AI and physics papers.
Your role is to provide comprehensive, insightful analyses that help readers understand:
- The core problems and their significance
- Methodological approaches and innovations
- Key findings and contributions
- Real-world implications and applications
- Limitations and future research directions

Focus on clarity, depth, and practical relevance. Write in a professional yet accessible tone."""

        # Create configuration with optimized settings for summarization
        config_params = {
            "system_instruction": system_instruction,
            "temperature": 0.7,  # Balanced creativity and consistency
            "top_p": 0.95,
            "top_k": 40,
        }

        # Add thinking mode for complex analysis (if available in SDK)
        # Note: ThinkingConfig requires google-genai >= 0.4.0
        try:
            thinking_budget = config.THINKING_BUDGET_DEFAULT
            # Detect if text is complex (long or technical)
            if len(text) > 2000 or any(keyword in text.lower() for keyword in ['algorithm', 'methodology', 'experiment', 'evaluation']):
                thinking_budget = config.THINKING_BUDGET_COMPLEX

            if hasattr(types, 'ThinkingConfig'):
                config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        except Exception as e:
            # ThinkingConfig not available in this SDK version, skip it
            print(f"Note: Thinking mode not available: {e}")

        # Add structured output if requested
        if use_structured_output or config.USE_STRUCTURED_OUTPUT:
            config_params["response_mime_type"] = "application/json"
            # Generate schema without additionalProperties
            schema = PaperAnalysis.model_json_schema()
            # Clean the schema recursively to remove additionalProperties
            def clean_schema(obj):
                if isinstance(obj, dict):
                    obj.pop('additionalProperties', None)
                    for v in obj.values():
                        clean_schema(v)
                elif isinstance(obj, list):
                    for item in obj:
                        clean_schema(item)
            clean_schema(schema)
            config_params["response_schema"] = schema

        gen_config = types.GenerateContentConfig(**config_params)

        try:
            # Use structured prompt for better analysis (system instruction provides context)
            prompt = config.SUMMARY_PROMPT.format(text)

            if use_streaming:
                # Return streaming response generator
                response_stream = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=gen_config
                )
                return response_stream
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=gen_config
                )

                # If structured output, parse and return Pydantic model
                if use_structured_output or config.USE_STRUCTURED_OUTPUT:
                    if hasattr(response, 'parsed') and response.parsed:
                        return response.parsed
                    # Fallback: try to parse JSON from text
                    import json
                    try:
                        json_data = json.loads(response.text)
                        return PaperAnalysis(**json_data)
                    except:
                        return response.text.strip()
                else:
                    return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                error_text = f"Error: API rate limit or quota exceeded. Please try again later.\nDetails: {error_msg}"
                if use_structured_output:
                    # Return error in structured format
                    return PaperAnalysis(
                        problem_statement=error_text,
                        methodology=Methodology(approach="", datasets=[], metrics=[]),
                        results=Results(key_findings=[], performance_metrics=[], comparisons=[]),
                        contributions=[],
                        limitations=["API error occurred"],
                        future_work=[],
                        relevance_score=1
                    )
                return error_text
            elif "invalid" in error_msg.lower() or "400" in error_msg:
                error_text = f"Error: Invalid API request. Check your API key and model name.\nDetails: {error_msg}"
                if use_structured_output:
                    return PaperAnalysis(
                        problem_statement=error_text,
                        methodology=Methodology(approach="", datasets=[], metrics=[]),
                        results=Results(key_findings=[], performance_metrics=[], comparisons=[]),
                        contributions=[],
                        limitations=["Invalid request"],
                        future_work=[],
                        relevance_score=1
                    )
                return error_text
            else:
                error_text = f"Error generating summary: {error_msg}"
                if use_structured_output:
                    return PaperAnalysis(
                        problem_statement=error_text,
                        methodology=Methodology(approach="", datasets=[], metrics=[]),
                        results=Results(key_findings=[], performance_metrics=[], comparisons=[]),
                        contributions=[],
                        limitations=["Processing error"],
                        future_work=[],
                        relevance_score=1
                    )
                return error_text

    def analyze_multiple_papers(self, papers_list, use_structured_output=False):
        """
        Analyze multiple papers together in a single long-context request.
        Identifies cross-paper themes, contradictions, and complementary insights.

        Args:
            papers_list: List of paper dicts with entry_id/url
            use_structured_output: If True, return ComparativeAnalysis structure

        Returns:
            str or ComparativeAnalysis: Comparative analysis text or structured output
        """
        if len(papers_list) == 0:
            return "No papers provided for analysis."

        print(f"Analyzing {len(papers_list)} papers together using long context...")

        try:
            # Download and upload all PDFs
            uploaded_files = []
            for i, paper in enumerate(papers_list, 1):
                print(f"Processing paper {i}/{len(papers_list)}: {paper.get('title', 'Unknown')}")
                try:
                    uploaded_file = self.download_and_process_pdf(paper)
                    uploaded_files.append(uploaded_file)
                except Exception as e:
                    print(f"Failed to process PDF for {paper.get('title', 'Unknown')}: {e}")
                    # Continue with other papers

            if not uploaded_files:
                return "No papers could be processed for analysis."

            # System instruction for comparative analysis
            system_instruction = """You are an expert research analyst specializing in comparative analysis of research papers.
Your role is to identify:
- Common themes and shared approaches across papers
- Methodological differences and innovations
- Conflicting findings and contradictions
- Complementary insights that work together
- Emerging patterns and trends
- Research gaps and opportunities

Provide a comprehensive comparative analysis that helps researchers understand the landscape."""

            config_params = {
                "system_instruction": system_instruction,
                "temperature": 0.8,  # Higher for more creative synthesis
                "top_p": 0.95,
                "top_k": 40,
            }

            if use_structured_output:
                config_params["response_mime_type"] = "application/json"
                # Generate schema without additionalProperties
                schema = ComparativeAnalysis.model_json_schema()
                # Clean the schema recursively to remove additionalProperties
                def clean_schema(obj):
                    if isinstance(obj, dict):
                        obj.pop('additionalProperties', None)
                        for v in obj.values():
                            clean_schema(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            clean_schema(item)
                clean_schema(schema)
                config_params["response_schema"] = schema

            gen_config = types.GenerateContentConfig(**config_params)

            prompt = f"""Compare and analyze these {len(uploaded_files)} research papers together. Provide:
1. Common themes across all papers
2. Methodological approaches used by each (identify papers by title)
3. Any conflicting findings or disagreements
4. How these papers complement each other
5. Emerging patterns or trends
6. Identified research gaps

For each paper, briefly note: {', '.join([p.get('title', 'Unknown')[:50] for p in papers_list[:5]])}"""

            contents = uploaded_files + [prompt]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=gen_config
            )

            if use_structured_output:
                if hasattr(response, 'parsed') and response.parsed:
                    return response.parsed
                # Fallback: try to parse JSON
                import json
                try:
                    json_data = json.loads(response.text)
                    return ComparativeAnalysis(**json_data)
                except:
                    return response.text.strip()

            return response.text.strip()

        except Exception as e:
            error_msg = str(e)
            return f"Error in multi-paper analysis: {error_msg}"

    def gemini_summarize_with_url_context(self, paper_url, use_grounding=False):
        """
        Summarize paper using URL context tool to directly access arXiv URL.

        Args:
            paper_url: Full arXiv URL or ID
            use_grounding: If True, also use Google Search grounding

        Returns:
            str: The summary text
        """
        # Construct full URL if needed
        if not paper_url.startswith("http"):
            if "/" in paper_url:
                paper_id = paper_url.split("/")[-1]
            else:
                paper_id = paper_url
            paper_url = f"https://arxiv.org/abs/{paper_id}"

        tools = [{"url_context": {}}]
        if use_grounding or config.USE_GROUNDING:
            tools.append({"google_search": {}})

        system_instruction = """You are an expert scientific research analyst.
Analyze the research paper from the provided URL and provide a comprehensive analysis."""

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
            tools=tools
        )

        prompt = f"""Analyze the research paper at {paper_url} and provide a comprehensive analysis covering:

1. Key Problem & Research Question
2. Methodology & Approach
3. Main Findings & Contributions
4. Implications & Significance
5. Limitations & Future Directions

If grounding is enabled, also provide context on recent developments and real-world applications."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=gen_config
            )

            # Extract URL context metadata if available
            url_metadata = None
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'url_context_metadata'):
                    url_metadata = candidate.url_context_metadata
                    print(f"Retrieved content from: {url_metadata}")

            return response.text.strip()
        except Exception as e:
            return f"Error using URL context: {str(e)}"
