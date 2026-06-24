from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from tea_match.normalization.candidate_retriever import CandidateRetriever

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"
MOCK_ENV_VALUES = {"1", "true", "yes", "on"}

SYSTEM_PROMPT = """
你是中医茶饮推荐系统的语义归一模块。你的任务不是推荐茶饮，而是把用户表达映射到给定候选标准词。
必须遵守：
1. 只能从候选 candidates 中选择 canonical，不要发明新标准词。
2. 如果候选不合适，返回 null。
3. 输出严格 JSON，不要 Markdown。
4. related_terms 必须来自候选里的 related_terms，用于后续规则匹配。
""".strip()


class SemanticNormalizer:
    def __init__(self, candidate_retriever: CandidateRetriever | None = None):
        self.candidate_retriever = candidate_retriever or CandidateRetriever()

    def normalize(
        self,
        query: str,
        selected_symptoms: list[str],
        complaints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mappings = []
        canonical_terms: list[str] = []
        seen_terms = set()

        for mapping in self._build_selected_symptom_mappings(selected_symptoms):
            mappings.append(mapping)
            for term in mapping.get("related_terms", []) or []:
                term = str(term or "").strip()
                if term and term not in seen_terms:
                    canonical_terms.append(term)
                    seen_terms.add(term)

        inputs = self._collect_inputs(query, complaints)
        for text in inputs:
            candidates = self.candidate_retriever.retrieve(text, top_k=8)
            if not candidates:
                continue
            mapping = self._select_candidate(text, candidates)
            if not mapping:
                continue
            mappings.append(mapping)
            for term in mapping.get("related_terms", []) or []:
                term = str(term or "").strip()
                if term and term not in seen_terms:
                    canonical_terms.append(term)
                    seen_terms.add(term)

        return {"mappings": mappings, "canonical_terms": canonical_terms}

    def _build_selected_symptom_mappings(self, selected_symptoms: list[str]) -> list[dict[str, Any]]:
        mappings: list[dict[str, Any]] = []
        for symptom in selected_symptoms:
            text = str(symptom or "").strip()
            if not text:
                continue
            mappings.append(
                {
                    "raw": text,
                    "canonical": text,
                    "related_terms": [text],
                    "confidence": 1.0,
                    "method": "exact_selected_symptom",
                    "matched_alias": text,
                    "candidates": [
                        {
                            "canonical": text,
                            "related_terms": [text],
                            "score": 1.0,
                            "matched_alias": text,
                            "sources": ["selected_symptoms"],
                        }
                    ],
                }
            )
        return mappings

    def _collect_inputs(self, query: str, complaints: list[dict[str, Any]]) -> list[str]:
        items: list[str] = []
        has_free_text_complaints = False
        for complaint in complaints:
            if not isinstance(complaint, dict):
                continue
            source = complaint.get("source") or []
            if isinstance(source, str):
                source = [source]
            if "selected_symptoms" in source:
                continue
            has_free_text_complaints = True
            self._append_unique(items, complaint.get("raw", ""))
            terms = complaint.get("normalized_terms") or []
            if isinstance(terms, str):
                terms = [terms]
            for term in terms:
                self._append_unique(items, term)

        if not has_free_text_complaints:
            self._append_unique(items, query)
        return items

    def _select_candidate(self, text: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if self._should_use_llm():
            selected = self._select_with_llm(text, candidates)
            if selected:
                return selected
        return self._select_locally(text, candidates)

    def _select_locally(self, text: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        best = candidates[0]
        if float(best.get("score") or 0) < 0.55:
            return None
        return {
            "raw": text,
            "canonical": best["canonical"],
            "related_terms": best.get("related_terms", [best["canonical"]]),
            "confidence": round(float(best.get("score") or 0), 3),
            "method": "local_candidate_match",
            "matched_alias": best.get("matched_alias", ""),
            "candidates": compact_candidates(candidates[:5]),
        }

    def _select_with_llm(self, text: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        api_key = api_key_from_env()
        if not api_key:
            return None
        try:
            client = OpenAI(api_key=api_key, base_url=os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL))
            payload = {"raw": text, "candidates": compact_candidates(candidates[:8])}
            response = client.chat.completions.create(
                model=os.getenv("QWEN_NORMALIZER_MODEL", DEFAULT_MODEL),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(strip_code_fence(content))
            canonical = data.get("canonical")
            if not canonical:
                return None
            for candidate in candidates:
                if candidate.get("canonical") == canonical:
                    return {
                        "raw": text,
                        "canonical": canonical,
                        "related_terms": data.get("related_terms") or candidate.get("related_terms", [canonical]),
                        "confidence": float(data.get("confidence") or candidate.get("score") or 0),
                        "method": "llm_candidate_selection",
                        "matched_alias": candidate.get("matched_alias", ""),
                        "candidates": compact_candidates(candidates[:5]),
                    }
        except Exception:
            return None
        return None

    def _should_use_llm(self) -> bool:
        if os.getenv("USE_MOCK_UNDERSTANDING", "").lower() in MOCK_ENV_VALUES:
            return False
        if os.getenv("USE_LLM_NORMALIZATION", "").lower() in {"0", "false", "no", "off"}:
            return False
        return bool(api_key_from_env()) and OpenAI is not None

    @staticmethod
    def _append_unique(items: list[str], value: object) -> None:
        text = str(value or "").strip()
        if text and text not in items:
            items.append(text)


def compact_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "canonical": item.get("canonical"),
            "related_terms": item.get("related_terms", []),
            "score": item.get("score", 0),
            "matched_alias": item.get("matched_alias", ""),
            "sources": item.get("sources", []),
        }
        for item in candidates
    ]


def api_key_from_env() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text



