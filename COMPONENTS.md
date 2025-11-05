# ArXiv Paper Pulse - Components Inventory

This document catalogs all modules, classes, API endpoints, CLI commands, schemas, and features of the ArXiv Paper Pulse system.

**Last Updated:** 2025-11-01

---

## 📦 Core Modules

### `arxiv_paper_pulse/core.py`
**Primary Class:** `ArxivSummarizer`
- Main summarization engine
- arXiv paper fetching and processing
- PDF download and File API upload
- Gemini API integration for summarization
- Context caching support
- Multi-paper comparative analysis
- URL context tool integration
- Google Search grounding support
- Thinking mode configuration
- Streaming response support
- Structured output generation

**Key Methods:**
- `summarize_papers()` - Summarize papers from abstracts
- `download_and_process_pdf()` - Download and upload PDF to File API
- `gemini_summarize()` - Summarize with Gemini API
- `gemini_summarize_from_pdf()` - Summarize from PDF
- `analyze_multiple_papers()` - Compare multiple papers
- `gemini_summarize_with_url_context()` - Process via URL context tool
- `_wait_for_file_processing()` - Wait for File API processing

### `arxiv_paper_pulse/config.py`
**Configuration Management**
- Environment variable loading
- Feature flags (PDF processing, structured output, caching, grounding)
- Model selection configuration
- Thinking budget settings
- Directory paths (raw, summaries, briefings, images)
- Prompt templates (summary, synthesis)
- Default model selection

**Configuration Options:**
- `GEMINI_API_KEY` - API key
- `DEFAULT_MODEL` - Default Gemini model
- `USE_PDF_PROCESSING` - Enable PDF processing
- `USE_STRUCTURED_OUTPUT` - Enable structured JSON output
- `USE_CONTEXT_CACHING` - Enable context caching
- `USE_GROUNDING` - Enable Google Search grounding
- `USE_URL_CONTEXT` - Enable URL context tool
- `CACHE_TTL_SECONDS` - Cache TTL
- `THINKING_BUDGET_DEFAULT` - Default thinking budget
- `THINKING_BUDGET_COMPLEX` - Complex thinking budget
- `AUTO_MODEL_SELECTION` - Auto-select model based on task

### `arxiv_paper_pulse/models.py`
**Data Models & Schemas**

**Legacy Models:**
- `PaperSummary` - Legacy paper summary class

**Pydantic Schemas for Structured Output:**
- `Methodology` - Research methodology details
  - `approach` - Primary research approach
  - `datasets` - Datasets used
  - `metrics` - Evaluation metrics
  - `experimental_setup` - Experimental configuration

- `Results` - Key findings and results
  - `key_findings` - Main discoveries
  - `performance_metrics` - Quantitative measurements
  - `statistical_significance` - Statistical confidence
  - `comparisons` - Baseline comparisons

- `Contributions` - Research contributions
  - `theoretical_contributions` - Theoretical advances
  - `methodological_contributions` - Novel methods
  - `practical_applications` - Real-world applications

- `PaperAnalysis` - Comprehensive paper analysis
  - `problem_statement` - Core problem addressed
  - `methodology` - Methodology details
  - `results` - Experimental results
  - `contributions` - Key contributions
  - `limitations` - Study limitations
  - `future_work` - Future directions
  - `relevance_score` - Relevance score (1-10)
  - `key_insights` - Actionable insights
  - `related_domains` - Related domains

- `ComparativeAnalysis` - Multi-paper comparison
  - `common_themes` - Shared themes
  - `methodological_approaches` - Methods comparison
  - `conflicting_findings` - Contradictions
  - `complementary_insights` - Complementary findings
  - `emerging_patterns` - Trends across papers
  - `research_gaps` - Identified gaps

### `arxiv_paper_pulse/documents.py`
**NEW: Documents Module** (2025-11-01)
**Primary Class:** `DocumentProcessor`

**Input Schemas:**
- `DocumentFromURL` - PDF from URL
- `DocumentFromPath` - PDF from local file path
- `DocumentFromBytes` - PDF from bytes (inline, <20MB)
- `DocumentFromBase64` - PDF from base64 (inline, <20MB)
- `DocumentInput` - Single document wrapper
- `MultipleDocumentsInput` - Batch processing (1-1000 pages)

**Processing Configuration:**
- `ProcessingMethod` enum - AUTO, INLINE, FILE_API
- `OutputFormat` enum - TEXT, STRUCTURED, TRANSCRIPTION
- `DocumentProcessingConfig` - Comprehensive config options

