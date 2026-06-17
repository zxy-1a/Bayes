from __future__ import annotations

from collections import Counter
from typing import Any

POSITIVE_EFFECTS = {"effective", "improved", "like", "continue"}
NEGATIVE_EFFECTS = {"ineffective", "no_effect", "dislike"}
ADVERSE_EFFECTS = {"adverse", "uncomfortable", "worse"}


class MemorySummarizer:
    def summarize(self, memory: dict[str, Any]) -> dict[str, Any]:
        feedback = memory.get("recent_feedback", []) or []
        positive = Counter()
        negative = Counter()
        adverse = Counter()

        for item in feedback:
            tea_name = str(item.get("tea_name") or "").strip()
            effect = str(item.get("effect") or "").strip()
            if not tea_name:
                continue
            if effect in POSITIVE_EFFECTS:
                positive[tea_name] += 1
            elif effect in NEGATIVE_EFFECTS:
                negative[tea_name] += 1
            elif effect in ADVERSE_EFFECTS or item.get("adverse_reaction"):
                adverse[tea_name] += 1

        return {
            "profile": memory.get("profile", {}),
            "preferred_teas": [tea for tea, _ in positive.most_common(5)],
            "ineffective_teas": [tea for tea, _ in negative.most_common(5)],
            "avoid_teas": [tea for tea, _ in adverse.most_common(5)],
            "recent_feedback_count": len(feedback),
        }
