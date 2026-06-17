from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from tea_match.config import PROJECT_ROOT

TERM_SPLIT_RE = re.compile(r"[、,，;；/|\s]+")
STRIP_RE = re.compile(r"[\s,，。.;；:：、！!？?（）()【】\[\]《》<>]+")


class FirstStepMatcher:
    """Match step-1 symptom screening rows before step-2 combination rules."""

    def __init__(self, path: Path | None = None):
        self.path = path or PROJECT_ROOT / "rag_output" / "tea_symptom_index.csv"

    def match(self, query: str, terms: Iterable[str]) -> list[dict[str, object]]:
        haystack_terms = [str(query or ""), *[str(term) for term in terms if term]]
        normalized_haystack = " ".join(norm_text(term) for term in haystack_terms if term)
        term_set = {norm_text(term) for term in haystack_terms if term}
        matches = []
        rows = self._rows()
        symptoms_with_direct_rows = {
            norm_text(row.get("symptom", ""))
            for row in rows
            if norm_text(row.get("symptom", "")) == norm_text(row.get("raw_symptom", ""))
        }

        for row in rows:
            symptom = str(row.get("symptom", "")).strip()
            tea_name = str(row.get("tea_name", "")).strip()
            raw_symptom = str(row.get("raw_symptom", "")).strip()
            if not symptom or not tea_name:
                continue

            aliases = term_variants(symptom)
            raw_terms = split_terms(raw_symptom)
            has_direct_row = norm_text(symptom) in symptoms_with_direct_rows
            is_grouped_row = len(raw_terms) > 1 or norm_text(raw_symptom) != norm_text(symptom)
            if has_direct_row and is_grouped_row:
                continue

            matched_alias = ""
            for alias in aliases:
                normalized_alias = norm_text(alias)
                if not normalized_alias:
                    continue
                if normalized_alias in term_set or normalized_alias in normalized_haystack:
                    matched_alias = alias
                    break
            if not matched_alias:
                continue

            raw_count = max(1, len(raw_terms) or 1)
            exact_raw_bonus = 30 if norm_text(raw_symptom) == norm_text(symptom) else 0
            exact_alias_bonus = 20 if norm_text(matched_alias) == norm_text(symptom) else 0
            specificity_score = 100 + exact_raw_bonus + exact_alias_bonus - raw_count
            matches.append(
                {
                    "symptom": symptom,
                    "tea_name": tea_name,
                    "course": row.get("course", ""),
                    "source_row": int(row.get("source_row") or 9999),
                    "raw_symptom": raw_symptom,
                    "matched_alias": matched_alias,
                    "stage_score": specificity_score,
                    "source": "step1_symptom_screening",
                }
            )

        matches.sort(key=lambda item: (item["stage_score"], -int(item["source_row"])), reverse=True)
        return matches

    def _rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))


def split_terms(value: object) -> list[str]:
    text = str(value or "").strip()
    return [part.strip() for part in TERM_SPLIT_RE.split(text) if part.strip()]


def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return STRIP_RE.sub("", text)


def term_variants(term: str) -> set[str]:
    term = str(term or "").strip()
    variants = {term} if term else set()
    if term.startswith("高") and len(term) > 1:
        variants.add(term[1:] + "高")
    if term.endswith("高") and len(term) > 1:
        variants.add("高" + term[:-1])
    if term.endswith("症") and len(term) > 2:
        variants.add(term[:-1])
    if term.endswith("病") and len(term) > 2:
        variants.add(term[:-1])
    return {variant for variant in variants if variant}

