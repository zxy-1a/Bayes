from __future__ import annotations

from typing import Any

from tea_match.agents.query_understanding import QueryUnderstandingAgent
from tea_match.memory.adjuster import RecommendationAdjuster
from tea_match.memory.retriever import MemoryRetriever
from tea_match.memory.store import JsonMemoryStore
from tea_match.memory.summarizer import MemorySummarizer
from tea_match.normalization.semantic_normalizer import SemanticNormalizer
from tea_match.recommenders.rule_rag import RuleRagRecommender


class RecommendationService:
    def __init__(self, store: JsonMemoryStore | None = None):
        self.store = store or JsonMemoryStore()
        self.query_agent = QueryUnderstandingAgent()
        self.memory_retriever = MemoryRetriever(self.store)
        self.memory_summarizer = MemorySummarizer()
        self.semantic_normalizer = SemanticNormalizer()
        self.rule_rag_recommender = RuleRagRecommender()
        self.adjuster = RecommendationAdjuster()

    def recommend(self, user_id: str, query: str, selected_symptoms: list[str]) -> dict[str, Any]:
        memory = self.memory_retriever.retrieve(user_id, query, selected_symptoms)
        memory_summary = self.memory_summarizer.summarize(memory)
        complaints = self.query_agent.understand(query, selected_symptoms, memory_summary)
        semantic_normalization = self.semantic_normalizer.normalize(query, selected_symptoms, complaints)

        if complaints:
            rule_result = self.rule_rag_recommender.recommend(
                query,
                selected_symptoms,
                complaints,
                semantic_terms=semantic_normalization.get("canonical_terms", []),
            )
            adjusted = self.adjuster.adjust(rule_result["top_recommendations"], memory_summary)
        else:
            rule_result = {"symptoms": [], "step2_matches": [], "fallback_matches": [], "top_recommendations": []}
            adjusted = []

        event = self.store.add_recommendation_event(
            user_id,
            {
                "query": query,
                "selected_symptoms": selected_symptoms,
                "complaints": complaints,
                "semantic_normalization": semantic_normalization,
                "symptoms": rule_result["symptoms"],
                "top_recommendations": adjusted,
                "memory_summary": memory_summary,
                "rule_hits": {
                    "step2": rule_result.get("step2_matches", []),
                    "fallback": rule_result.get("fallback_matches", []),
                },
            },
        )

        return {
            "success": True,
            "user_id": user_id,
            "recommendation_id": event["event_id"],
            "query": query,
            "selected_symptoms": selected_symptoms,
            "complaints": [
                {
                    "raw": c.get("raw", ""),
                    "confidence": c.get("confidence", 0),
                    "source": c.get("source", []),
                }
                for c in complaints
                if isinstance(c, dict)
            ],
            "semantic_normalization": semantic_normalization,
            "symptoms": rule_result["symptoms"],
            "memory_summary": memory_summary,
            "top_recommendations": adjusted,
        }

    def collect_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        tea_name: str,
        effect: str,
        notes: str = "",
        days_used: int | None = None,
        adverse_reaction: str = "",
    ) -> dict[str, Any]:
        event = self.store.add_feedback_event(
            user_id,
            {
                "recommendation_id": recommendation_id,
                "tea_name": tea_name,
                "effect": effect,
                "notes": notes,
                "days_used": days_used,
                "adverse_reaction": adverse_reaction,
            },
        )
        return {"success": True, "feedback_id": event["event_id"], "event": event}
