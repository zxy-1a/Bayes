from __future__ import annotations

from typing import Any

from tea_match.diagnosis.mappings import (
    CONSTITUTION_ALIAS_MAP,
    DEFAULT_SIGN_PROBABILITY_THRESHOLD,
    DEFAULT_WEAK_SIGN_THRESHOLD,
    ORGAN_RULES,
    PULSE_CONSTITUTION_RULES,
    PULSE_FIELD_LABELS,
    STEP3_CONSTITUTION_TO_TEAS,
    STEP4_ORGAN_TO_TEAS,
    SYMPTOM_RULES,
    TONGUE_CONSTITUTION_RULES,
)
from tea_match.diagnosis.schemas import DiagnosticSummary, EvidenceItem, RuleHint


class DiagnosisSummarizer:
    def __init__(
        self,
        sign_threshold: float = DEFAULT_SIGN_PROBABILITY_THRESHOLD,
        weak_threshold: float = DEFAULT_WEAK_SIGN_THRESHOLD,
    ):
        self.sign_threshold = sign_threshold
        self.weak_threshold = weak_threshold

    def summarize(
        self,
        tongue_result: dict[str, Any] | None = None,
        sublingual_result: dict[str, Any] | None = None,
        pulse_result: dict[str, Any] | None = None,
    ) -> DiagnosticSummary:
        tongue_result = tongue_result or {}
        sublingual_result = sublingual_result or {}
        pulse_result = pulse_result or {}

        summary = DiagnosticSummary(
            raw_summary={
                "tongue_result": tongue_result,
                "sublingual_result": sublingual_result,
                "pulse_result": pulse_result,
            }
        )

        summary.tongue_signs.extend(self._extract_tongue_signs(tongue_result))
        summary.sublingual_signs.extend(self._extract_sublingual_signs(sublingual_result))
        summary.pulse_signs.extend(self._extract_pulse_signs(pulse_result))
        summary.syndrome_signs.extend(self._extract_syndrome_signs(tongue_result))
        summary.syndrome_hints.extend([item.name for item in summary.syndrome_signs])

        constitution_candidates: list[RuleHint] = []
        constitution_name = str(tongue_result.get("tizhi_name") or "").strip()
        mapped_constitution = CONSTITUTION_ALIAS_MAP.get(constitution_name, "")
        if mapped_constitution:
            constitution_candidates.append(
                RuleHint(
                    name=mapped_constitution,
                    rule_step="step3",
                    source=[constitution_name],
                    confidence=0.95,
                    recommended_teas=STEP3_CONSTITUTION_TO_TEAS.get(mapped_constitution, []),
                    evidence_count=1,
                )
            )

        all_evidence = [
            *summary.tongue_signs,
            *summary.sublingual_signs,
            *summary.pulse_signs,
            *summary.syndrome_signs,
        ]

        constitution_candidates.extend(
            self._match_rule_hints(
                all_evidence,
                TONGUE_CONSTITUTION_RULES,
                "step3",
                tea_mapping=STEP3_CONSTITUTION_TO_TEAS,
            )
        )
        constitution_candidates.extend(
            self._match_rule_hints(
                all_evidence,
                PULSE_CONSTITUTION_RULES,
                "step3",
                tea_mapping=STEP3_CONSTITUTION_TO_TEAS,
            )
        )
        summary.constitution_hints = self._dedupe_rule_hints(constitution_candidates)

        organ_candidates = self._match_rule_hints(
            all_evidence,
            ORGAN_RULES,
            "step4",
            tea_mapping=STEP4_ORGAN_TO_TEAS,
        )
        summary.organ_hints = self._dedupe_rule_hints(organ_candidates)

        symptom_candidates = self._match_rule_hints(
            all_evidence,
            SYMPTOM_RULES,
            "symptom_hint",
            tea_mapping={},
        )
        summary.symptom_hints = self._dedupe_rule_hints(symptom_candidates)
        return summary

    def _extract_tongue_signs(self, tongue_result: dict[str, Any]) -> list[EvidenceItem]:
        signs: list[EvidenceItem] = []
        for item in tongue_result.get("char") or []:
            if not isinstance(item, dict):
                continue
            sign_name = str(item.get("type") or "").strip()
            probability = self._safe_float(item.get("probability"))
            details = str(item.get("type_details") or "").strip()
            if not sign_name or probability is None or probability < self.weak_threshold:
                continue
            signs.append(EvidenceItem(name=sign_name, source="tongue_char", confidence=probability, details=details))
        return signs

    def _extract_sublingual_signs(self, sublingual_result: dict[str, Any]) -> list[EvidenceItem]:
        signs: list[EvidenceItem] = []
        characters = sublingual_result.get("characters") or {}
        if isinstance(characters, dict):
            for name, score in characters.items():
                probability = self._safe_float(score)
                if not name or probability is None or probability < self.sign_threshold:
                    continue
                signs.append(EvidenceItem(name=str(name).strip(), source="sublingual_characters", confidence=probability))
        return signs

    def _extract_pulse_signs(self, pulse_result: dict[str, Any]) -> list[EvidenceItem]:
        signs: list[EvidenceItem] = []
        for field_name, default_label in PULSE_FIELD_LABELS.items():
            values = pulse_result.get(field_name) or []
            if isinstance(values, str):
                values = [values]
            for value in values:
                sign_name = str(value or default_label).strip()
                if not sign_name or sign_name == "常脉":
                    continue
                signs.append(EvidenceItem(name=sign_name, source=field_name, confidence=1.0))
        return self._dedupe_evidence(signs)

    def _extract_syndrome_signs(self, tongue_result: dict[str, Any]) -> list[EvidenceItem]:
        signs: list[EvidenceItem] = []
        for item in tongue_result.get("syndrome") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("syndrome") or "").strip()
            details = str(item.get("bingjigaiyao") or "").strip()
            if not name:
                continue
            signs.append(EvidenceItem(name=name, source="tongue_syndrome", confidence=0.9, details=details))
        return self._dedupe_evidence(signs)

    def _match_rule_hints(
        self,
        signs: list[EvidenceItem],
        rules: dict[str, list[str]],
        rule_step: str,
        tea_mapping: dict[str, list[str]],
    ) -> list[RuleHint]:
        hints: list[RuleHint] = []
        for target_name, keywords in rules.items():
            matched_sources: list[str] = []
            confidence_values: list[float] = []
            for sign in signs:
                if any(keyword and keyword in sign.name for keyword in keywords):
                    matched_sources.append(sign.name)
                    if sign.confidence is not None:
                        confidence_values.append(float(sign.confidence))
            if matched_sources:
                unique_sources = list(dict.fromkeys(matched_sources))
                score = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.7
                hints.append(
                    RuleHint(
                        name=target_name,
                        rule_step=rule_step,
                        source=unique_sources,
                        confidence=score,
                        recommended_teas=tea_mapping.get(target_name, []),
                        evidence_count=len(unique_sources),
                    )
                )
        return hints

    @staticmethod
    def _dedupe_rule_hints(hints: list[RuleHint]) -> list[RuleHint]:
        merged: dict[str, RuleHint] = {}
        for hint in hints:
            current = merged.get(hint.name)
            if not current:
                merged[hint.name] = RuleHint(
                    name=hint.name,
                    rule_step=hint.rule_step,
                    source=list(dict.fromkeys(hint.source)),
                    confidence=hint.confidence,
                    recommended_teas=list(dict.fromkeys(hint.recommended_teas)),
                    evidence_count=max(int(hint.evidence_count or 0), len(list(dict.fromkeys(hint.source)))),
                )
                continue
            current.source = list(dict.fromkeys([*current.source, *hint.source]))
            current.confidence = max(current.confidence, hint.confidence)
            current.recommended_teas = list(dict.fromkeys([*current.recommended_teas, *hint.recommended_teas]))
            current.evidence_count = max(current.evidence_count, len(current.source))

        return sorted(
            merged.values(),
            key=lambda item: (float(item.confidence or 0), int(item.evidence_count or 0), len(item.recommended_teas)),
            reverse=True,
        )

    @staticmethod
    def _dedupe_evidence(signs: list[EvidenceItem]) -> list[EvidenceItem]:
        merged: dict[str, EvidenceItem] = {}
        for sign in signs:
            current = merged.get(sign.name)
            if not current:
                merged[sign.name] = sign
                continue
            if (sign.confidence or 0) > (current.confidence or 0):
                merged[sign.name] = sign
        return list(merged.values())

    @staticmethod
    def _safe_float(value: object) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
