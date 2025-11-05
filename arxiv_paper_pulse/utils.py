from datetime import datetime
import subprocess
import feedparser
import urllib.parse
import time
import random
from functools import wraps
from typing import Callable, Any

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


def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0, exponential_base=2, jitter=True):
    """
    Decorator for retrying functions with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Check if error is retryable
                    if attempt < max_retries:
                        # Rate limit errors
                        if any(keyword in error_msg for keyword in ["rate", "quota", "429", "limit"]):
                            delay = min(
                                base_delay * (exponential_base ** attempt),
                                max_delay
                            )
                            if jitter:
                                delay += random.uniform(0, delay * 0.1)

                            print(f"Rate limit hit, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(delay)
                            continue

                        # Temporary errors
                        elif any(keyword in error_msg for keyword in ["timeout", "503", "502", "500", "temporary"]):
                            delay = base_delay * (exponential_base ** attempt)
                            if jitter:
                                delay += random.uniform(0, delay * 0.1)

                            print(f"Temporary error, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(delay)
                            continue

                    # Non-retryable errors or max retries reached
                    break

            # Re-raise last exception if all retries failed
            raise last_exception

        return wrapper
    return decorator


class RateLimiter:
    """
    Simple rate limiter for API calls.
    """

    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = False

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        if len(self.calls) >= self.max_calls:
            # Calculate wait time until oldest call expires
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call) + 0.1  # Small buffer

            if wait_time > 0:
                print(f"Rate limit reached, waiting {wait_time:.2f}s...")
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        # Record this call
        self.calls.append(time.time())
