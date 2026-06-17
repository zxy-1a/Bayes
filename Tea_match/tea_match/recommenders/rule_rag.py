from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from tea_match.config import PROJECT_ROOT
from tea_match.qdrant_store import QdrantTeaKnowledgeRetriever
from tea_match.recommenders.first_step import FirstStepMatcher

TEA_SPLIT_RE = re.compile(r"[+锛嬨€?锛?锛?]+")


class RuleRagRecommender:
    """Final recommendation engine controlled by local rules and the local RAG store."""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.first_step_matcher = FirstStepMatcher()
        self.qdrant_retriever = QdrantTeaKnowledgeRetriever()

    def recommend(
        self,
        query: str,
        selected_symptoms: list[str],
        complaints: list[dict[str, Any]],
        semantic_terms: list[str] | None = None,
    ) -> dict[str, Any]:
        all_symptoms = self.collect_search_terms(complaints)
        organ_hint_terms = self.collect_organ_hint_terms(query, complaints, semantic_terms or [])
        for term in organ_hint_terms:
            if term not in all_symptoms:
                all_symptoms.append(term)
        for term in semantic_terms or []:
            term = str(term or "").strip()
            if term and term not in all_symptoms:
                all_symptoms.append(term)
        combined_query = " ".join([query, *selected_symptoms]).strip()
        all_teas: dict[str, dict[str, Any]] = {}

        first_step_matches = self.first_step_matcher.match(combined_query, all_symptoms)
        for match in first_step_matches:
            source = f"第一步症状初筛：{match.get('symptom', '')}"
            self.add_tea(
                all_teas,
                str(match.get("tea_name", "")),
                source,
                stage_priority=1,
                stage_score=float(match.get("stage_score") or 0),
                weight=1.0,
            )

        from step2_rule_matcher import match_step2_rules

        step2_matches = match_step2_rules(combined_query, all_symptoms)
        for rule in step2_matches:
            source = f"第二步组合规则：{rule.get('primary_conditions', '')}"
            trigger = rule.get("trigger_condition")
            if trigger:
                source = f"{source} + {trigger}"
            for tea_name in rule.get("recommended_teas", []):
                self.add_tea(
                    all_teas,
                    str(tea_name),
                    source,
                    stage_priority=2,
                    stage_score=80 - float(rule.get("priority") or 2),
                    weight=0.8,
                )

        from fallback_rule_matcher import match_fallback_rules

        fallback_matches = []
        all_fallback_matches = match_fallback_rules(combined_query, all_symptoms)
        if not step2_matches and not first_step_matches:
            fallback_matches = all_fallback_matches
            for rule in fallback_matches:
                source = f"第{rule.get('priority')}步兜底规则：{rule.get('condition', '')}"
                self.add_tea(
                    all_teas,
                    str(rule.get("tea_name", "")),
                    source,
                    stage_priority=3,
                    stage_score=60 - float(rule.get("priority") or 4),
                    weight=0.6,
                )
        else:
            fallback_matches = [
                rule
                for rule in all_fallback_matches
                if str(rule.get("fallback_type", "")) == "organ"
                and str(rule.get("tea_name", "")).strip()
                and str(rule.get("tea_name", "")).strip() not in all_teas
            ]
            for rule in fallback_matches:
                source = f"第四步五脏筛选：{rule.get('condition', '')}"
                self.add_tea(
                    all_teas,
                    str(rule.get("tea_name", "")),
                    source,
                    stage_priority=3,
                    stage_score=56 - float(rule.get("priority") or 4),
                    weight=0.35,
                )

        if not first_step_matches and not step2_matches and not fallback_matches:
            for symptom in all_symptoms:
                for tea_info in self.search_tea_with_details(symptom):
                    self.add_tea(
                        all_teas,
                        tea_info.get("name", ""),
                        symptom,
                        tea_info.get("details", ""),
                        stage_priority=4,
                        stage_score=20,
                        weight=0.2,
                    )

        limit = 5
        return {
            "symptoms": all_symptoms,
            "first_step_matches": first_step_matches,
            "step2_matches": step2_matches,
            "fallback_matches": fallback_matches,
            "top_recommendations": self.build_recommendations(all_teas, limit),
        }

    def collect_search_terms(self, complaints: list[dict[str, Any]]) -> list[str]:
        all_symptoms: list[str] = []
        seen = set()

        def append_term(term: str) -> None:
            term = str(term or "").strip()
            if term and term not in seen:
                all_symptoms.append(term)
                seen.add(term)

        for complaint in complaints:
            raw = str(complaint.get("raw") or "").strip()
            confidence = float(complaint.get("confidence") or 0)
            source_list = complaint.get("source") or []
            if isinstance(source_list, str):
                source_list = [source_list]
            is_selected = "selected_symptoms" in source_list

            if confidence >= 0.8 or is_selected:
                terms = complaint.get("normalized_terms") or [raw]
                if isinstance(terms, str):
                    terms = [terms]
                for term in terms:
                    append_term(str(term))
            elif raw:
                for symptom in self.run_disambiguate(raw):
                    append_term(symptom)

        return all_symptoms

    @staticmethod
    def collect_organ_hint_terms(query: str, complaints: list[dict[str, Any]], semantic_terms: list[str]) -> list[str]:
        combined = " ".join(
            [
                str(query or ""),
                *[str(item.get("raw") or "") for item in complaints if isinstance(item, dict)],
                *[str(term or "") for term in semantic_terms],
            ]
        )
        organ_terms: list[str] = []
        organ_rules = {
            "肝": ["肝", "肝火", "肝郁", "护肝"],
            "心": ["心", "心慌", "心烦", "胸闷"],
            "脾": ["脾", "胃", "脾胃", "消化"],
            "肺": ["肺", "呼吸", "气管", "咳嗽", "肺气"],
            "肾": ["肾", "肾虚", "肾亏", "肾气", "腰酸", "腰膝酸软", "夜尿", "尿频"],
        }
        for organ, hints in organ_rules.items():
            if any(hint and hint in combined for hint in hints):
                organ_terms.append(organ)
        return organ_terms

    def run_disambiguate(self, complaint: str) -> list[str]:
        result = subprocess.run(
            [sys.executable, "disambiguate_complaint.py", complaint, "--use-local", "--pretty"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            encoding="utf-8",
            errors="replace",
        )
        try:
            data = json.loads(result.stdout)
            if not data.get("is_vague"):
                return [complaint]
            inferred = data.get("inferred_symptoms")
            if isinstance(inferred, list) and inferred:
                return [str(item).strip() for item in inferred if str(item).strip()]

            from disambiguate_complaint import VAGUE_COMPLAINT_PATTERNS

            for pattern_config in VAGUE_COMPLAINT_PATTERNS.values():
                if any(keyword in complaint for keyword in pattern_config.get("keywords", [])):
                    defaults = pattern_config.get("default_normalized", [])
                    return [str(item).strip() for item in defaults if str(item).strip()] or [complaint]
            return [complaint]
        except Exception:
            return [complaint]

    def search_tea_with_details(self, symptom: str) -> list[dict[str, str]]:
        qdrant_hits = self.qdrant_retriever.search(symptom, limit=5)
        if qdrant_hits:
            return [{"name": str(item.get("name", "")), "details": str(item.get("details", ""))} for item in qdrant_hits]

        result = subprocess.run(
            [sys.executable, "search_vector_store.py", symptom],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            encoding="utf-8",
            errors="replace",
        )

        teas: list[dict[str, str]] = []
        current_tea = ""
        current_content: list[str] = []

        def append_current_tea() -> None:
            if not current_tea:
                return
            details = "\n".join(current_content)
            for tea in self.split_tea_names(current_tea):
                teas.append({"name": tea, "details": details})

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "tea=" in stripped and " type=" in stripped:
                append_current_tea()
                current_tea = stripped.split("tea=", 1)[1].split(" type=", 1)[0].strip()
                current_content = []
            elif current_tea and stripped and "score=" not in stripped and not stripped.startswith("=="):
                current_content.append(stripped)

        append_current_tea()
        return teas
    @staticmethod
    def split_tea_names(tea_text: str) -> list[str]:
        teas = []
        seen = set()
        for tea in TEA_SPLIT_RE.split(tea_text or ""):
            tea = tea.strip()
            if tea and tea not in seen:
                teas.append(tea)
                seen.add(tea)
        return teas

    @staticmethod
    def add_tea(
        all_teas: dict[str, dict[str, Any]],
        tea_name: str,
        source: str,
        details: str = "",
        stage_priority: int = 9,
        stage_score: float = 0,
        weight: float = 0,
    ) -> None:
        if not tea_name:
            return
        item = all_teas.setdefault(
            tea_name,
            {
                "count": 0,
                "sources": [],
                "details": details,
                "stage_priority": stage_priority,
                "stage_score": stage_score,
                "total_score": 0.0,
            },
        )
        item["count"] += 1
        item["total_score"] += weight
        if stage_priority < item.get("stage_priority", 9):
            item["stage_priority"] = stage_priority
            item["stage_score"] = stage_score
        elif stage_priority == item.get("stage_priority", 9):
            item["stage_score"] = max(float(item.get("stage_score", 0)), stage_score)
        if source and source not in item["sources"]:
            item["sources"].append(source)
        if details and not item.get("details"):
            item["details"] = details

    @staticmethod
    def build_recommendations(all_teas: dict[str, dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        sorted_teas = sorted(
            all_teas.items(),
            key=lambda item: (
                int(item[1].get("stage_priority", 9)) * -1,
                float(item[1].get("stage_score", 0)),
                float(item[1].get("total_score", 0)),
                int(item[1].get("count", 0)),
            ),
            reverse=True,
        )[:limit]
        recommendations: list[dict[str, Any]] = []
        for rank, (tea_name, tea_info) in enumerate(sorted_teas, start=1):
            sources = tea_info.get("sources", [])
            count = int(tea_info.get("count", 0))
            if not sources:
                reason = "与您的主诉匹配"
            elif len(sources) == 1:
                reason = f"与您的主诉「{sources[0]}」相匹配"
            elif len(sources) == 2:
                reason = f"与您的主诉「{sources[0]}」「{sources[1]}」相匹配"
            else:
                reason = f"与您的主诉「{sources[0]}」等 {len(sources)} 个方面相匹配"

            recommendations.append(
                {
                    "rank": rank,
                    "name": tea_name,
                    "match_count": count,
                    "reason": reason,
                    "match_symptoms": sources,
                    "stage_priority": tea_info.get("stage_priority", 9),
                    "stage_score": tea_info.get("stage_score", 0),
                }
            )
        return recommendations



