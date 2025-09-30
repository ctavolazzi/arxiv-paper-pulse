# arxiv_paper_pulse/models.py

from typing import Dict

class PaperSummary:
    def __init__(self, title: str, published: str, url: str, abstract: str, summary: str):
        self.title = title
        self.published = published
        self.url = url
        self.abstract = abstract
        self.summary = summary

    def to_dict(self) -> Dict:
        """Convert the object to a dictionary for JSON storage."""
        return {
            "title": self.title,
            "published": self.published,
            "url": self.url,
            "abstract": self.abstract,
            "summary": self.summary
        }

    @staticmethod
    def from_dict(data: Dict):
        """Recreate a PaperSummary object from a dictionary."""
        return PaperSummary(**data)
