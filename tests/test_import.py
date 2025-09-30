import arxiv
from arxiv_paper_pulse.utils import get_installed_ollama_models, get_total_available, get_unique_id

def test_import_arxiv():
    assert hasattr(arxiv, "Client")

def test_get_installed_ollama_models():
    models = get_installed_ollama_models()
    assert isinstance(models, list)

def test_get_total_available():
    # Provide a query; if results are available, the return should be an integer.
    total = get_total_available("cat:cs.AI")
    if total is not None:
        assert isinstance(total, int)

def test_get_unique_id():
    paper = {"entry_id": "123", "url": "http://example.com"}
    uid = get_unique_id(paper)
    assert uid == "123"
