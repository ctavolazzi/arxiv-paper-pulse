# arxiv_paper_pulse/embeddings.py

from typing import List, Dict, Optional
import numpy as np
from google import genai
from . import config


class PaperEmbeddings:
    """
    Generate embeddings for papers to enable semantic search and clustering.
    """

    def __init__(self, model="models/text-embedding-004", api_key=None):
        """
        Initialize embeddings generator.

        Args:
            model: Embedding model to use
            api_key: API key (default from config)
        """
        self.model = model
        self.client = genai.Client(api_key=api_key or config.GEMINI_API_KEY)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            result = self.client.models.embed_content(
                model=self.model,
                content=text
            )
            return result.embedding if hasattr(result, 'embedding') else []
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def generate_paper_embedding(self, paper: Dict, use_abstract=True, use_title=True) -> List[float]:
        """
        Generate embedding for a paper using title and/or abstract.

        Args:
            paper: Paper dict with title and abstract
            use_abstract: Include abstract in embedding
            use_title: Include title in embedding

        Returns:
            Embedding vector
        """
        parts = []
        if use_title and paper.get("title"):
            parts.append(f"Title: {paper['title']}")
        if use_abstract and paper.get("abstract"):
            parts.append(f"Abstract: {paper['abstract']}")

        text = "\n".join(parts)
        return self.generate_embedding(text)

    def generate_batch_embeddings(self, papers: List[Dict]) -> Dict[str, List[float]]:
        """
        Generate embeddings for multiple papers.

        Args:
            papers: List of paper dicts

        Returns:
            Dict mapping paper IDs to embeddings
        """
        embeddings = {}
        for paper in papers:
            paper_id = paper.get("id") or paper.get("entry_id") or str(hash(paper.get("title", "")))
            embedding = self.generate_paper_embedding(paper)
            if embedding:
                embeddings[paper_id] = embedding

        return embeddings

    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between -1 and 1
        """
        if not embedding1 or not embedding2:
            return 0.0

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_similar_papers(self, target_paper: Dict, all_papers: List[Dict],
                           top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """
        Find papers similar to target paper.

        Args:
            target_paper: Paper to find similarities for
            all_papers: List of all papers to search
            top_k: Number of similar papers to return
            threshold: Minimum similarity threshold

        Returns:
            List of similar papers with similarity scores
        """
        target_embedding = self.generate_paper_embedding(target_paper)
        if not target_embedding:
            return []

        all_embeddings = self.generate_batch_embeddings(all_papers)

        similarities = []
        for paper in all_papers:
            paper_id = paper.get("id") or paper.get("entry_id") or str(hash(paper.get("title", "")))
            if paper_id in all_embeddings:
                similarity = self.cosine_similarity(target_embedding, all_embeddings[paper_id])
                if similarity >= threshold:
                    similarities.append({
                        "paper": paper,
                        "similarity": similarity
                    })

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return similarities[:top_k]

    def cluster_papers(self, papers: List[Dict], n_clusters: Optional[int] = None) -> Dict[int, List[Dict]]:
        """
        Cluster papers by similarity using embeddings.

        Args:
            papers: List of papers to cluster
            n_clusters: Number of clusters (auto-detect if None)

        Returns:
            Dict mapping cluster IDs to lists of papers
        """
        # Generate embeddings
        embeddings_dict = self.generate_batch_embeddings(papers)
        if not embeddings_dict:
            return {}

        # Simple K-means clustering (basic implementation)
        # For production, use sklearn or similar
        embeddings = list(embeddings_dict.values())
        paper_ids = list(embeddings_dict.keys())

        if len(embeddings) < 2:
            return {0: papers}

        # Auto-detect number of clusters
        if n_clusters is None:
            n_clusters = max(2, min(5, len(papers) // 3))

        # Simple clustering based on cosine similarity
        clusters = {}
        for i, paper_id in enumerate(paper_ids):
            paper = next((p for p in papers if (p.get("id") or p.get("entry_id")) == paper_id), None)
            if not paper:
                continue

            # Find closest cluster
            closest_cluster = 0
            max_similarity = -1

            for cluster_id, cluster_papers in clusters.items():
                # Average similarity to cluster
                similarities = [
                    self.cosine_similarity(
                        embeddings_dict[paper_id],
                        embeddings_dict.get(cluster_papers[0].get("id") or cluster_papers[0].get("entry_id"), [])
                    )
                    for cluster_papers in [cluster_papers]
                ]
                avg_similarity = np.mean(similarities) if similarities else 0
                if avg_similarity > max_similarity:
                    max_similarity = avg_similarity
                    closest_cluster = cluster_id

            if max_similarity < 0.5 and len(clusters) < n_clusters:
                # Create new cluster
                closest_cluster = len(clusters)

            if closest_cluster not in clusters:
                clusters[closest_cluster] = []
            clusters[closest_cluster].append(paper)

        return clusters

