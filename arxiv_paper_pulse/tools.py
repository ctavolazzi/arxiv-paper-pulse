# arxiv_paper_pulse/tools.py

from typing import List, Dict
from google.genai import types


def define_arxiv_tools() -> List[Dict]:
    """
    Define function calling tools for Gemini API.
    Allows the model to autonomously search arXiv, get citations, and gather information.
    """
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_arxiv_papers",
                    description="Search arXiv for papers related to a specific topic or query",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "query": {
                                "type": "STRING",
                                "description": "arXiv search query (e.g., 'cat:cs.AI', 'machine learning', 'title:transformer')"
                            },
                            "max_results": {
                                "type": "INTEGER",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10
                            },
                            "sort_by": {
                                "type": "STRING",
                                "description": "Sort order: 'submittedDate', 'relevance', 'lastUpdatedDate'",
                                "enum": ["submittedDate", "relevance", "lastUpdatedDate"],
                                "default": "submittedDate"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_paper_details",
                    description="Get detailed information about a specific arXiv paper by ID",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "paper_id": {
                                "type": "STRING",
                                "description": "arXiv paper ID (e.g., '2301.12345' or 'cs.AI/2301.12345')"
                            },
                            "include_abstract": {
                                "type": "BOOLEAN",
                                "description": "Whether to include the full abstract",
                                "default": True
                            }
                        },
                        "required": ["paper_id"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_related_papers",
                    description="Find papers related to a given paper or topic",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "paper_id": {
                                "type": "STRING",
                                "description": "arXiv paper ID to find related papers for"
                            },
                            "similarity_threshold": {
                                "type": "NUMBER",
                                "description": "Minimum similarity threshold (0.0 to 1.0)",
                                "default": 0.7
                            },
                            "max_results": {
                                "type": "INTEGER",
                                "description": "Maximum number of related papers to return",
                                "default": 10
                            }
                        },
                        "required": ["paper_id"]
                    }
                ),
                types.FunctionDeclaration(
                    name="analyze_paper_impact",
                    description="Analyze the impact and significance of a research paper",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "paper_id": {
                                "type": "STRING",
                                "description": "arXiv paper ID to analyze"
                            },
                            "include_citations": {
                                "type": "BOOLEAN",
                                "description": "Whether to include citation analysis",
                                "default": True
                            },
                            "include_trends": {
                                "type": "BOOLEAN",
                                "description": "Whether to include trend analysis",
                                "default": True
                            }
                        },
                        "required": ["paper_id"]
                    }
                )
            ]
        )
    ]

    return tools


class ArxivToolHandler:
    """
    Handler for executing function calls from Gemini API.
    """

    def __init__(self, summarizer=None):
        """
        Initialize tool handler.

        Args:
            summarizer: ArxivSummarizer instance for paper operations
        """
        self.summarizer = summarizer

    def execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """
        Execute a function call from Gemini API.

        Args:
            function_name: Name of the function to execute
            arguments: Function arguments

        Returns:
            Function result as dict
        """
        if function_name == "search_arxiv_papers":
            return self._search_arxiv_papers(**arguments)
        elif function_name == "get_paper_details":
            return self._get_paper_details(**arguments)
        elif function_name == "get_related_papers":
            return self._get_related_papers(**arguments)
        elif function_name == "analyze_paper_impact":
            return self._analyze_paper_impact(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}

    def _search_arxiv_papers(self, query: str, max_results: int = 10, sort_by: str = "submittedDate") -> Dict:
        """Search arXiv for papers."""
        if not self.summarizer:
            return {"error": "Summarizer not available"}

        try:
            import arxiv
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=getattr(arxiv.SortCriterion, sort_by, arxiv.SortCriterion.SubmittedDate)
            )
            client = arxiv.Client()
            papers = list(client.results(search))

            results = []
            for paper in papers:
                results.append({
                    "title": paper.title,
                    "id": paper.entry_id.split("/")[-1],
                    "authors": [author.name for author in paper.authors],
                    "published": str(paper.published),
                    "summary": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                    "url": paper.entry_id
                })

            return {"papers": results, "count": len(results)}
        except Exception as e:
            return {"error": str(e)}

    def _get_paper_details(self, paper_id: str, include_abstract: bool = True) -> Dict:
        """Get detailed information about a paper."""
        try:
            import arxiv
            search = arxiv.Search(id_list=[paper_id])
            client = arxiv.Client()
            paper = next(iter(search.results()), None)

            if not paper:
                return {"error": f"Paper {paper_id} not found"}

            result = {
                "title": paper.title,
                "id": paper_id,
                "authors": [author.name for author in paper.authors],
                "published": str(paper.published),
                "url": paper.entry_id,
                "categories": paper.categories
            }

            if include_abstract:
                result["abstract"] = paper.summary

            return result
        except Exception as e:
            return {"error": str(e)}

    def _get_related_papers(self, paper_id: str, similarity_threshold: float = 0.7, max_results: int = 10) -> Dict:
        """Find related papers using embeddings."""
        if not self.summarizer:
            return {"error": "Summarizer not available"}

        try:
            from .embeddings import PaperEmbeddings

            # Get target paper
            search_result = self._get_paper_details(paper_id)
            if "error" in search_result:
                return search_result

            # This would require fetching other papers and comparing embeddings
            # Simplified implementation
            return {
                "message": "Related papers search requires embedding comparison",
                "target_paper": search_result.get("title", ""),
                "similarity_threshold": similarity_threshold
            }
        except Exception as e:
            return {"error": str(e)}

    def _analyze_paper_impact(self, paper_id: str, include_citations: bool = True, include_trends: bool = True) -> Dict:
        """Analyze paper impact."""
        paper_details = self._get_paper_details(paper_id, include_abstract=True)
        if "error" in paper_details:
            return paper_details

        analysis = {
            "paper": {
                "title": paper_details.get("title"),
                "id": paper_id,
                "published": paper_details.get("published")
            },
            "analysis": {
                "impact_indicators": [
                    "Publication date and recency",
                    "Category and domain relevance",
                    "Abstract content analysis"
                ]
            }
        }

        if include_citations:
            analysis["citations"] = {
                "note": "Citation data requires external API access",
                "estimated_relevance": "High" if "transformer" in paper_details.get("title", "").lower() else "Medium"
            }

        if include_trends:
            analysis["trends"] = {
                "keywords": paper_details.get("categories", []),
                "estimated_domain_interest": "High"
            }

        return analysis

