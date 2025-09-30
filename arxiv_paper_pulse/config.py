# arxiv_paper_pulse/config.py

SUMMARY_FILE = "arxiv_paper_pulse/summaries.json"
DEFAULT_MODEL = "llama2"
RAW_DATA_DIR = "arxiv_paper_pulse/data/raw"
SUMMARY_DIR = "arxiv_paper_pulse/data/summaries"
BRIEFING_DIR = "arxiv_paper_pulse/data/briefings"

# Enhanced prompt for Ollama summarization that focuses on implications and context
SUMMARY_PROMPT = """Provide a comprehensive analysis of the paper, focusing on its real-world implications and significance:

1. Key Problem & Research Question: What issue is this paper addressing and why is it important?

2. Methodology & Approach: How did they tackle the problem?

3. Main Findings & Contributions: What are the most important discoveries or advancements?

4. Implications & Significance:
   - What does this mean for the field or industry?
   - What practical applications or consequences might result?
   - How might this change our understanding or current practices?

5. Limitations & Future Directions: What are the constraints of this work and where might it lead?

<think>Analyze the abstract carefully and provide thoughtful insights about the broader impact of this research.</think>

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
