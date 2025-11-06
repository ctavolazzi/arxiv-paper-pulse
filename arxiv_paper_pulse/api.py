from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .core import ArxivSummarizer
from . import config
from .utils import get_total_available
from .chat import PaperChatSession
from .batch_processor import BatchPaperProcessor
from .embeddings import PaperEmbeddings
from .image_generator import ImageGenerator
from .self_playing_game import SelfDesigningGame
from .article_generator import generate_article
from .beehiiv_reader import BeehiivReader, get_stored_articles
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="ArXiv Paper Pulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Global summarizer instance (will be initialized per request with parameters)
summarizer_cache = {}

def get_summarizer(max_results=10, query="cat:cs.AI", model=None):
    """Get or create summarizer instance"""
    cache_key = f"{max_results}_{query}_{model or config.DEFAULT_MODEL}"
    if cache_key not in summarizer_cache:
        summarizer_cache[cache_key] = ArxivSummarizer(
            max_results=max_results,
            query=query,
            model=model or config.DEFAULT_MODEL
        )
    return summarizer_cache[cache_key]

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "ArXiv Paper Pulse API", "docs": "/docs"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    api_key_set = bool(config.GEMINI_API_KEY)
    return {
        "status": "healthy" if api_key_set else "warning",
        "gemini_api_key_set": api_key_set,
        "default_model": config.DEFAULT_MODEL
    }

@app.get("/api/papers")
async def get_papers():
    """Get latest paper summaries"""
    summary_dir = Path(config.SUMMARY_DIR)
    if not summary_dir.exists():
        return {"papers": []}

    files = sorted(summary_dir.glob("*_summary.json"), reverse=True)
    if not files:
        return {"papers": []}

    latest_file = files[0]
    with open(latest_file, "r") as f:
        data = json.load(f)
    return {"papers": data, "file": str(latest_file.name)}