**Output Schemas:**
- `FileMetadata` - File upload metadata
- `DocumentProcessingResult` - Single document result
- `MultipleDocumentsResult` - Batch processing result
- `DocumentProcessingError` - Error information

**Key Methods:**
- `process()` - Process single document
- `process_multiple()` - Process multiple documents
- `_determine_method()` - Auto-select processing method
- `_process_inline()` - Inline processing (<20MB)
- `_process_file_api()` - File API processing (>=20MB)
- `_upload_file()` - Upload to File API
- `_wait_for_file_processing()` - Wait for processing

### `arxiv_paper_pulse/api.py`
**FastAPI Application**
**Main App:** `app = FastAPI()`

**API Endpoints:**

**GET Endpoints:**
- `GET /` - Serve frontend HTML
- `GET /health` - Health check
- `GET /api/papers` - Get latest paper summaries
- `GET /api/briefing` - Get latest briefing content
- `GET /api/available` - Get total available papers for query
- `GET /api/batch/{batch_id}/status` - Get batch status
- `GET /api/batch/{batch_id}/results` - Get batch results

**POST Endpoints:**
- `POST /api/summarize` - Summarize papers from arXiv
- `POST /api/search` - Search arXiv papers (fast, no summarization)
- `POST /api/summarize-pdf` - Summarize paper from PDF
- `POST /api/summarize-structured` - Get structured JSON summary
- `POST /api/summarize-stream` - Stream paper summary (SSE)
- `POST /api/analyze-multiple` - Analyze multiple papers together
- `POST /api/chat/create` - Create chat session
- `POST /api/chat/ask` - Ask question in chat session
- `POST /api/embeddings/generate` - Generate embeddings
- `POST /api/embeddings/similar` - Find similar papers
- `POST /api/batch/submit` - Submit batch processing
- `POST /api/url-context` - Summarize using URL context
- `POST /api/generate-image` - Generate image from prompt

**Middleware:**
- CORS middleware (allows all origins)
- Static file serving (`/static`)

### `arxiv_paper_pulse/cli.py`
**Command-Line Interface**
**Entry Point:** `main()`

**CLI Arguments:**
- `--max_results` - Number of papers to fetch (default: 10)
- `--pull` - Force pull new data from arXiv
- `--query` - Search query for arXiv (default: 'cat:cs.AI')
- `--pdf` - Process full PDF papers
- `--structured` - Use structured JSON output
- `--caching` - Enable context caching
- `--model` - Model to use
- `--url-context` - Use URL context tool
- `--grounding` - Enable Google Search grounding
- `--batch` - Use batch processing
- `--analyze-multiple` - Analyze multiple papers together
- `--briefing-format` - Briefing format (executive/technical/visual)
- `--streaming` - Use streaming responses

**Features:**
- Interactive article selection
- Cached data detection
- Briefing generation

### `arxiv_paper_pulse/batch_processor.py`
**Primary Class:** `BatchPaperProcessor`
- Async batch processing for cost efficiency
- Batch API integration
- Status tracking
- Results retrieval

**Key Methods:**
- `submit_batch()` - Submit papers for batch processing
- `check_batch_status()` - Check batch status
- `get_batch_results()` - Get batch results

### `arxiv_paper_pulse/embeddings.py`
**Primary Class:** `PaperEmbeddings`
- Semantic embedding generation
- Similarity search
- Paper clustering

**Key Methods:**
- `generate_batch_embeddings()` - Generate embeddings for papers
- `find_similar_papers()` - Find similar papers

### `arxiv_paper_pulse/chat.py`
**Primary Class:** `PaperChatSession`
- Multi-turn conversations about papers
- Chat history management
- Streaming chat support

**Key Methods:**
- `ask()` - Ask question in chat
- `ask_streaming()` - Stream chat response

### `arxiv_paper_pulse/tools.py`
**Primary Class:** `ArxivToolHandler`
- Function calling definitions
- Autonomous arXiv search tools

**Functions:**
- `define_arxiv_tools()` - Define arXiv function calling tools

### `arxiv_paper_pulse/image_generator.py`
**Primary Class:** `ImageGenerator`
- Text-to-image generation
- Image editing capabilities
- Config-driven output directory

