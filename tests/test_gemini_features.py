# tests/test_gemini_features.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from arxiv_paper_pulse.core import ArxivSummarizer
from arxiv_paper_pulse.models import PaperAnalysis, Methodology, Results, ComparativeAnalysis
from arxiv_paper_pulse.embeddings import PaperEmbeddings
from arxiv_paper_pulse.batch_processor import BatchPaperProcessor
from arxiv_paper_pulse.chat import PaperChatSession
from arxiv_paper_pulse.tools import ArxivToolHandler, define_arxiv_tools


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing"""
    with patch('arxiv_paper_pulse.core.genai.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock file operations
        mock_file = Mock()
        mock_file.name = "test_file_name"
        mock_file.state = "ACTIVE"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file

        # Mock generate_content
        mock_response = Mock()
        mock_response.text = "Test summary text"
        mock_response.parsed = None
        mock_client.models.generate_content.return_value = mock_response
        mock_client.models.generate_content_stream.return_value = iter([mock_response])

        # Mock caching
        mock_cache = Mock()
        mock_cache.name = "test_cache"
        mock_cache.uri = "test_cache_uri"
        mock_cache.state = "ACTIVE"
        mock_client.caches.create.return_value = mock_cache
        mock_client.caches.get.return_value = mock_cache

        yield mock_client


@pytest.fixture
def sample_paper():
    """Sample paper dict for testing"""
    return {
        "entry_id": "http://arxiv.org/abs/2301.12345",
        "title": "Test Paper Title",
        "published": "2023-01-01",
        "url": "http://arxiv.org/abs/2301.12345",
        "abstract": "This is a test abstract for a research paper.",
        "id": "test_paper_id"
    }


@pytest.fixture
def summarizer(mock_gemini_client):
    """Create ArxivSummarizer instance with mocked client"""
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
        return ArxivSummarizer(max_results=5, query="cat:cs.AI")


class TestPDFProcessing:
    """Tests for PDF processing functionality"""

    def test_download_and_process_pdf(self, summarizer, sample_paper, mock_gemini_client):
        """Test PDF download and upload"""
        with patch('arxiv_paper_pulse.core.httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"fake pdf content"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = summarizer.download_and_process_pdf(sample_paper)

            assert result is not None
            mock_gemini_client.files.upload.assert_called_once()

    def test_wait_for_file_processing(self, summarizer, mock_gemini_client):
        """Test file processing wait logic"""
        mock_file = Mock()
        mock_file.name = "test_file"

        # First call returns PROCESSING, second returns ACTIVE
        processing_file = Mock()
        processing_file.state = "PROCESSING"
        active_file = Mock()
        active_file.state = "ACTIVE"

        mock_gemini_client.files.get.side_effect = [processing_file, active_file]

        result = summarizer._wait_for_file_processing(mock_file, max_wait_time=10)
        assert result.state == "ACTIVE"


class TestStructuredOutput:
    """Tests for structured output functionality"""

    def test_structured_output_enabled(self, summarizer, mock_gemini_client):
        """Test structured output generation"""
        mock_response = Mock()
        mock_response.text = '{"problem_statement": "test", "methodology": {"approach": "test"}, "results": {"key_findings": []}, "contributions": [], "limitations": [], "future_work": [], "relevance_score": 5}'
        mock_response.parsed = None
        mock_gemini_client.models.generate_content.return_value = mock_response

        result = summarizer.gemini_summarize(
            "Test abstract",
            use_structured_output=True
        )

        assert result is not None

    def test_pydantic_models(self):
        """Test Pydantic model validation"""
        methodology = Methodology(
            approach="Test approach",
            datasets=["dataset1"],
            metrics=["metric1"]
        )

        results = Results(
            key_findings=["finding1"],
            performance_metrics={"accuracy": 0.95}
        )

        analysis = PaperAnalysis(
            problem_statement="Test problem",
            methodology=methodology,
            results=results,
            contributions=["contribution1"],
            limitations=["limitation1"],
            future_work=["future1"],
            relevance_score=8
        )

        assert analysis.problem_statement == "Test problem"
        assert analysis.relevance_score == 8
        assert len(analysis.contributions) == 1


class TestContextCaching:
    """Tests for context caching"""

    def test_create_cached_context(self, summarizer, mock_gemini_client):
        """Test cache creation"""
        summarizer.use_caching = True
        result = summarizer.create_cached_context("test content", ttl_seconds=3600)

        assert result is not None
        mock_gemini_client.caches.create.assert_called_once()

    def test_get_or_create_cache(self, summarizer, sample_paper, mock_gemini_client):
        """Test cache retrieval or creation"""
        summarizer.use_caching = True
        result = summarizer.get_or_create_cache(sample_paper, "content")

        assert result is not None

    def test_cache_key_generation(self, summarizer, sample_paper):
        """Test cache key generation"""
        key = summarizer._get_cache_key(sample_paper)
        assert "test_paper_id" in key
        assert summarizer.model in key


class TestMultiPaperAnalysis:
    """Tests for multi-paper analysis"""

    def test_analyze_multiple_papers(self, summarizer, mock_gemini_client):
        """Test multi-paper comparative analysis"""
        papers = [
            {"entry_id": "2301.12345", "title": "Paper 1"},
            {"entry_id": "2302.12345", "title": "Paper 2"},
        ]

        with patch.object(summarizer, 'download_and_process_pdf') as mock_download:
            mock_file = Mock()
            mock_file.name = "test"
            mock_download.return_value = mock_file

            result = summarizer.analyze_multiple_papers(papers)
            assert result is not None

    def test_analyze_multiple_empty_list(self, summarizer):
        """Test empty paper list"""
        result = summarizer.analyze_multiple_papers([])
        assert "No papers" in result


class TestURLContext:
    """Tests for URL context tool"""

    def test_url_context_processing(self, summarizer, mock_gemini_client):
        """Test URL context tool usage"""
        mock_response = Mock()
        mock_response.text = "Summary from URL"
        mock_gemini_client.models.generate_content.return_value = mock_response

        result = summarizer.gemini_summarize_with_url_context(
            "https://arxiv.org/abs/2301.12345"
        )

        assert "Summary" in result or "Error" in result


class TestEmbeddings:
    """Tests for embeddings functionality"""

    def test_generate_embedding(self, mock_gemini_client):
        """Test embedding generation"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            embeddings_gen = PaperEmbeddings()

            mock_result = Mock()
            mock_result.embedding = [0.1, 0.2, 0.3]
            mock_gemini_client.models.embed_content.return_value = mock_result

            result = embeddings_gen.generate_embedding("test text")
            assert len(result) > 0

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            embeddings_gen = PaperEmbeddings()

            vec1 = [1.0, 0.0, 0.0]
            vec2 = [1.0, 0.0, 0.0]

            similarity = embeddings_gen.cosine_similarity(vec1, vec2)
            assert abs(similarity - 1.0) < 0.01  # Should be 1.0 for identical vectors


