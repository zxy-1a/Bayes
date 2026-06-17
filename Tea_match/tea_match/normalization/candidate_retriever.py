from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from tea_match.config import PROJECT_ROOT

TERM_SPLIT_RE = re.compile(r"[、，,；;：:|\s]+")
STRIP_RE = re.compile(r"[\s,，、；;：:。.!！？?（）()\[\]【】<>《》]+")


@dataclass
class CandidateTerm:
    canonical: str
    aliases: set[str] = field(default_factory=set)
    related_terms: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    priority: int = 5

    def to_dict(self, score: float = 0.0, matched_alias: str = "") -> dict[str, Any]:
        return {
            "canonical": self.canonical,
            "aliases": sorted(self.aliases),
            "related_terms": sorted(self.related_terms or {self.canonical}),
            "sources": sorted(self.sources),
            "priority": self.priority,
            "score": score,
            "matched_alias": matched_alias,
        }


class CandidateRetriever:
    """Build and search canonical terms that can actually hit local rules/RAG."""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.rag_dir = project_root / "rag_output"
        self._candidates: dict[str, CandidateTerm] | None = None

    def retrieve(self, text: str, top_k: int = 8, min_score: float = 0.35) -> list[dict[str, Any]]:
        text = str(text or "").strip()
        if not text:
            return []
        candidates = self.load_candidates()
        scored = []
        for candidate in candidates.values():
            score, matched_alias = self._score(text, candidate)
            if score < min_score:
                continue
            scored.append(candidate.to_dict(score=score, matched_alias=matched_alias))
        scored.sort(key=lambda item: (item["score"], -item["priority"]), reverse=True)
        return scored[:top_k]

    def load_candidates(self) -> dict[str, CandidateTerm]:
        if self._candidates is not None:
            return self._candidates
        candidates: dict[str, CandidateTerm] = {}
        self._load_step2_rules(candidates)
        self._load_fallback_rules(candidates)
        self._load_tea_symptom_index(candidates)
        self._load_step2_aliases(candidates)
        self._load_symptom_alias_dictionary(candidates)
        self._add_generated_aliases(candidates)
        self._candidates = candidates
        return candidates

    def _ensure(
        self,
        candidates: dict[str, CandidateTerm],
        canonical: str,
        source: str,
        priority: int = 5,
        related_terms: list[str] | None = None,
    ) -> CandidateTerm | None:
        canonical = str(canonical or "").strip()
        if not canonical:
            return None
        item = candidates.get(canonical)
        if item is None:
            item = CandidateTerm(canonical=canonical)
            candidates[canonical] = item
        item.aliases.add(canonical)
        item.related_terms.add(canonical)
        item.sources.add(source)
        item.priority = min(item.priority, priority)
        for term in related_terms or []:
            term = str(term or "").strip()
            if term:
                item.related_terms.add(term)
        return item

    def _load_step2_rules(self, candidates: dict[str, CandidateTerm]) -> None:
        path = self.rag_dir / "step2_combo_rules.csv"
        for row in self._read_csv(path):
            primary_terms = split_terms(row.get("primary_conditions", ""))
            trigger_terms = split_terms(row.get("trigger_condition", ""))
            priority = int(row.get("priority") or 2)
            if not trigger_terms:
                for term in primary_terms:
                    self._ensure(candidates, term, "step2_primary", priority, [term])
                continue
            for term in trigger_terms:
                related = list(dict.fromkeys([*matching_primary_terms(term, primary_terms), term]))
                self._ensure(candidates, term, "step2_trigger", priority, related)
            default_related = trigger_terms if is_default_trigger(trigger_terms) else []
            for term in primary_terms:
                self._ensure(candidates, term, "step2_primary", priority, list(dict.fromkeys([term, *default_related])))

    def _load_fallback_rules(self, candidates: dict[str, CandidateTerm]) -> None:
        for filename, source in [("step3_constitution_fallback.csv", "step3_fallback"), ("step4_organ_fallback.csv", "step4_fallback")]:
            for row in self._read_csv(self.rag_dir / filename):
                condition = row.get("fallback_condition", "")
                priority = int(row.get("priority") or 5)
                self._ensure(candidates, condition, source, priority, [condition])

    def _load_tea_symptom_index(self, candidates: dict[str, CandidateTerm]) -> None:
        for row in self._read_csv(self.rag_dir / "tea_symptom_index.csv"):
            symptom = row.get("symptom", "")
            self._ensure(candidates, symptom, "tea_symptom_index", int(row.get("source_row") or 9), [symptom])

    def _load_step2_aliases(self, candidates: dict[str, CandidateTerm]) -> None:
        for row in self._read_csv(self.rag_dir / "step2_oral_aliases.csv"):
            condition = str(row.get("condition", "")).strip()
            item = candidates.get(condition)
            if item is None:
                continue
            raw_aliases = str(row.get("aliases", ""))
            for alias in split_terms(raw_aliases.replace("|", "、")):
                if is_forbidden_alias(condition, alias):
                    continue
                item.aliases.add(alias)
            item.sources.add("step2_oral_aliases")

    def _load_symptom_alias_dictionary(self, candidates: dict[str, CandidateTerm]) -> None:
        path = self.rag_dir / "symptom_alias_dictionary.csv"
        for row in self._read_csv(path):
            alias = str(row.get("alias", "")).strip()
            canonical = str(row.get("canonical", "")).strip()
            source = str(row.get("source", "")).strip()
            if not alias or not canonical:
                continue
            # Keep this dictionary one-way: alias -> canonical.
            if canonical in candidates and is_reasonable_alias(alias, canonical, source):
                candidates[canonical].aliases.add(alias)
                candidates[canonical].sources.add("symptom_alias_dictionary")

    def _add_generated_aliases(self, candidates: dict[str, CandidateTerm]) -> None:
        for item in candidates.values():
            aliases = set(item.aliases)
            for term in list(aliases):
                if term.endswith("火大") and len(term) > 2:
                    prefix = term[:-2]
                    item.aliases.update({f"{prefix}热", f"{prefix}火", f"{prefix}火旺", f"{prefix}里有火"})
                    item.sources.add("generated_fire_heat_aliases")
                if term.endswith("火旺") and len(term) > 2:
                    prefix = term[:-2]
                    item.aliases.update({f"{prefix}热", f"{prefix}火", f"{prefix}火大"})
                    item.sources.add("generated_fire_heat_aliases")
                if "上火" in term:
                    item.aliases.update({"火气重", "火气大", "老上火", "体内有火"})
                    item.sources.add("generated_fire_heat_aliases")
                item.aliases.update(generate_oral_aliases(term))
            if len(item.aliases) > len(aliases):
                item.sources.add("generated_oral_aliases")

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _score(self, text: str, candidate: CandidateTerm) -> tuple[float, str]:
        normalized_text = norm_text(text)
        best_score = 0.0
        best_alias = ""
        for alias in candidate.aliases:
            normalized_alias = norm_text(alias)
            if not normalized_alias:
                continue
            if normalized_alias == normalized_text:
                return 1.0, alias
            if normalized_alias in normalized_text or normalized_text in normalized_alias:
                score = 0.92 if len(normalized_text) >= 2 else 0.75
            else:
                seq_score = SequenceMatcher(None, normalized_text, normalized_alias).ratio()
                overlap = char_overlap(normalized_text, normalized_alias)
                score = max(seq_score, overlap)
            if score > best_score:
                best_score = score
                best_alias = alias
        return best_score, best_alias