**Key Methods:**
- `generate_from_text()` - Generate image from prompt
- `generate_from_text_and_image()` - Edit image with prompt
- `generate_and_save()` - Generate and save image
- `save_image()` - Save PIL Image to file

**Configuration:**
- Model: `gemini-2.5-flash-image-preview`
- Output directory: `config.IMAGE_OUTPUT_DIR`

### `arxiv_paper_pulse/utils.py`
**Utility Functions**
- Rate limiting utilities
- Total available papers count
- Unique ID generation
- File management helpers

### `arxiv_paper_pulse/crawler.py`
**Web Crawler** (Legacy)
- ArXiv paper crawling functionality

### `arxiv_paper_pulse/gui.py`
**GUI Application** (Legacy)
- Graphical user interface
- Article selection dialogs

---

## 🎨 Frontend Components

### `frontend/index.html`
**Single-Page Web Application**
- Paper search and summarization interface
- Real-time streaming display
- Paper selection interface
- Briefing generation UI
- Image generation interface
- Interactive chat interface

**Key Features:**
- SSE (Server-Sent Events) for streaming
- Dynamic content updates
- Article selection checkboxes
- Progress indicators

---

## 🗄️ Data Storage

### Directories:
- `arxiv_paper_pulse/data/raw/` - Raw arXiv data JSON files
- `arxiv_paper_pulse/data/summaries/` - Generated summary JSON files
- `arxiv_paper_pulse/data/briefings/` - Generated briefing Markdown files
- `arxiv_paper_pulse/data/generated_images/` - Generated image files

### File Naming:
- Raw: `YYYY-MM-DD_HHMMSS_raw.json`
- Summary: `YYYY-MM-DD_HHMMSS_summary.json`
- Briefing: `YYYY-MM-DD_HHMMSS_briefing.md`
- Images: `generated_image_YYYYMMDD_HHMMSS.png`

---

## 🧪 Test Suite

### Test Modules (`tests/`):
- `test_core.py` - Core summarization tests
- `test_briefing.py` - Briefing generation tests
- `test_cli_article_selection.py` - CLI selection tests
- `test_gui_article_selection.py` - GUI selection tests
- `test_prompt_config.py` - Prompt configuration tests
- `test_crawler.py` - Crawler functionality tests
- `test_gui.py` - GUI functionality tests
- `test_import.py` - Import functionality tests
- `test_workflow_integration.py` - End-to-end workflow tests
- `test_gemini_features.py` - Gemini API feature tests
- `test_api_endpoints.py` - API endpoint tests
- `test_image_generator.py` - Image generation tests

**Test Configuration:**
- `conftest.py` - Pytest fixtures and configuration
- Markers: `@pytest.mark.integration`, `@pytest.mark.gui`
- Environment variable: `RUN_LIVE_TESTS` for external API tests

---

## 🔧 External Dependencies

### Python Packages:
- `google-genai` - Gemini API SDK
- `arxiv` - arXiv paper fetching
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation and schemas
- `httpx` - HTTP client for downloads
- `numpy` - Numerical operations (embeddings)
- `pillow` - Image processing
- `python-dotenv` - Environment variable loading

### External Services:
- **Google Gemini API** - AI summarization and analysis
- **arXiv.org** - Paper source
- **Google Search** - Grounding service (optional)

---

## 🚀 Features & Capabilities

### Core Features:
✅ **Paper Fetching** - Query arXiv for papers
✅ **Abstract Summarization** - Summarize paper abstracts
✅ **PDF Processing** - Full paper analysis via File API
✅ **Structured Output** - JSON-formatted analyses
✅ **Context Caching** - Cost-optimized caching (~75% savings)
✅ **Multi-Paper Analysis** - Compare multiple papers together
✅ **URL Context Tool** - Direct arXiv URL processing
✅ **Google Search Grounding** - Real-world context
✅ **Thinking Mode** - Configurable reasoning budgets
✅ **Batch Processing** - Async bulk processing (~50% savings)
✅ **Semantic Search** - Embedding-based similarity
✅ **Interactive Chat** - Multi-turn conversations
✅ **Function Calling** - Autonomous arXiv tools
✅ **Smart Model Selection** - Auto-select based on task
✅ **Streaming Responses** - Real-time output streaming
✅ **Image Generation** - Text-to-image and editing
✅ **Documents Module** - Comprehensive PDF processing

### Output Formats:
- **Text** - Plain text summaries
- **Structured JSON** - Pydantic schema-based output
- **HTML Transcription** - Layout-preserving transcription
- **Briefings** - Executive/technical/visual formats
- **Images** - PNG image files