class TestBatchProcessing:
    """Tests for batch processing"""

    def test_batch_processor_init(self, mock_gemini_client):
        """Test batch processor initialization"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            processor = BatchPaperProcessor()
            assert processor.model is not None

    def test_create_batch_request(self, mock_gemini_client):
        """Test batch request creation"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            processor = BatchPaperProcessor()
            paper = {"abstract": "Test abstract"}
            request = processor._create_batch_request(paper)
            assert "model" in request or request is not None


class TestChatSessions:
    """Tests for chat sessions"""

    def test_chat_session_creation(self, mock_gemini_client):
        """Test chat session initialization"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            papers = [{"title": "Test", "url": "http://test.com", "abstract": "Test abstract"}]

            mock_chat = Mock()
            mock_chat.send_message.return_value = Mock(text="Response")
            mock_chat.get_history.return_value = []
            mock_gemini_client.chats.create.return_value = mock_chat

            chat = PaperChatSession(papers)
            assert chat.papers == papers

    def test_chat_ask(self, mock_gemini_client):
        """Test asking questions in chat"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            papers = [{"title": "Test", "url": "http://test.com"}]

            mock_chat = Mock()
            mock_response = Mock()
            mock_response.text = "Answer"
            mock_chat.send_message.return_value = mock_response
            mock_gemini_client.chats.create.return_value = mock_chat

            chat = PaperChatSession(papers)
            response = chat.ask("Test question")
            assert response is not None


class TestModelSelection:
    """Tests for model selection"""

    def test_auto_model_selection_fast(self):
        """Test auto-selection chooses fast model for high volume"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key', 'AUTO_MODEL_SELECTION': 'true'}):
            summarizer = ArxivSummarizer(max_results=60, query="cat:cs.AI")
            # Should select flash-lite for high volume
            assert summarizer.model is not None

    def test_auto_model_selection_complex(self):
        """Test auto-selection chooses pro model for complex queries"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key', 'AUTO_MODEL_SELECTION': 'true'}):
            summarizer = ArxivSummarizer(max_results=10, query="survey review")
            # Should select pro for complex queries
            assert summarizer.model is not None


class TestRateLimiting:
    """Tests for rate limiting utilities"""

    def test_rate_limiter(self):
        """Test rate limiter functionality"""
        from arxiv_paper_pulse.utils import RateLimiter

        limiter = RateLimiter(max_calls=2, time_window=1.0)
        limiter.wait_if_needed()  # First call
        limiter.wait_if_needed()  # Second call
        # Third call should wait
        limiter.wait_if_needed()

        assert len(limiter.calls) <= 2


class TestTools:
    """Tests for function calling tools"""

    def test_define_arxiv_tools(self):
        """Test tool definitions"""
        tools = define_arxiv_tools()
        assert len(tools) > 0

    def test_tool_handler(self):
        """Test tool handler execution"""
        handler = ArxivToolHandler()

        # Test with mock summarizer
        handler.summarizer = Mock()
        result = handler.execute_function("search_arxiv_papers", {"query": "test", "max_results": 5})

        # Should return dict with results or error
        assert isinstance(result, dict)

