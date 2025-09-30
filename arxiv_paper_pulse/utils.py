from datetime import datetime
import subprocess
import feedparser
import urllib.parse

def get_unique_id(paper: dict) -> str:
    """
    Returns the unique identifier for a given paper dictionary.
    Checks for 'id', then 'entry_id', then 'url' keys in that order.
    """
    return paper.get("id") or paper.get("entry_id") or paper.get("url")

def parse_date(date_str: str) -> datetime:
    """
    Parses an ISO-formatted date string into a datetime object.
    If the string ends with 'Z', it is removed before parsing.
    """
    if date_str.endswith("Z"):
        date_str = date_str[:-1]
    return datetime.fromisoformat(date_str)

def get_total_available(query: str, sort_by="submittedDate", sort_order="descending", start=0, max_results=0):
    """
    Returns the total number of articles for a given arXiv query.
    """
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order
    }
    url = base_url + urllib.parse.urlencode(params)
    feed = feedparser.parse(url)
    if hasattr(feed, "feed") and "opensearch_totalresults" in feed.feed:
        return int(feed.feed.opensearch_totalresults)
    return None

def get_installed_ollama_models():
    """
    Returns a list of installed Ollama models by running 'ollama list'.
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        models = []
        for line in lines:
            if not line.strip() or line.startswith("NAME"):
                continue
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except subprocess.CalledProcessError:
        return []