### Processing Methods:
- **Inline** - Direct processing (<20MB)
- **File API** - Upload-based processing (>=20MB, up to 50MB)
- **Auto** - Automatic method selection

---

## 📊 Integration Points

### API Integration:
- **FastAPI** - REST API server
- **CLI** - Command-line interface
- **Library** - Python importable modules

### Gemini API Integration:
- **Generate Content** - Text generation
- **Generate Content Stream** - Streaming text
- **File API** - PDF upload and processing
- **Context Caching** - Cached context reuse
- **Batch API** - Async batch processing
- **URL Context Tool** - Direct URL access
- **Google Search Grounding** - Real-world context
- **Function Calling** - Tool integration
- **Structured Output** - JSON schema responses
- **Image Generation** - Text-to-image models

---

## 🏗️ Architecture Patterns

### Module Design:
- **Single Responsibility** - Each module has one clear purpose
- **Dependency Injection** - Constructor-based dependencies
- **Clear Contracts** - Well-defined input/output types
- **Direct & Minimal** - No unnecessary abstractions

### Data Flow:
1. **Input** → ArXiv query/paper source
2. **Fetch** → Download papers/PDFs
3. **Process** → Gemini API analysis
4. **Transform** → Structure output
5. **Store** → Save to files
6. **Serve** → API/CLI/Frontend

### Processing Flow:
1. **Single Paper** → Direct processing
2. **Multiple Papers** → Batch or combined processing
3. **PDF Processing** → File API upload → Wait → Generate
4. **Structured Output** → Schema validation → JSON

---

## 📝 Configuration Schema

### Environment Variables:
```bash
# Required
GEMINI_API_KEY=your_key_here

# Optional Feature Flags
USE_PDF_PROCESSING=true|false
USE_STRUCTURED_OUTPUT=true|false
USE_CONTEXT_CACHING=true|false
USE_GROUNDING=true|false
USE_URL_CONTEXT=true|false
AUTO_MODEL_SELECTION=true|false

# Configuration
DEFAULT_MODEL=gemini-2.5-flash
CACHE_TTL_SECONDS=3600
THINKING_BUDGET_DEFAULT=1000
THINKING_BUDGET_COMPLEX=5000
```

### Model Selection:
- **Fast** - `gemini-2.5-flash-lite` (high volume)
- **Balanced** - `gemini-2.5-flash` (default)
- **Deep** - `gemini-2.5-pro` (complex analysis)
- **Image** - `gemini-2.5-flash-image-preview` (image generation)

---

## 🔍 Work Efforts & Documentation

### Work Efforts (`_work_efforts_/`):
- `00.01_gemini_api_integration.md` - Comprehensive Gemini API integration
- `00.02_streaming_display_fix.md` - Streaming display fixes
- `00.03_devlog.md` - Development log
- `00.04_gemini_api_alignment.md` - API alignment review
- `00.05_loot_game_system.md` - Loot-based game system
- `00.06_image_generation_architecture.md` - Image generation architecture
- `00.07_documents_module_schemas.md` - Documents module schemas

---

## 📈 Version & Status

**Current Version:** Development
**Last Major Update:** 2025-11-01
**Status:** ✅ Active Development

**Recent Additions:**
- Documents module (2025-11-01)
- Image generation module (2025-11-01)
- Comprehensive test suites
- Work effort documentation system

---

## 🎯 Quick Reference

### Most Common Use Cases:
1. **Summarize papers** → `POST /api/summarize`
2. **Process PDF** → `POST /api/summarize-pdf`
3. **Structured output** → `POST /api/summarize-structured`
4. **Generate image** → `POST /api/generate-image`
5. **Process document** → `DocumentProcessor.process()`

### Key Classes:
- `ArxivSummarizer` - Main summarization engine
- `DocumentProcessor` - NEW: Document processing
- `ImageGenerator` - Image generation
- `PaperEmbeddings` - Semantic search
- `BatchPaperProcessor` - Batch processing
- `PaperChatSession` - Interactive chat

### Key Schemas:
- `PaperAnalysis` - Single paper analysis
- `ComparativeAnalysis` - Multi-paper comparison
- `DocumentInput` - Document source
- `DocumentProcessingResult` - Processing result

---

**This inventory is maintained as the codebase evolves.**
**For detailed documentation, see individual module docstrings and README.md**

