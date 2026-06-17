from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).parent
RULE_PATH = BASE_DIR / "rag_output" / "step2_combo_rules.csv"
ALIAS_PATH = BASE_DIR / "rag_output" / "step2_oral_aliases.csv"
TERM_SPLIT_RE = re.compile(r"[、，,;；\s]+")
STRIP_RE = re.compile(r"[\s，,。.;；:：、！!？?（）()【】\[\]《》<>]+")


def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return STRIP_RE.sub("", text)


def split_terms(value: object) -> list[str]:
    text = str(value or "").strip()
    return [part.strip() for part in TERM_SPLIT_RE.split(text) if part.strip()]


def load_step2_rules(path: Path = RULE_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_oral_aliases(path: Path = ALIAS_PATH) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    if not path.exists():
        return aliases
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            condition = str(row.get("condition", "")).strip()
            if not condition:
                continue
            values = split_terms(str(row.get("aliases", "")).replace("|", "、"))
            merged = [condition, *values]
            aliases[condition] = list(dict.fromkeys([item for item in merged if item]))
    return aliases


def term_matches(term: str, haystack: str, alias_map: dict[str, list[str]]) -> bool:
    if not term:
        return False
    normalized_haystack = norm_text(haystack)
    candidates = alias_map.get(term, [term])
    return any(norm_text(candidate) in normalized_haystack for candidate in candidates if candidate)


def rule_matches(rule: dict[str, str], haystack: str, alias_map: dict[str, list[str]]) -> bool:
    primary_terms = split_terms(rule.get("primary_conditions", ""))
    trigger_terms = split_terms(rule.get("trigger_condition", ""))

    if primary_terms and not any(term_matches(term, haystack, alias_map) for term in primary_terms):
        return False
    if trigger_terms and not any(term_matches(term, haystack, alias_map) for term in trigger_terms):
        return False
    return True

def prefer_specific_trigger_rules(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    triggered_primary_groups = {
        norm_primary_group(match.get("primary_conditions", ""))
        for match in matches
        if str(match.get("trigger_condition", "")).strip()
    }
    if not triggered_primary_groups:
        return matches
    filtered = []
    for match in matches:
        has_trigger = bool(str(match.get("trigger_condition", "")).strip())
        primary_group = norm_primary_group(match.get("primary_conditions", ""))
        if not has_trigger and primary_group in triggered_primary_groups:
            continue
        filtered.append(match)
    return filtered


def norm_primary_group(value: object) -> tuple[str, ...]:
    return tuple(sorted(norm_text(term) for term in split_terms(value) if norm_text(term)))


def match_step2_rules(query: str, normalized_terms: Iterable[str]) -> list[dict[str, object]]:
    haystack = " ".join([query, *[str(term) for term in normalized_terms if term]])
    alias_map = load_oral_aliases()
    matches = []
    seen_rule_ids = set()
    for rule in load_step2_rules():
        rule_id = rule.get("rule_id", "")
        if rule_id in seen_rule_ids:
            continue
        if not rule_matches(rule, haystack, alias_map):
            continue
        recommended_teas = split_terms(rule.get("recommended_teas", ""))
        if not recommended_teas:
            continue
        seen_rule_ids.add(rule_id)
        matches.append(
            {
                "rule_id": rule_id,
                "primary_conditions": rule.get("primary_conditions", ""),
                "trigger_condition": rule.get("trigger_condition", ""),
                "recommended_teas": recommended_teas,
                "rule_type": rule.get("rule_type", "combination"),
                "priority": int(rule.get("priority") or 2),
                "source": "step2_combo_rules",
            }
        )
    return prefer_specific_trigger_rules(matches)