def is_default_trigger(trigger_terms: list[str]) -> bool:
    joined = " ".join(trigger_terms)
    return any(word in joined for word in ["轻症", "轻微", "普通", "一般", "初期", "早期"])


def is_forbidden_alias(condition: str, alias: str) -> bool:
    condition_key = norm_text(condition)
    alias_key = norm_text(alias)
    if condition_key == norm_text("血糖高") and alias_key in {
        norm_text("糖尿病"),
        norm_text("糖尿病史"),
        norm_text("有糖尿病史"),
        norm_text("有糖尿病"),
    }:
        return True
    return False


def is_reasonable_alias(alias: str, canonical: str, source: str) -> bool:
    alias_key = norm_text(alias)
    canonical_key = norm_text(canonical)
    if not alias_key or not canonical_key:
        return False
    if alias_key == canonical_key:
        return True
    if source.endswith("_self"):
        return False
    if len(alias_key) == 1 or len(canonical_key) == 1:
        return False
    if alias_key in canonical_key or canonical_key in alias_key:
        return True
    overlap = char_overlap(alias_key, canonical_key)
    seq_score = SequenceMatcher(None, alias_key, canonical_key).ratio()
    return max(overlap, seq_score) >= 0.6


def matching_primary_terms(trigger: str, primary_terms: list[str]) -> list[str]:
    trigger = str(trigger or "").strip()
    matches = []
    for primary in primary_terms:
        primary = str(primary or "").strip()
        if not primary:
            continue
        roots = {primary}
        if primary.endswith("高") and len(primary) > 1:
            roots.add(primary[:-1])
            roots.add("高" + primary[:-1])
        if primary.startswith("高") and len(primary) > 1:
            roots.add(primary[1:])
            roots.add(primary[1:] + "高")
        if any(root and root in trigger for root in roots):
            matches.append(primary)
    return matches or primary_terms[:1]


