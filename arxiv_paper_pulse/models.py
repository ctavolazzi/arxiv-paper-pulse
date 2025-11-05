# arxiv_paper_pulse/models.py

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


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


# Pydantic models for structured output with Gemini API

class Methodology(BaseModel):
    """Research methodology and approach details"""
    model_config = ConfigDict(extra='forbid')

    approach: str = Field(description="Primary research approach or methodology used")
    datasets: List[str] = Field(default_factory=list, description="Datasets used in the research")
    metrics: List[str] = Field(default_factory=list, description="Evaluation metrics or performance measures")
    experimental_setup: Optional[str] = Field(None, description="Details about experimental configuration")


class Results(BaseModel):
    """Key findings and experimental results"""
    model_config = ConfigDict(extra='forbid')

    key_findings: List[str] = Field(default_factory=list, description="Main discoveries or results")
    performance_metrics: List[str] = Field(default_factory=list, description="Quantitative performance measurements (e.g., 'Accuracy: 95%')")
    statistical_significance: Optional[str] = Field(None, description="Statistical significance or confidence levels")
    comparisons: List[str] = Field(default_factory=list, description="Comparisons with baseline or prior work")


class Contributions(BaseModel):
    """Research contributions and innovations"""
    model_config = ConfigDict(extra='forbid')

    theoretical_contributions: List[str] = Field(default_factory=list, description="Theoretical or conceptual advances")
    methodological_contributions: List[str] = Field(default_factory=list, description="Novel methods or techniques")
    practical_applications: List[str] = Field(default_factory=list, description="Real-world applications or use cases")


class PaperAnalysis(BaseModel):
    """Comprehensive structured analysis of a research paper"""
    model_config = ConfigDict(extra='forbid')

    problem_statement: str = Field(description="Core problem addressed and its significance")
    methodology: Methodology = Field(description="Research methodology details")
    results: Results = Field(description="Experimental results and findings")
    contributions: List[str] = Field(default_factory=list, description="Key contributions to the field")
    limitations: List[str] = Field(default_factory=list, description="Study limitations and constraints")
    future_work: List[str] = Field(default_factory=list, description="Suggested directions for future research")
    relevance_score: int = Field(ge=1, le=10, description="Relevance score from 1-10 based on impact and importance")
    key_insights: List[str] = Field(default_factory=list, description="Actionable insights for practitioners")
    related_domains: List[str] = Field(default_factory=list, description="Related research domains or fields")


class ComparativeAnalysis(BaseModel):
    """Structured output for comparing multiple papers"""
    model_config = ConfigDict(extra='forbid')

    common_themes: List[str] = Field(default_factory=list, description="Shared themes across papers")
    methodological_approaches: List[str] = Field(default_factory=list, description="Methods used by each paper (e.g., 'Paper A: CNN approach, Paper B: Transformer')")
    conflicting_findings: List[str] = Field(default_factory=list, description="Contradictions or disagreements between papers")
    complementary_insights: List[str] = Field(default_factory=list, description="How papers complement each other")
    emerging_patterns: List[str] = Field(default_factory=list, description="Trends or patterns across papers")
    research_gaps: List[str] = Field(default_factory=list, description="Identified gaps in current research")
