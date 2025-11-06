# arxiv_paper_pulse/config.py
import os
from dotenv import load_dotenv

load_dotenv()

SUMMARY_FILE = "arxiv_paper_pulse/summaries.json"
DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAW_DATA_DIR = "arxiv_paper_pulse/data/raw"
SUMMARY_DIR = "arxiv_paper_pulse/data/summaries"
BRIEFING_DIR = "arxiv_paper_pulse/data/briefings"
IMAGE_OUTPUT_DIR = "arxiv_paper_pulse/data/generated_images"
IMAGE_API_LOG_DIR = "arxiv_paper_pulse/data/api_logs"
GAME_OUTPUT_DIR = "arxiv_paper_pulse/data/self_generated_games"
ARTICLE_OUTPUT_DIR = "arxiv_paper_pulse/data/articles"
BOT_WORKING_DIR = "arxiv_paper_pulse/data/bots"
BEEHIIV_DATA_DIR = "arxiv_paper_pulse/data/beehiiv"
BEEHIIV_POLL_INTERVAL = int(os.getenv("BEEHIIV_POLL_INTERVAL", "3600"))  # Default: 1 hour
BEEHIIV_AUTO_POLL = os.getenv("BEEHIIV_AUTO_POLL", "false").lower() == "true"
BEEHIIV_FEEDS = os.getenv("BEEHIIV_FEEDS", "").split(",") if os.getenv("BEEHIIV_FEEDS") else []  # Comma-separated feed URLs
CONTEXT_MAX_BYTES = int(os.getenv("CONTEXT_MAX_BYTES", str(65536)))  # 64KB default
CONTEXT_HISTORY_RETENTION = int(os.getenv("CONTEXT_HISTORY_RETENTION", "20"))
CONTEXT_HISTORY_DIRNAME = "context_history"

# Feature flags for Gemini API capabilities
USE_PDF_PROCESSING = os.getenv("USE_PDF_PROCESSING", "false").lower() == "true"
USE_STRUCTURED_OUTPUT = os.getenv("USE_STRUCTURED_OUTPUT", "false").lower() == "true"
USE_CONTEXT_CACHING = os.getenv("USE_CONTEXT_CACHING", "false").lower() == "true"
USE_GROUNDING = os.getenv("USE_GROUNDING", "false").lower() == "true"
USE_URL_CONTEXT = os.getenv("USE_URL_CONTEXT", "false").lower() == "true"

# Context caching configuration
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default

# Thinking mode configuration
THINKING_BUDGET_DEFAULT = int(os.getenv("THINKING_BUDGET_DEFAULT", "1000"))
THINKING_BUDGET_COMPLEX = int(os.getenv("THINKING_BUDGET_COMPLEX", "5000"))

# Model selection configuration
MODELS = {
    "fast": "gemini-2.5-flash-lite",  # High-volume, fast summaries
    "balanced": "gemini-2.5-flash",    # Default, best price-performance
    "deep": "gemini-2.5-pro",          # Deep analysis, complex reasoning
}

AUTO_MODEL_SELECTION = os.getenv("AUTO_MODEL_SELECTION", "true").lower() == "true"

# Note: System instructions are now defined in core.py gemini_summarize() method
# This prompt is used as a simple wrapper - the detailed guidance comes from system instructions
SUMMARY_PROMPT = """Analyze the following research paper abstract and provide a comprehensive analysis covering:

1. Key Problem & Research Question: What issue is this paper addressing and why is it important?
2. Methodology & Approach: How did they tackle the problem?
3. Main Findings & Contributions: What are the most important discoveries or advancements?
4. Implications & Significance: What does this mean for the field, industry, and practical applications?
5. Limitations & Future Directions: What are the constraints and where might this lead?

Paper Abstract:
{}
"""

# Synthesis prompt for creating the final briefing
SYNTHESIS_PROMPT = """Based on the following article summaries from arXiv, create a comprehensive executive briefing that:

1. Identifies the most significant insights across all papers
2. Highlights emerging trends, patterns, or contradictions
3. Explains real-world implications for industry, society, and future research
4. Provides actionable takeaways for someone wanting to stay informed in this field

Format your response as an easy-to-skim executive summary with:
- A brief overall assessment (2-3 sentences)
- Key themes as clearly marked bullet points
- Each bullet containing a concise insight and its importance
- A concluding paragraph on what to watch for next

Article Summaries:
{}
"""
