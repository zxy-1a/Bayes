from __future__ import annotations

from typing import Any


class RecommendationAdjuster:
    """Re-rank local recommendations with personal memory. It does not invent new products."""

    def adjust(self, recommendations: list[dict[str, Any]], memory_summary: dict[str, Any]) -> list[dict[str, Any]]:
        preferred = set(memory_summary.get("preferred_teas", []) or [])
        ineffective = set(memory_summary.get("ineffective_teas", []) or [])
        avoid = set(memory_summary.get("avoid_teas", []) or [])

        adjusted = []
        for rec in recommendations:
            rec = dict(rec)
            name = rec.get("name", "")
            stage_priority = int(rec.get("stage_priority", 9) or 9)
            stage_score = float(rec.get("stage_score", 0) or 0)
            score = (10 - stage_priority) * 1000 + stage_score + float(rec.get("match_count", 0)) * 0.1
            notes = []
            if name in preferred:
                score += 0.5
                notes.append("历史反馈较好")
            if name in ineffective:
                score -= 0.8
                notes.append("历史反馈效果一般")
            if name in avoid:
                score -= 2.0
                notes.append("历史反馈曾有不适，需谨慎")
            rec["memory_score"] = score
            rec["memory_notes"] = notes
            adjusted.append(rec)

        adjusted.sort(key=lambda item: item.get("memory_score", 0), reverse=True)
        for rank, rec in enumerate(adjusted, start=1):
            rec["rank"] = rank
            if rec.get("memory_notes"):
                rec["reason"] = rec.get("reason", "") + "；" + "、".join(rec["memory_notes"])
        return adjusted

