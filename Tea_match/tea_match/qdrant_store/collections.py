from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CollectionDefinition:
    name: str
    vector_size: int
    distance: str = "Cosine"
    description: str = ""
    payload_schema: dict[str, str] | None = None

    def as_payload_schema(self) -> dict[str, Any]:
        return dict(self.payload_schema or {})


COLLECTION_DEFINITIONS: dict[str, CollectionDefinition] = {
    "symptom_aliases": CollectionDefinition(
        name="symptom_aliases",
        vector_size=1024,
        description="Maps colloquial complaints, western disease names, constitutions, and organ phrases to canonical TCM terms.",
        payload_schema={
            "canonical_term": "keyword",
            "alias": "text",
            "category": "keyword",
            "step_hint": "integer",
            "source": "keyword",
            "confidence": "float",
        },
    ),
    "tea_knowledge": CollectionDefinition(
        name="tea_knowledge",
        vector_size=1024,
        description="Stores tea efficacy, symptom coverage, constitution coverage, and organ coverage for semantic recall.",
        payload_schema={
            "tea_name": "keyword",
            "functions": "text[]",
            "applicable_symptoms": "keyword[]",
            "applicable_constitutions": "keyword[]",
            "applicable_organs": "keyword[]",
            "source": "keyword",
            "priority": "integer",
        },
    ),
    "rule_chunks": CollectionDefinition(
        name="rule_chunks",
        vector_size=1024,
        description="Stores chunks parsed from the Excel matching logic for semantic retrieval before local rule execution.",
        payload_schema={
            "rule_id": "keyword",
            "step": "integer",
            "rule_type": "keyword",
            "condition_text": "text",
            "trigger_terms": "keyword[]",
            "recommended_teas": "keyword[]",
            "priority": "integer",
            "source_excel_row": "integer",
        },
    ),
    "case_memory": CollectionDefinition(
        name="case_memory",
        vector_size=1024,
        description="Stores historical complaint summaries, button selections, recommendations, and user feedback for memory retrieval.",
        payload_schema={
            "user_id": "keyword",
            "query_text": "text",
            "selected_buttons": "keyword[]",
            "normalized_terms": "keyword[]",
            "recommended_teas": "keyword[]",
            "feedback": "keyword",
            "feedback_text": "text",
            "created_at": "datetime",
            "session_id": "keyword",
        },
    ),
}

COLLECTION_NAMES = tuple(COLLECTION_DEFINITIONS.keys())