def generate_oral_aliases(term: str) -> set[str]:
    term = str(term or "").strip()
    aliases: set[str] = set()
    if not term:
        return aliases

    if "睡眠" in term:
        aliases.add(term.replace("睡眠", "睡觉"))
    if "醒" in term:
        aliases.update({"容易醒", "半夜醒", "半夜会醒", "夜里醒", "夜里会醒", "睡着会醒", "睡到半夜醒", "醒得早"})
    if "梦" in term:
        aliases.update({"做梦多", "梦多", "睡觉做梦", "睡觉多梦"})
    if term == "失眠":
        aliases.update({"睡不好", "睡眠差", "睡得不好", "睡不踏实", "睡不沉", "入睡难", "半夜会醒", "夜里会醒"})

    if term.endswith("疾病") and len(term) > 2:
        base = term[:-2]
        aliases.update({f"{base}不舒服", f"{base}不好", f"{base}有问题", f"{base}系统不好"})
    if term.endswith("结节") and len(term) > 2:
        base = term[:-2]
        aliases.update({f"{base}有结节", f"{base}长结节", f"{base}小结节", f"查出{base}结节"})
    if term.startswith("反复") and len(term) > 2:
        base = term[2:]
        aliases.update({f"经常{base}", f"老是{base}", f"总是{base}", f"一直{base}"})
    if term.endswith("不振") and len(term) > 2:
        aliases.update({"不想吃饭", "吃不下饭", "胃口不好", "没胃口", "饭量小"})
    if "疲劳" in term or "乏力" in term:
        aliases.update({"容易累", "总是累", "没劲", "没力气", "体力差", "浑身没劲"})
    if "饱胀" in term or "胃胀" in term:
        aliases.update({"吃完饭胀", "吃完很胀", "饭后胀", "饭后胃胀", "吃饭后胃胀"})
    if "便秘" in term:
        aliases.update({"大便干", "拉不出来", "排便困难", "几天不上厕所"})
    if "高" in term and len(term) >= 3:
        aliases.update({term.replace("高", "偏高"), term.replace("高", "有点高"), term.replace("高", "很高")})
    if "月经" in term:
        aliases.update({"经期不准", "月经不准", "经量异常", "例假不正常"})
    if "头发" in term or "掉发" in term:
        aliases.update({"脱发", "掉头发", "头发少", "发量少"})
    if "鼻炎" in term:
        aliases.update({"鼻子过敏", "鼻塞", "流鼻涕", "打喷嚏", "鼻子痒"})
    if "耳鸣" in term:
        aliases.update({"耳朵响", "耳内响", "嗡嗡响"})
    return {alias for alias in aliases if alias and alias != term}


def split_terms(value: object) -> list[str]:
    text = str(value or "").strip()
    return [part.strip() for part in TERM_SPLIT_RE.split(text) if part.strip()]


def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return STRIP_RE.sub("", text)


def char_overlap(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    return len(a_set & b_set) / max(len(a_set), len(b_set))
