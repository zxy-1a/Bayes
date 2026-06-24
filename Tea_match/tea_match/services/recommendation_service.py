from __future__ import annotations

from typing import Any

from step2_rule_matcher import norm_text
from tea_match.agents.clarification_agent import CLARIFICATION_SKIP_VALUE, ClarificationAgent
from tea_match.agents.clarification_config import DOMAIN_CONFIGS
from tea_match.agents.query_understanding import QueryUnderstandingAgent
from tea_match.diagnosis import DiagnosisSummarizer
from tea_match.memory.adjuster import RecommendationAdjuster
from tea_match.memory.retriever import MemoryRetriever
from tea_match.memory.store import JsonMemoryStore
from tea_match.memory.summarizer import MemorySummarizer
from tea_match.normalization.semantic_normalizer import SemanticNormalizer
from tea_match.recommenders.rule_rag import RuleRagRecommender


SYMPTOM_FOCUS_LIMIT = 2
SYMPTOM_FOCUS_TEA_THRESHOLD = 3


class RecommendationService:
    def __init__(self, store: JsonMemoryStore | None = None):
        self.store = store or JsonMemoryStore()
        self.query_agent = QueryUnderstandingAgent()
        self.clarification_agent = ClarificationAgent()
        self.memory_retriever = MemoryRetriever(self.store)
        self.memory_summarizer = MemorySummarizer()
        self.semantic_normalizer = SemanticNormalizer()
        self.diagnosis_summarizer = DiagnosisSummarizer()
        self.rule_rag_recommender = RuleRagRecommender()
        self.adjuster = RecommendationAdjuster()

    def recommend(
        self,
        user_id: str,
        query: str,
        selected_symptoms: list[str],
        clarification_answers: list[str] | None = None,
        focus_symptoms: list[str] | None = None,
        tongue_result: dict[str, Any] | None = None,
        sublingual_result: dict[str, Any] | None = None,
        pulse_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clarification_answers = self._dedupe_texts(clarification_answers or [])
        selected_symptoms = self._dedupe_texts(selected_symptoms)
        focus_symptoms = self._dedupe_texts(focus_symptoms or [])[:SYMPTOM_FOCUS_LIMIT]
        skip_clarification = CLARIFICATION_SKIP_VALUE in clarification_answers
        effective_clarification_answers = [item for item in clarification_answers if item != CLARIFICATION_SKIP_VALUE]
        all_selected_symptoms = self._dedupe_texts([*selected_symptoms, *effective_clarification_answers])

        memory = self.memory_retriever.retrieve(user_id, query, all_selected_symptoms)
        memory_summary = self.memory_summarizer.summarize(memory)
        complaints = self.query_agent.understand(query, all_selected_symptoms, memory_summary)
        semantic_normalization = self.semantic_normalizer.normalize(query, all_selected_symptoms, complaints)
        semantic_normalization = self._apply_clarification_semantic_hints(semantic_normalization, all_selected_symptoms)

        diagnostic_summary = self.diagnosis_summarizer.summarize(
            tongue_result=tongue_result,
            sublingual_result=sublingual_result,
            pulse_result=pulse_result,
        )
        diagnostic_constitutions = [item.name for item in diagnostic_summary.constitution_hints]
        diagnostic_organs = [item.name for item in diagnostic_summary.organ_hints]
        diagnostic_symptom_hints = [item.name for item in diagnostic_summary.symptom_hints]

        should_recommend = bool(
            complaints
            or query.strip()
            or all_selected_symptoms
            or diagnostic_constitutions
            or diagnostic_organs
            or focus_symptoms
        )

        if should_recommend:
            focus_query = query
            focus_selected_symptoms = all_selected_symptoms
            if focus_symptoms:
                focus_query = ";".join(focus_symptoms)
                focus_selected_symptoms = self._dedupe_texts([*all_selected_symptoms, *focus_symptoms])
            rule_result = self.rule_rag_recommender.recommend(
                focus_query,
                focus_selected_symptoms,
                complaints,
                semantic_terms=semantic_normalization.get("canonical_terms", []),
                diagnostic_constitutions=diagnostic_constitutions,
                diagnostic_organs=diagnostic_organs,
                diagnostic_symptom_hints=diagnostic_symptom_hints,
            )
            grouped_rule_results = self._build_grouped_rule_results(
                query=query,
                selected_symptoms=selected_symptoms,
                clarification_answers=effective_clarification_answers,
                complaints=complaints,
                semantic_normalization=semantic_normalization,
                diagnostic_constitutions=diagnostic_constitutions,
                diagnostic_organs=diagnostic_organs,
                diagnostic_symptom_hints=diagnostic_symptom_hints,
            )
            if focus_symptoms:
                grouped_rule_results = self._filter_grouped_results_by_focus(grouped_rule_results, focus_symptoms)
            clarification = None
            if not skip_clarification:
                clarification = self._pick_group_clarification(grouped_rule_results)
                if clarification is None:
                    clarification = self.clarification_agent.maybe_clarify(rule_result, query, all_selected_symptoms)
            if clarification:
                return self._build_clarification_response(
                    user_id=user_id,
                    query=query,
                    selected_symptoms=selected_symptoms,
                    clarification_answers=effective_clarification_answers,
                    focus_symptoms=focus_symptoms,
                    all_selected_symptoms=all_selected_symptoms,
                    complaints=complaints,
                    semantic_normalization=semantic_normalization,
                    rule_result=rule_result,
                    memory_summary=memory_summary,
                    diagnostic_summary=diagnostic_summary.to_dict(),
                    clarification=clarification,
                )
            grouped_recommendations = self._build_grouped_recommendations(grouped_rule_results, memory_summary)
            adjusted = self._flatten_grouped_recommendations(grouped_recommendations)
            if not adjusted:
                adjusted = self.adjuster.adjust(rule_result["top_recommendations"], memory_summary)
                adjusted = self._apply_clarification_overrides(query, all_selected_symptoms, adjusted)
        else:
            rule_result = {
                "symptoms": [],
                "first_step_matches": [],
                "step2_matches": [],
                "fallback_matches": [],
                "top_recommendations": [],
                "candidate_tea_count": 0,
                "candidate_tea_names": [],
                "diagnostic_constitutions": diagnostic_constitutions,
                "diagnostic_organs": diagnostic_organs,
                "diagnostic_symptom_hints": diagnostic_symptom_hints,
            }
            grouped_recommendations = []
            adjusted = []

        diagnostic_summary_dict = diagnostic_summary.to_dict()
        event = self.store.add_recommendation_event(
            user_id,
            {
                "query": query,
                "selected_symptoms": selected_symptoms,
                "clarification_answers": clarification_answers,
                "focus_symptoms": focus_symptoms,
                "all_selected_symptoms": all_selected_symptoms,
                "complaints": complaints,
                "semantic_normalization": semantic_normalization,
                "symptoms": rule_result["symptoms"],
                "top_recommendations": adjusted,
                "grouped_recommendations": grouped_recommendations,
                "memory_summary": memory_summary,
                "diagnostic_summary": diagnostic_summary_dict,
                "rule_hits": {
                    "first_step": rule_result.get("first_step_matches", []),
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
            "clarification_answers": clarification_answers,
            "focus_symptoms": focus_symptoms,
            "all_selected_symptoms": all_selected_symptoms,
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
            "diagnostic_summary": diagnostic_summary_dict,
            "candidate_tea_count": rule_result.get("candidate_tea_count", len(adjusted)),
            "candidate_tea_names": rule_result.get("candidate_tea_names", []),
            "needs_clarification": False,
            "interaction_mode": "recommendation",
            "clarification": None,
            "grouped_recommendations": grouped_recommendations,
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

    def _build_grouped_rule_results(
        self,
        query: str,
        selected_symptoms: list[str],
        clarification_answers: list[str],
        complaints: list[dict[str, Any]],
        semantic_normalization: dict[str, Any],
        diagnostic_constitutions: list[str],
        diagnostic_organs: list[str],
        diagnostic_symptom_hints: list[str],
    ) -> list[dict[str, Any]]:
        groups = self._group_complaints(query, complaints)
        grouped_results: list[dict[str, Any]] = []
        for group in groups:
            rule_result = self.rule_rag_recommender.recommend(
                group["query"],
                group["selected_symptoms"],
                group["complaints"],
                semantic_terms=self._collect_group_semantic_terms(group, semantic_normalization),
                diagnostic_constitutions=diagnostic_constitutions,
                diagnostic_organs=diagnostic_organs,
                diagnostic_symptom_hints=diagnostic_symptom_hints,
            )
            grouped_results.append(
                {
                    **group,
                    "rule_result": rule_result,
                    "clarification_answers": clarification_answers,
                    "selected_symptoms_input": selected_symptoms,
                }
            )
        return grouped_results

    def _group_complaints(self, query: str, complaints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items = [item for item in complaints if isinstance(item, dict)]
        if not items and query.strip():
            items = [
                {
                    "order": 1,
                    "raw": query.strip(),
                    "normalized_terms": [query.strip()],
                    "source": ["free_text"],
                }
            ]

        groups_by_key: dict[str, dict[str, Any]] = {}
        ordered_keys: list[str] = []

        for item in items:
            raw = str(item.get("raw") or "").strip()
            normalized_terms = item.get("normalized_terms") or []
            if isinstance(normalized_terms, str):
                normalized_terms = [normalized_terms]
            normalized_terms = [str(term or "").strip() for term in normalized_terms if str(term or "").strip()]
            label_term = self._clean_group_term(raw) or (normalized_terms[0] if normalized_terms else "")
            if not label_term:
                continue
            group_key = self._classify_complaint_group(label_term, normalized_terms)
            group = groups_by_key.get(group_key)
            if group is None:
                group = {
                    "group_key": group_key,
                    "group_label": "",
                    "query": "",
                    "complaints": [],
                    "selected_symptoms": [],
                    "user_terms": [],
                    "normalized_terms": [],
                    "order": int(item.get("order") or len(ordered_keys) + 1),
                }
                groups_by_key[group_key] = group
                ordered_keys.append(group_key)
            group["complaints"].append(item)
            self._append_unique(group["user_terms"], label_term)
            for term in normalized_terms:
                self._append_unique(group["normalized_terms"], term)
            source_list = item.get("source") or []
            if isinstance(source_list, str):
                source_list = [source_list]
            if "selected_symptoms" in source_list:
                self._append_unique(group["selected_symptoms"], label_term)

        grouped_results = []
        for key in ordered_keys:
            group = groups_by_key[key]
            user_terms = group["user_terms"] or group["normalized_terms"] or [query.strip()]
            group["group_label"] = self._format_group_label(user_terms)
            group["query"] = "；".join(user_terms)
            grouped_results.append(group)
        return grouped_results

    @staticmethod
    def _clean_group_term(text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return ""
        prefixes = (
            "而且",
            "并且",
            "同时",
            "还有",
            "另外",
            "然后",
            "再就是",
            "以及",
        )
        changed = True
        while changed and value:
            changed = False
            for prefix in prefixes:
                if value.startswith(prefix):
                    value = value[len(prefix):].strip(" ，,、；;。")
                    changed = True
        return value.strip(" ，,、；;。")

    def _collect_group_semantic_terms(
        self,
        group: dict[str, Any],
        semantic_normalization: dict[str, Any],
    ) -> list[str]:
        terms: list[str] = []
        seen = set()
        raw_terms = {str(term or "").strip() for term in group.get("user_terms", []) if str(term or "").strip()}
        normalized_terms = {str(term or "").strip() for term in group.get("normalized_terms", []) if str(term or "").strip()}

        def add_term(value: object) -> None:
            text = str(value or "").strip()
            if text and text not in seen:
                terms.append(text)
                seen.add(text)

        for term in group.get("normalized_terms", []):
            add_term(term)

        for mapping in semantic_normalization.get("mappings", []) or []:
            if not isinstance(mapping, dict):
                continue
            raw = str(mapping.get("raw") or "").strip()
            canonical = str(mapping.get("canonical") or "").strip()
            related_terms = [str(term or "").strip() for term in (mapping.get("related_terms") or []) if str(term or "").strip()]
            if raw in raw_terms or raw in normalized_terms or canonical in normalized_terms or any(term in normalized_terms for term in related_terms):
                for term in related_terms or [canonical]:
                    add_term(term)
        return terms

    def _filter_grouped_results_by_focus(
        self,
        grouped_rule_results: list[dict[str, Any]],
        focus_symptoms: list[str],
    ) -> list[dict[str, Any]]:
        normalized_focus = {norm_text(item) for item in focus_symptoms if str(item or "").strip()}
        if not normalized_focus:
            return grouped_rule_results

        filtered: list[dict[str, Any]] = []
        for group in grouped_rule_results:
            candidates = [
                str(group.get("group_label") or ""),
                str(group.get("query") or ""),
                *[str(item or "") for item in group.get("user_terms", []) or []],
                *[str(item or "") for item in group.get("normalized_terms", []) or []],
                *[str(item.get("raw") or "") for item in group.get("complaints", []) or [] if isinstance(item, dict)],
            ]
            candidate_keys = {norm_text(item) for item in candidates if str(item or "").strip()}
            if normalized_focus & candidate_keys:
                filtered.append(group)

        return filtered or grouped_rule_results

    def _pick_group_clarification(self, grouped_rule_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        for group in sorted(grouped_rule_results, key=lambda item: int(item.get("order") or 999)):
            clarification = self.clarification_agent.maybe_clarify(
                group.get("rule_result", {}),
                str(group.get("query") or ""),
                [*list(group.get("selected_symptoms", []) or []), *list(group.get("clarification_answers", []) or [])],
            )
            if clarification:
                clarification["group_label"] = group.get("group_label", "")
                clarification["group_key"] = group.get("group_key", "")
                return clarification
        return None

    def _build_grouped_recommendations(
        self,
        grouped_rule_results: list[dict[str, Any]],
        memory_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        grouped_recommendations: list[dict[str, Any]] = []
        for group in grouped_rule_results:
            rule_result = group.get("rule_result", {})
            adjusted = self.adjuster.adjust(rule_result.get("top_recommendations", []), memory_summary)
            adjusted = self._apply_clarification_overrides(
                str(group.get("query") or ""),
                list(group.get("selected_symptoms", []) or []),
                adjusted,
            )
            if not adjusted:
                continue
            grouped_recommendations.append(
                {
                    "group_key": str(group.get("group_key") or ""),
                    "group_label": str(group.get("group_label") or ""),
                    "matched_terms": list(group.get("user_terms", []) or []),
                    "candidate_tea_count": int(rule_result.get("candidate_tea_count", len(adjusted))),
                    "recommendations": adjusted[:3],
                }
            )

        diabetic_group_label = r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2".encode("ascii").decode("unicode_escape")
        plain_group_label = r"\u89c6\u529b\u6a21\u7cca".encode("ascii").decode("unicode_escape")
        labels = {str(item.get("group_label") or "") for item in grouped_recommendations}
        if diabetic_group_label in labels:
            grouped_recommendations = [
                item for item in grouped_recommendations
                if str(item.get("group_label") or "") != plain_group_label
            ]
        return grouped_recommendations

    @staticmethod
    def _flatten_grouped_recommendations(grouped_recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flattened: list[dict[str, Any]] = []
        seen = set()
        for group in grouped_recommendations:
            label = str(group.get("group_label") or "")
            for item in group.get("recommendations", []) or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name or name in seen:
                    continue
                merged = dict(item)
                merged["group_label"] = label
                flattened.append(merged)
                seen.add(name)
        return flattened

    def _classify_complaint_group(self, raw: str, normalized_terms: list[str]) -> str:
        domain_name = self._detect_domain_name([raw, *normalized_terms])
        if domain_name:
            return f"domain::{domain_name}"
        for term in [*normalized_terms, raw]:
            group_name = self.rule_rag_recommender.classify_symptom_group(term)
            if group_name:
                return group_name
        return raw or "general"

    @staticmethod
    def _detect_domain_name(values: list[str]) -> str:
        joined = " ".join(norm_text(value) for value in values if str(value or "").strip())
        if not joined:
            return ""
        for domain_name, config in DOMAIN_CONFIGS.items():
            for alias in config.get("trigger_aliases", set()):
                alias_key = norm_text(alias)
                if alias_key and alias_key in joined:
                    return domain_name
            for option in config.get("options", []):
                value_key = norm_text(option.get("value", ""))
                if value_key and value_key in joined:
                    return domain_name
                for keyword in option.get("keywords", []):
                    keyword_key = norm_text(keyword)
                    if keyword_key and keyword_key in joined:
                        return domain_name
        return ""

    @staticmethod
    def _format_group_label(terms: list[str]) -> str:
        clean_terms = [str(term or "").strip() for term in terms if str(term or "").strip()]
        if not clean_terms:
            return "当前主诉"
        if len(clean_terms) == 1:
            return clean_terms[0]
        preview = "、".join(clean_terms[:2])
        if len(clean_terms) > 2:
            return preview + "等"
        return preview

    @staticmethod
    def _append_unique(values: list[str], value: object) -> None:
        text = str(value or "").strip()
        if text and text not in values:
            values.append(text)

    @staticmethod
    def _apply_clarification_semantic_hints(
        semantic_normalization: dict[str, Any],
        all_selected_symptoms: list[str],
    ) -> dict[str, Any]:
        hint_map = {
            "\u80be\u706b\u5927": ["\u5bb9\u6613\u4e0a\u706b"],
        }
        canonical_terms = list(semantic_normalization.get("canonical_terms", []) or [])
        for symptom in all_selected_symptoms:
            for hint in hint_map.get(str(symptom or "").strip(), []):
                if hint not in canonical_terms:
                    canonical_terms.append(hint)
        semantic_normalization["canonical_terms"] = canonical_terms
        return semantic_normalization

    @staticmethod
    def _apply_clarification_overrides(
        query: str,
        all_selected_symptoms: list[str],
        recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        respiratory_terms = [
            "\u611f\u5192",
            "\u6d41\u611f",
            "\u54bd\u708e",
            "\u652f\u6c14\u7ba1\u708e",
            "\u6162\u6027\u652f\u6c14\u7ba1\u708e",
            "\u80ba\u6c14\u80bf",
            "\u80ba\u7ed3\u8282",
            "\u80ba\u4e0d\u597d",
            "\u80ba\u529f\u80fd\u969c\u788d",
            "\u80ba\u529f\u80fd\u5dee",
            "\u547c\u5438\u4e0d\u597d",
            "\u547c\u5438\u9053\u75be\u75c5",
        ]
        text = " ".join([str(query or "").strip(), *[str(item or "").strip() for item in all_selected_symptoms if str(item or "").strip()]])
        is_respiratory = any(term in text for term in respiratory_terms)
        no_qi_token = "\u547c\u5438\u5e73\u7a33"
        yuanqi = "\u5143\u6c14\u8336"
        if is_respiratory and no_qi_token in all_selected_symptoms:
            return [item for item in recommendations if str(item.get("name") or "") != yuanqi]
        return recommendations

    @staticmethod
    def _dedupe_texts(values: list[str] | None) -> list[str]:
        deduped: list[str] = []
        seen = set()
        for item in values or []:
            text = str(item or "").strip()
            if text and text not in seen:
                deduped.append(text)
                seen.add(text)
        return deduped

    @staticmethod
    def _build_clarification_response(
        user_id: str,
        query: str,
        selected_symptoms: list[str],
        clarification_answers: list[str],
        focus_symptoms: list[str],
        all_selected_symptoms: list[str],
        complaints: list[dict[str, Any]],
        semantic_normalization: dict[str, Any],
        rule_result: dict[str, Any],
        memory_summary: dict[str, Any],
        diagnostic_summary: dict[str, Any],
        clarification: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "success": True,
            "user_id": user_id,
            "recommendation_id": "",
            "query": query,
            "selected_symptoms": selected_symptoms,
            "clarification_answers": clarification_answers,
            "focus_symptoms": focus_symptoms,
            "all_selected_symptoms": all_selected_symptoms,
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
            "symptoms": rule_result.get("symptoms", []),
            "memory_summary": memory_summary,
            "diagnostic_summary": diagnostic_summary,
            "candidate_tea_count": rule_result.get("candidate_tea_count", 0),
            "candidate_tea_names": rule_result.get("candidate_tea_names", []),
            "needs_clarification": True,
            "interaction_mode": "clarification",
            "clarification": clarification,
            "grouped_recommendations": [],
            "top_recommendations": [],
        }

