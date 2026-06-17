from __future__ import annotations

from typing import Any

from tea_match.memory.store import JsonMemoryStore


class MemoryRetriever:
    def __init__(self, store: JsonMemoryStore):
        self.store = store

    def retrieve(self, user_id: str, query: str, selected_symptoms: list[str] | None = None) -> dict[str, Any]:
        selected_symptoms = selected_symptoms or []
        return {
            "profile": self.store.get_profile(user_id),
            "recent_recommendations": self.store.list_recommendations(user_id, limit=8),
            "recent_feedback": self.store.list_feedback(user_id, limit=30),
            "current_query": query,
            "selected_symptoms": selected_symptoms,
        }