@app.get("/api/briefing")
async def get_briefing():
    """Get latest briefing file content"""
    briefing_dir = Path(config.BRIEFING_DIR)
    if not briefing_dir.exists():
        raise HTTPException(status_code=404, detail="No briefing file found")

    files = sorted(briefing_dir.glob("*_briefing.md"), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No briefing file found")

    latest_file = files[0]
    with open(latest_file, "r") as f:
        content = f.read()
    return {"content": content, "file": str(latest_file.name)}

@app.post("/api/summarize")
async def summarize_papers(
    query: str = "cat:cs.AI",
    max_results: int = 10,
    force_pull: bool = False
):
    """Summarize papers from arXiv"""
    try:
        summarizer = get_summarizer(max_results=max_results, query=query)
        summaries = summarizer.summarize_papers(force_pull=force_pull)
        return {
            "status": "success",
            "count": len(summaries),
            "papers": summaries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/available")
async def get_available(query: str = "cat:cs.AI"):
    """Get total available papers for a query"""
    total = get_total_available(query)
    return {"query": query, "total_available": total}

@app.post("/api/search")
async def search_papers(
    query: str = "cat:cs.AI",
    max_results: int = 20
):
    """Search arXiv papers without full summarization (faster)"""
    try:
        summarizer = get_summarizer(max_results=max_results, query=query)
        # Just fetch raw data without summarization
        raw_data = summarizer.fetch_raw_data(force_pull=True)
        return {
            "status": "success",
            "count": len(raw_data),
            "papers": raw_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# New endpoints for advanced features

@app.post("/api/summarize-pdf")
async def summarize_pdf(
    paper_id: str,
    use_streaming: bool = False
):
    """Summarize paper from PDF"""
    try:
        summarizer = get_summarizer()
        paper = {"entry_id": paper_id, "url": f"https://arxiv.org/abs/{paper_id}"}
        summary = summarizer.gemini_summarize_from_pdf(paper, use_streaming=use_streaming)
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SummaryRequest(BaseModel):
    abstract: str
    model: Optional[str] = None

@app.post("/api/summarize-structured")
async def summarize_structured(request: SummaryRequest):
    """Get structured JSON summary"""
    try:
        summarizer = get_summarizer(model=request.model)
        analysis = summarizer.gemini_summarize(request.abstract, use_structured_output=True)
        return {"status": "success", "analysis": analysis.model_dump() if hasattr(analysis, 'model_dump') else str(analysis)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/summarize-stream")
async def summarize_stream(request: SummaryRequest):
    """Stream paper summary"""
    def generate():
        try:
            summarizer = get_summarizer(model=request.model)

            yield f"data: {json.dumps({'type': 'status', 'text': 'Starting analysis...'})}\n\n"

            stream = summarizer.gemini_summarize(request.abstract, use_streaming=True)

            for chunk in stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk.text})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/analyze-multiple")
async def analyze_multiple_papers(
    paper_ids: List[str],
    use_structured_output: bool = False
):
    """Analyze multiple papers together"""
    try:
        summarizer = get_summarizer()
        papers = [{"entry_id": pid, "url": f"https://arxiv.org/abs/{pid}"} for pid in paper_ids]
        result = summarizer.analyze_multiple_papers(papers, use_structured_output=use_structured_output)
        if use_structured_output:
            return {"status": "success", "analysis": result.model_dump() if hasattr(result, 'model_dump') else str(result)}
        return {"status": "success", "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/create")
async def create_chat_session(papers: List[dict], model: str = None):
    """Create a new chat session for papers"""
    try:
        session = PaperChatSession(papers, model=model)
        return {"status": "success", "session_id": str(id(session))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/ask")
async def chat_ask(
    session_id: str,
    question: str,
    use_streaming: bool = False
):
    """Ask a question in chat session"""
    # In production, store sessions properly
    # For now, this is a placeholder
    return {"status": "error", "message": "Session management not fully implemented"}


@app.post("/api/embeddings/generate")
async def generate_embeddings(papers: List[dict]):
    """Generate embeddings for papers"""
    try:
        embeddings_gen = PaperEmbeddings()
        result = embeddings_gen.generate_batch_embeddings(papers)
        return {"status": "success", "embeddings": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/embeddings/similar")
async def find_similar_papers(
    target_paper: dict,
    all_papers: List[dict],
    top_k: int = 5,
    threshold: float = 0.7
):
    """Find similar papers"""
    try:
        embeddings_gen = PaperEmbeddings()
        similar = embeddings_gen.find_similar_papers(target_paper, all_papers, top_k, threshold)
        return {"status": "success", "similar_papers": similar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch/submit")
async def submit_batch(papers: List[dict], model: str = None):
    """Submit papers for batch processing"""
    try:
        processor = BatchPaperProcessor(model=model)
        batch_id = processor.submit_batch(papers)
        return {"status": "success", "batch_id": batch_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get batch processing status"""
    try:
        processor = BatchPaperProcessor()
        status = processor.check_batch_status(batch_id)
        return {"status": "success", "batch_status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get batch processing results"""
    try:
        processor = BatchPaperProcessor()
        results = processor.get_batch_results(batch_id)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/url-context")
async def summarize_with_url_context(
    paper_url: str,
    use_grounding: bool = False
):
    """Summarize paper using URL context"""
    try:
        summarizer = get_summarizer()
        summary = summarizer.gemini_summarize_with_url_context(paper_url, use_grounding=use_grounding)
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-image")
async def generate_image(request: dict):
    """
    Generate an image from a text prompt using Gemini image generation.
    Layer 1: Image Generation Module
    """
    prompt = request.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        generator = ImageGenerator()

        # Generate filename from prompt (simple hash)
        import hashlib
        filename = hashlib.md5(prompt.encode()).hexdigest()[:12] + ".png"
        output_path = generator.output_dir / filename

        saved_path = generator.generate_and_save(prompt, str(output_path))

        return {
            "status": "success",
            "image_path": str(saved_path),
            "filename": filename,
            "output_directory": str(generator.output_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-article")
async def generate_article_endpoint(request: dict):
    """
    Generate article from arXiv paper.

    Request body:
    {
        "paper_id": "1706.03762" or "https://arxiv.org/abs/1706.03762",
        "output_format": "docx" or "md" (default: "docx")
    }
    """
    paper_id = request.get("paper_id")
    if not paper_id:
        raise HTTPException(status_code=400, detail="paper_id is required")

    output_format = request.get("output_format", "docx")
    if output_format not in ["docx", "md"]:
        raise HTTPException(status_code=400, detail="output_format must be 'docx' or 'md'")

    try:
        result_path = generate_article(paper_id, output_format=output_format)

        return {
            "success": True,
            "article_path": result_path,
            "paper_id": paper_id,
            "output_format": output_format,
            "file_exists": Path(result_path).exists(),
            "file_size": Path(result_path).stat().st_size if Path(result_path).exists() else 0
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/articles")
async def list_articles():
    """List all generated articles with metadata."""
    article_dir = Path(config.ARTICLE_OUTPUT_DIR)
    if not article_dir.exists():
        return {"articles": []}

    articles = []
    for article_file in sorted(article_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        articles.append({
            "name": article_file.name,
            "path": str(article_file),
            "size": article_file.stat().st_size,
            "modified": article_file.stat().st_mtime,
            "format": "md"
        })

    for article_file in sorted(article_dir.glob("*.docx"), key=lambda x: x.stat().st_mtime, reverse=True):
        articles.append({
            "name": article_file.name,
            "path": str(article_file),
            "size": article_file.stat().st_size,
            "modified": article_file.stat().st_mtime,
            "format": "docx"
        })

    # Sort by modified time
    articles.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "articles": articles,
        "count": len(articles)
    }


@app.get("/api/articles/{article_name}")
async def get_article(article_name: str):
    """Get specific article file."""
    article_dir = Path(config.ARTICLE_OUTPUT_DIR)
    article_path = article_dir / article_name

    if not article_path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    if article_path.suffix == ".md":
        return FileResponse(str(article_path), media_type="text/markdown")
    elif article_path.suffix == ".docx":
        return FileResponse(str(article_path), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")


# Beehiiv RSS Feed Endpoints
@app.post("/api/beehiiv/feeds")
async def fetch_beehiiv_feed(request: dict):
    """
    Fetch and return Beehiiv RSS feed data.
    
    Request body:
        feed_url: RSS feed URL
        force_refresh: If True, fetch fresh data without saving
    """
    try:
        feed_url = request.get("feed_url")
        if not feed_url:
            raise HTTPException(status_code=400, detail="feed_url is required")
        
        force_refresh = request.get("force_refresh", False)
        reader = BeehiivReader(feed_url)
        feed_data = reader.fetch_feed(force_refresh=force_refresh)
        return feed_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feed: {str(e)}")


@app.post("/api/beehiiv/feed-info")
async def get_beehiiv_feed_info(request: dict):
    """
    Get feed metadata without fetching full articles.
    
    Request body:
        feed_url: RSS feed URL
    """
    try:
        feed_url = request.get("feed_url")
        if not feed_url:
            raise HTTPException(status_code=400, detail="feed_url is required")
        
        reader = BeehiivReader(feed_url)
        feed_info = reader.get_feed_info()
        return feed_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feed info: {str(e)}")


@app.get("/api/beehiiv/articles")
async def get_beehiiv_articles(limit: Optional[int] = None):
    """
    Get all stored Beehiiv articles.
    
    Args:
        limit: Maximum number of articles to return
    """
    try:
        articles = get_stored_articles()
        
        if limit:
            articles = articles[:limit]
        
        return {
            "articles": articles,
            "count": len(articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching articles: {str(e)}")


@app.get("/api/beehiiv/articles/{article_id}")
async def get_beehiiv_article(article_id: str, feed_url: str = None):
    """
    Get a specific Beehiiv article by ID.
    
    Args:
        article_id: Article ID or link
        feed_url: Optional feed URL to search in
    """
    try:
        if feed_url:
            import urllib.parse
            decoded_url = urllib.parse.unquote(feed_url) if feed_url.startswith("http") else feed_url
            reader = BeehiivReader(decoded_url)
            article = reader.get_article_by_id(article_id)
        else:
            # Search in all stored articles
            articles = get_stored_articles()
            article = next((a for a in articles if a.get("id") == article_id or a.get("link") == article_id), None)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching article: {str(e)}")


@app.post("/api/generate-self-playing-game")
async def generate_self_playing_game(request: dict):
    """
    Generate a self-playing game from a prompt.
    Phase 1: Deterministic simulations only (no user input).
    """
    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        generator = SelfDesigningGame()

        # Generate game code
        design_result = generator.design_game(prompt)

        if not design_result['valid']:
            return {
                'success': False,
                'error': f"Code generation failed: {design_result['error']}",
                'raw_response': design_result.get('raw_response', ''),
                'code': design_result.get('code', ''),
                'response_time': design_result.get('response_time', 0)
            }

        # Execute game code
        execution_result = generator.execute_game(design_result['code'])

        # Save game and results
        game_dir = generator.save_game(
            design_result['code'],
            execution_result,
            Path(config.GAME_OUTPUT_DIR)
        )

        return {
            'success': execution_result['success'],
            'code': design_result['code'],
            'execution': {
                'success': execution_result['success'],
                'stdout': execution_result['stdout'],
                'stderr': execution_result['stderr'],
                'returncode': execution_result['returncode'],
                'execution_time': execution_result['execution_time']
            },
            'game_directory': str(game_dir),
            'response_time': design_result.get('response_time', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

