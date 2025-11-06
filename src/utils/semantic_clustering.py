"""Semantic clustering of failure root causes using embeddings.

This module uses sentence transformers or LLM embeddings to group
semantically similar failures together, even if the exact wording differs.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class SemanticCluster:
    """A cluster of semantically similar failures."""

    cluster_id: int
    representative_text: str  # The most common or central text
    items: list[dict[str, Any]]  # Original items in this cluster
    total_count: int
    avg_similarity: float


class SemanticClusterer:
    """Cluster failure descriptions using semantic similarity."""

    def __init__(
        self,
        method: str = "sentence_transformers",
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.75,
    ) -> None:
        """Initialize the semantic clusterer.

        Args:
            method: Embedding method - "sentence_transformers", "openai", or "dspy"
            model_name: Model name for the chosen method
            similarity_threshold: Cosine similarity threshold for clustering (0-1)
        """
        self.method = method
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.model: Any = None

    def _load_sentence_transformer(self) -> None:
        """Load sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    def _get_embeddings_sentence_transformers(self, texts: list[str]) -> np.ndarray:
        """Get embeddings using sentence transformers.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings
        """
        if self.model is None:
            self._load_sentence_transformer()

        if self.model is not None:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings

        raise RuntimeError("Failed to load sentence transformer model")

    def _get_embeddings_openai(self, texts: list[str]) -> np.ndarray:
        """Get embeddings using OpenAI API.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings
        """
        try:
            import os

            import openai

            client = openai.OpenAI(api_key=os.getenv("LLM_API_KEY"))

            embeddings = []
            chunk_size = 100

            for i in range(0, len(texts), chunk_size):
                chunk = texts[i : i + chunk_size]
                response = client.embeddings.create(
                    input=chunk, model="text-embedding-3-small"
                )
                embeddings.extend([item.embedding for item in response.data])

            return np.array(embeddings)

        except ImportError:
            raise ImportError(
                "openai not installed. " "Install with: pip install openai"
            )

    def _get_embeddings_dspy(self, texts: list[str]) -> np.ndarray:
        """Get embeddings using DSPy's configured LLM.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings
        """
        raise NotImplementedError(
            "DSPy embedding support not yet implemented. "
            "Use 'sentence_transformers' or 'openai' method instead."
        )

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Get embeddings for texts using configured method.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings, shape (len(texts), embedding_dim)
        """
        if self.method == "sentence_transformers":
            return self._get_embeddings_sentence_transformers(texts)
        elif self.method == "openai":
            return self._get_embeddings_openai(texts)
        elif self.method == "dspy":
            return self._get_embeddings_dspy(texts)
        else:
            raise ValueError(f"Unknown embedding method: {self.method}")

    def cosine_similarity(self, embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity matrix.

        Args:
            embeddings: Array of embeddings, shape (n, embedding_dim)

        Returns:
            Similarity matrix, shape (n, n)
        """
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        similarity = np.dot(normalized, normalized.T)
        return similarity

    def cluster_failures(
        self, failures: list[dict[str, Any]], text_key: str = "root_cause"
    ) -> list[SemanticCluster]:
        """Cluster failures based on semantic similarity.

        Args:
            failures: List of failure dicts with text to cluster
            text_key: Key in failure dict containing text to cluster

        Returns:
            List of semantic clusters
        """
        if not failures:
            return []

        texts = [f.get(text_key, "") for f in failures]

        print(f"   Computing embeddings for {len(texts)} failures...")
        embeddings = self.get_embeddings(texts)

        print("   Computing similarity matrix...")
        similarity = self.cosine_similarity(embeddings)

        print(f"   Clustering with threshold {self.similarity_threshold}...")
        clusters: list[list[int]] = []
        assigned = set()

        for i in range(len(texts)):
            if i in assigned:
                continue

            cluster_indices = [i]
            assigned.add(i)

            for j in range(i + 1, len(texts)):
                if j in assigned:
                    continue

                if similarity[i, j] >= self.similarity_threshold:
                    cluster_indices.append(j)
                    assigned.add(j)

            clusters.append(cluster_indices)

        semantic_clusters = []
        for cluster_id, indices in enumerate(clusters):
            cluster_failures = [failures[i] for i in indices]

            texts_in_cluster = [failures[i].get(text_key, "") for i in indices]
            representative = texts_in_cluster[0]

            if len(indices) > 1:
                cluster_sims = []
                for i in range(len(indices)):
                    for j in range(i + 1, len(indices)):
                        cluster_sims.append(similarity[indices[i], indices[j]])
                avg_similarity = np.mean(cluster_sims)
            else:
                avg_similarity = 1.0

            total_count = sum(f.get("count", 1) for f in cluster_failures)

            semantic_clusters.append(
                SemanticCluster(
                    cluster_id=cluster_id,
                    representative_text=representative,
                    items=cluster_failures,
                    total_count=total_count,
                    avg_similarity=float(avg_similarity),
                )
            )

        semantic_clusters.sort(key=lambda c: c.total_count, reverse=True)

        print(
            f"   Created {len(semantic_clusters)} semantic clusters from {len(texts)} items"
        )

        return semantic_clusters


def cluster_root_causes(
    root_causes: list[dict[str, Any]],
    method: str = "sentence_transformers",
    similarity_threshold: float = 0.75,
) -> list[SemanticCluster]:
    """Convenience function to cluster root causes.

    Args:
        root_causes: List of dicts with 'root_cause' and 'count' keys
        method: Embedding method to use
        similarity_threshold: Clustering threshold

    Returns:
        List of semantic clusters
    """
    clusterer = SemanticClusterer(
        method=method,
        similarity_threshold=similarity_threshold,
    )

    return clusterer.cluster_failures(root_causes, text_key="root_cause")
