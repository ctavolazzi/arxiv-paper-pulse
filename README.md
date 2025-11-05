# arxiv-paper-pulse

A Python package that fetches recent AI and physics papers from arXiv and summarizes them using Google's Gemini API with advanced features including full PDF processing, structured output, context caching, and multi-paper analysis.

## Features

### Core Functionality

- **Fetch Papers:** Uses [arxiv.py](https://github.com/lukasschwab/arxiv.py) to query arXiv for AI and physics papers.
- **Advanced Summarization:** Powered by Google's Gemini API with multiple model options.
- **JSON Storage:** Summaries are stored in JSON files with optional structured output.
- **CLI and Library Usage:** Run it from the command line or import it in your projects.
- **REST API:** FastAPI server with endpoints for all features.

### Advanced Gemini API Features

- **📄 Full PDF Processing:** Analyze entire research papers (not just abstracts) using Gemini's File API
- **📊 Structured Output:** Get JSON-formatted analyses with Pydantic schemas
- **💾 Context Caching:** Cost-optimized caching system (~75% cost savings for repeated queries)
- **🔗 Long Context Analysis:** Analyze multiple papers together (up to 1M tokens)
- **🌐 URL Context Tool:** Direct arXiv URL processing without downloads
- **🔍 Google Search Grounding:** Real-world context and applications
- **🧠 Thinking Mode:** Configurable reasoning budgets for complex papers
- **⚡ Batch Processing:** Async batch API for cost-efficient bulk processing (~50% savings)
- **🔎 Semantic Search:** Embedding-based paper similarity and clustering
- **💬 Interactive Chat:** Multi-turn conversations about papers
- **🤖 Function Calling:** Autonomous arXiv search and analysis tools
- **📈 Smart Model Selection:** Automatic model choice based on task complexity

## Installation

Clone the repository, then install locally:

```bash
pip install .
```

### Environment Setup

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_api_key_here
```

Optional configuration flags:

```bash
USE_PDF_PROCESSING=true
USE_STRUCTURED_OUTPUT=false
USE_CONTEXT_CACHING=true
USE_GROUNDING=false
USE_URL_CONTEXT=false
CACHE_TTL_SECONDS=3600
THINKING_BUDGET_DEFAULT=1000
THINKING_BUDGET_COMPLEX=5000
AUTO_MODEL_SELECTION=true
```

## Usage

### Command Line Interface

#### Basic Usage

```bash
# Fetch and summarize papers (abstracts only)
arxiv-paper-pulse --query "cat:cs.AI" --max_results 10

# Process full PDF papers
arxiv-paper-pulse --query "cat:cs.AI" --pdf

# Use structured JSON output
arxiv-paper-pulse --structured

# Enable context caching for cost savings
arxiv-paper-pulse --caching

# Analyze multiple papers together
arxiv-paper-pulse --analyze-multiple --max_results 5

# Use URL context tool (no PDF download)
arxiv-paper-pulse --url-context

# Enable Google Search grounding
arxiv-paper-pulse --grounding

# Use batch processing (async, cost-efficient)
arxiv-paper-pulse --batch

# Select specific model
arxiv-paper-pulse --model gemini-2.5-pro

# Use streaming responses
arxiv-paper-pulse --streaming
```

#### Advanced Examples

```bash
# Full analysis with all features
arxiv-paper-pulse \
  --query "cat:cs.AI AND abs:transformer" \
  --max_results 5 \
  --pdf \
  --structured \
  --caching \
  --briefing-format technical

# Multi-paper comparative analysis
arxiv-paper-pulse \
  --analyze-multiple \
  --max_results 3 \
  --structured
```

### Python Library Usage

#### Basic Summarization

```python
from arxiv_paper_pulse.core import ArxivSummarizer

# Create summarizer
summarizer = ArxivSummarizer(
    max_results=10,
    query="cat:cs.AI",
    model="gemini-2.5-flash"
)

# Summarize papers (abstracts)
summaries = summarizer.summarize_papers()
```

#### PDF Processing

```python
# Process full PDF papers
summarizer = ArxivSummarizer()
summaries = summarizer.summarize_papers(force_pull=True)

# For individual PDFs
paper = {"entry_id": "2301.12345", "title": "Paper Title"}
summary = summarizer.gemini_summarize_from_pdf(paper, use_pdf=True)
```

#### Structured Output

```python
from arxiv_paper_pulse.models import PaperAnalysis

# Get structured JSON analysis
analysis = summarizer.gemini_summarize(
    abstract_text,
    use_structured_output=True
)

# analysis is a PaperAnalysis Pydantic model
print(analysis.problem_statement)
print(analysis.methodology.approach)
print(analysis.results.key_findings)
print(analysis.relevance_score)
```

#### Context Caching

```python
# Enable caching for cost savings
summarizer = ArxivSummarizer(use_caching=True)

# First call - creates cache
summary1 = summarizer.gemini_summarize_from_pdf(paper)

# Subsequent calls use cached context (~75% cost savings)
summary2 = summarizer.gemini_summarize_from_pdf(paper)
```

#### Multi-Paper Analysis

```python
# Analyze multiple papers together
papers = [
    {"entry_id": "2301.12345", "title": "Paper 1"},
    {"entry_id": "2302.12345", "title": "Paper 2"},
    {"entry_id": "2303.12345", "title": "Paper 3"},
]

comparative_analysis = summarizer.analyze_multiple_papers(
    papers,
    use_structured_output=True
)

# Get structured comparison
print(comparative_analysis.common_themes)
print(comparative_analysis.conflicting_findings)
print(comparative_analysis.emerging_patterns)
```

#### URL Context Tool

```python
# Process paper directly from URL (no download)
summary = summarizer.gemini_summarize_with_url_context(
    "https://arxiv.org/abs/2301.12345",
    use_grounding=True  # Include Google Search grounding
)
```

#### Semantic Search

```python
from arxiv_paper_pulse.embeddings import PaperEmbeddings

embeddings_gen = PaperEmbeddings()

# Generate embeddings
papers = [...]
embeddings = embeddings_gen.generate_batch_embeddings(papers)

# Find similar papers
target_paper = papers[0]
similar = embeddings_gen.find_similar_papers(
    target_paper,
    papers,
    top_k=5,
    threshold=0.7
)

# Cluster papers
clusters = embeddings_gen.cluster_papers(papers, n_clusters=5)
```

#### Interactive Chat

```python
from arxiv_paper_pulse.chat import PaperChatSession

# Create chat session with papers
papers = [...]
chat = PaperChatSession(papers)

# Ask questions
response = chat.ask("What are the main contributions across these papers?")
print(response)

# Continue conversation
response = chat.ask("Which paper has the best experimental results?")
print(response)

# Get conversation history
history = chat.get_history()
```

#### Batch Processing

```python
from arxiv_paper_pulse.batch_processor import BatchPaperProcessor

processor = BatchPaperProcessor(model="gemini-2.5-flash")

# Submit batch job
batch_id = processor.submit_batch(papers)

# Check status
status = processor.check_batch_status(batch_id)

# Wait for completion
final_status = processor.wait_for_completion(batch_id)

# Get results
results = processor.get_batch_results(batch_id)
```

### REST API

Start the API server:

```bash
python run_api.py
# or
uvicorn arxiv_paper_pulse.api:app --reload
```

#### API Endpoints

**Basic Endpoints:**
- `GET /` - Frontend or API info
- `GET /health` - Health check
- `GET /api/papers` - Get latest summaries
- `GET /api/briefing` - Get latest briefing
- `POST /api/summarize` - Summarize papers
- `POST /api/summarize-stream` - Stream summary

**Advanced Endpoints:**
- `POST /api/summarize-pdf` - Summarize from PDF
- `POST /api/summarize-structured` - Get structured JSON
- `POST /api/analyze-multiple` - Multi-paper analysis
- `POST /api/url-context` - URL context processing
- `POST /api/embeddings/generate` - Generate embeddings
- `POST /api/embeddings/similar` - Find similar papers
- `POST /api/batch/submit` - Submit batch job
- `GET /api/batch/{batch_id}/status` - Check batch status
- `GET /api/batch/{batch_id}/results` - Get batch results
- `POST /api/chat/create` - Create chat session
- `POST /api/chat/ask` - Ask question in chat

#### Example API Calls

```bash
# Summarize papers
curl -X POST "http://localhost:8000/api/summarize" \
  -H "Content-Type: application/json" \
  -d '{"query": "cat:cs.AI", "max_results": 10}'

# Get structured analysis
curl -X POST "http://localhost:8000/api/summarize-structured" \
  -H "Content-Type: application/json" \
  -d '{"abstract": "Paper abstract here"}'

# Generate embeddings
curl -X POST "http://localhost:8000/api/embeddings/generate" \
  -H "Content-Type: application/json" \
  -d '{"papers": [...]}'
```

## Models

### Available Models

- `gemini-2.5-flash` (default) - Best price-performance, balanced
- `gemini-2.5-pro` - Deep analysis, complex reasoning
- `gemini-2.5-flash-lite` - High-volume, fast summaries

Auto-selection is enabled by default based on:
- **Volume:** High volume (50+ papers) → flash-lite
- **Complexity:** Complex queries → pro
- **Default:** Balanced → flash

### Model Selection

```python
# Manual selection
summarizer = ArxivSummarizer(model="gemini-2.5-pro")

# Auto-selection (default)
summarizer = ArxivSummarizer()  # Automatically selects based on query/volume
```

## Cost Optimization

### Context Caching

Enable caching to save ~75% on repeated queries:

```python
summarizer = ArxivSummarizer(use_caching=True)
# or
USE_CONTEXT_CACHING=true in .env
```

### Batch Processing

Use batch API for ~50% cost savings on bulk processing:

```python
processor = BatchPaperProcessor()
batch_id = processor.submit_batch(papers)  # ~50% cheaper
```

### Model Selection

- Use `gemini-2.5-flash-lite` for high-volume screening
- Use `gemini-2.5-flash` for balanced performance
- Use `gemini-2.5-pro` only for complex deep analysis

## Rate Limiting

Automatic rate limiting and retry logic is built-in:

```python
from arxiv_paper_pulse.utils import retry_with_backoff, RateLimiter

# Automatic retries with exponential backoff
@retry_with_backoff(max_retries=3, base_delay=1.0)
def api_call():
    # Your API call
    pass

# Rate limiter for manual control
limiter = RateLimiter(max_calls=100, time_window=60.0)  # 100 calls per minute
limiter.wait_if_needed()
```

## Configuration

All features can be configured via environment variables or code:

| Feature | Env Var | Default | Description |
|---------|---------|---------|-------------|
| PDF Processing | `USE_PDF_PROCESSING` | `false` | Enable full PDF analysis |
| Structured Output | `USE_STRUCTURED_OUTPUT` | `false` | Enable JSON schemas |
| Context Caching | `USE_CONTEXT_CACHING` | `false` | Enable caching |
| Grounding | `USE_GROUNDING` | `false` | Enable Google Search |
| URL Context | `USE_URL_CONTEXT` | `false` | Enable URL tool |
| Cache TTL | `CACHE_TTL_SECONDS` | `3600` | Cache lifetime |
| Thinking Budget | `THINKING_BUDGET_DEFAULT` | `1000` | Default reasoning tokens |
| Auto Model Select | `AUTO_MODEL_SELECTION` | `true` | Auto-select models |

## Examples

### Example 1: Full Paper Analysis

```python
from arxiv_paper_pulse.core import ArxivSummarizer

summarizer = ArxivSummarizer(
    max_results=5,
    query="cat:cs.AI AND abs:transformer",
    use_caching=True
)

# Fetch and analyze full PDFs
papers = summarizer.fetch_raw_data()
for paper in papers:
    summary = summarizer.gemini_summarize_from_pdf(paper, use_pdf=True)
    print(f"{paper['title']}: {summary[:200]}...")
```

### Example 2: Structured Analysis

```python
from arxiv_paper_pulse.core import ArxivSummarizer

summarizer = ArxivSummarizer()

# Get structured analysis
abstract = "Large language models have shown remarkable capabilities..."
analysis = summarizer.gemini_summarize(abstract, use_structured_output=True)

# Access structured fields
print(f"Problem: {analysis.problem_statement}")
print(f"Approach: {analysis.methodology.approach}")
print(f"Findings: {analysis.results.key_findings}")
print(f"Score: {analysis.relevance_score}/10")
```

### Example 3: Multi-Paper Comparison

```python
from arxiv_paper_pulse.core import ArxivSummarizer

summarizer = ArxivSummarizer()

papers = summarizer.fetch_raw_data()
comparison = summarizer.analyze_multiple_papers(
    papers[:3],
    use_structured_output=True
)

print("Common Themes:")
for theme in comparison.common_themes:
    print(f"  - {theme}")

print("\nConflicting Findings:")
for conflict in comparison.conflicting_findings:
    print(f"  - {conflict}")
```

## Project Structure

```
arxiv-paper-pulse/
├── arxiv_paper_pulse/
│   ├── core.py              # Main summarization logic
│   ├── config.py            # Configuration and feature flags
│   ├── models.py            # Pydantic schemas
│   ├── api.py               # FastAPI REST endpoints
│   ├── cli.py               # Command-line interface
│   ├── batch_processor.py   # Batch processing
│   ├── embeddings.py       # Semantic search
│   ├── chat.py             # Interactive chat
│   ├── tools.py            # Function calling
│   └── utils.py            # Utilities and rate limiting
├── frontend/               # Web frontend
├── tests/                  # Test suite
└── data/                   # Generated summaries and briefings
```

## License

See LICENSE file.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Uses [arxiv.py](https://github.com/lukasschwab/arxiv.py) for arXiv queries
- Powered by [Google's Gemini API](https://ai.google.dev/gemini-api/docs)
