from __future__ import annotations

import os
from typing import Any

from .qdrant_client import get_qdrant_client, get_qdrant_settings, qdrant_is_configured

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


class QdrantTeaKnowledgeRetriever:
    def __init__(self, model_name: str | None = None, score_threshold: float = 0.2):
        self.model_name = model_name or os.getenv("QDRANT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.score_threshold = score_threshold
        self.settings = get_qdrant_settings()
        self.collection_name = self.settings.collection_name("tea_knowledge")
        self.enabled = self._resolve_enabled()
        self._embedder = None

    def _resolve_enabled(self) -> bool:
        env = os.getenv("USE_QDRANT_RETRIEVAL")
        if env is not None:
            return env.strip().lower() in {"1", "true", "yes", "on"}
        return qdrant_is_configured()

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for Qdrant retrieval. Run `pip install sentence-transformers`."
            ) from exc
        self._embedder = SentenceTransformer(self.model_name)
        return self._embedder

    def _embed_query(self, query: str) -> list[float]:
        model = self._get_embedder()
        embedding = model.encode([query], normalize_embeddings=True)
        return [float(value) for value in embedding[0]]

    @staticmethod
    def _format_details(payload: dict[str, Any]) -> str:
        symptoms = payload.get("applicable_symptoms") or []
        constitutions = payload.get("applicable_constitutions") or []
        organs = payload.get("applicable_organs") or []
        functions = payload.get("functions") or []
        parts = ["source: qdrant_tea_knowledge"]
        if symptoms:
            parts.append("applicable_symptoms: " + "、".join(str(item) for item in symptoms if str(item).strip()))
        if constitutions:
            parts.append("applicable_constitutions: " + "、".join(str(item) for item in constitutions if str(item).strip()))
        if organs:
            parts.append("applicable_organs: " + "、".join(str(item) for item in organs if str(item).strip()))
        if functions:
            parts.append("functions: " + "、".join(str(item) for item in functions if str(item).strip()))
        return "\n".join(parts)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.enabled or not str(query or "").strip():
            return []

        try:
            client = get_qdrant_client()
            query_vector = self._embed_query(query)
            hits = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=self.score_threshold,
            )
        except Exception:
            return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in hits:
            payload = dict(getattr(hit, "payload", {}) or {})
            tea_name = str(payload.get("tea_name") or "").strip()
            if not tea_name or tea_name in seen:
                continue
            seen.add(tea_name)
            results.append(
                {
                    "name": tea_name,
                    "details": self._format_details(payload),
                    "score": float(getattr(hit, "score", 0.0) or 0.0),
                    "payload": payload,
                }
            )
        return results
