from __future__ import annotations

from typing import Any

from step2_rule_matcher import load_step2_rules, norm_text, split_terms
from tea_match.agents.clarification_config import (
    BROAD_STEP2_CONDITIONS,
    DOMAIN_CONFIGS,
    HEART_FIRST_STEP_TERMS,
    LIVER_FIRST_STEP_TERMS,
    MAX_OPTIONS,
    RESPIRATORY_FIRST_STEP_TERMS,
    RESPIRATORY_PRIMARY_CONDITIONS,
    RENAL_FIRST_STEP_TERMS,
    U,
)


CLARIFICATION_SKIP_VALUE = "__skip_clarification__"


class ClarificationAgent:
    def maybe_clarify(
        self,
        rule_result: dict[str, Any],
        query: str,
        selected_symptoms: list[str],
    ) -> dict[str, Any] | None:
        candidate_tea_count = max(
            int(rule_result.get("candidate_tea_count") or 0),
            len(rule_result.get("top_recommendations") or []),
        )

        domain_name, domain = self._detect_domain(rule_result, query, selected_symptoms)
        if not domain:
            return None
        if not self._should_clarify(candidate_tea_count, domain_name, domain, rule_result, query, selected_symptoms):
            return None
        if self._is_precise_enough(rule_result, query, selected_symptoms, domain_name, domain):
            return None

        options = self._build_options(rule_result, query, selected_symptoms, domain)
        if not options:
            return None

        options = options[:MAX_OPTIONS]
        options.append({"label": U(r"\u4e0d\u786e\u5b9a\uff0c\u5148\u76f4\u63a5\u63a8\u8350"), "value": CLARIFICATION_SKIP_VALUE})

        return {
            "question": self._build_question(query, domain),
            "reason": self._build_reason(candidate_tea_count, domain_name),
            "options": options,
            "candidate_tea_count": candidate_tea_count,
            "domain": domain_name,
        }

    def _detect_domain(
        self,
        rule_result: dict[str, Any],
        query: str,
        selected_symptoms: list[str],
    ) -> tuple[str, dict[str, Any] | None]:
        step2_matches = rule_result.get("step2_matches", []) or []
        broad_primaries = {str(match.get("primary_conditions") or "").strip() for match in step2_matches}
        user_text_parts = [query, *selected_symptoms]
        user_joined = " ".join(norm_text(part) for part in user_text_parts if str(part or "").strip())
        full_text_parts = [query, *selected_symptoms, *rule_result.get("symptoms", []), *rule_result.get("user_symptom_units", [])]
        full_joined = " ".join(norm_text(part) for part in full_text_parts if str(part or "").strip())

        for name, config in DOMAIN_CONFIGS.items():
            for alias in config.get("trigger_aliases", set()):
                alias_key = norm_text(alias)
                if alias_key and alias_key in user_joined:
                    return name, config

        for name, config in DOMAIN_CONFIGS.items():
            broad_conditions = config.get("broad_conditions", set())
            if any(primary in broad_conditions for primary in broad_primaries if primary):
                return name, config
            for alias in config.get("trigger_aliases", set()):
                alias_key = norm_text(alias)
                if alias_key and alias_key in full_joined:
                    return name, config
        return "", None

    def _should_clarify(
        self,
        candidate_tea_count: int,
        domain_name: str,
        domain: dict[str, Any],
        rule_result: dict[str, Any],
        query: str,
        selected_symptoms: list[str],
    ) -> bool:
        if domain_name == "respiratory" and self._is_respiratory_case(rule_result, query, selected_symptoms):
            return True
        if domain_name == "renal" and self._is_renal_case(rule_result, query, selected_symptoms):
            return True
        if domain_name == "liver" and self._is_liver_case(rule_result, query, selected_symptoms):
            return True
        if domain_name == "heart" and self._is_heart_case(rule_result, query, selected_symptoms):
            return True
        if domain.get("force_clarify") and self._is_generic_only(query, selected_symptoms, domain):
            return True
        return candidate_tea_count >= 3

    def _is_precise_enough(
        self,
        rule_result: dict[str, Any],
        query: str,
        selected_symptoms: list[str],
        domain_name: str,
        domain: dict[str, Any] | None,
    ) -> bool:
        step2_matches = rule_result.get("step2_matches", []) or []
        candidate_tea_count = max(
            int(rule_result.get("candidate_tea_count") or 0),
            len(rule_result.get("top_recommendations") or []),
        )
        if domain_name == "respiratory":
            return self._user_already_answered_respiratory(selected_symptoms)
        if domain_name in {"renal", "liver", "heart"}:
            return self._user_already_spoke_specifically(query, selected_symptoms, domain or {})
        if domain and self._user_already_spoke_specifically(query, selected_symptoms, domain):
            return True
        if candidate_tea_count <= 2:
            if domain and domain.get("force_clarify") and self._is_generic_only(query, selected_symptoms, domain):
                return False
            return True
        if len(step2_matches) == 1:
            match = step2_matches[0]
            primary = str(match.get("primary_conditions") or "").strip()
            trigger = str(match.get("trigger_condition") or "").strip()
            if primary and primary not in BROAD_STEP2_CONDITIONS:
                return True
            if trigger and primary and primary not in BROAD_STEP2_CONDITIONS:
                return True
        return False

    def _user_already_spoke_specifically(
        self,
        query: str,
        selected_symptoms: list[str],
        domain: dict[str, Any],
    ) -> bool:
        if domain.get("allow_precise_skip") is False:
            return False
        normalized_selected = {norm_text(part) for part in selected_symptoms if str(part or "").strip()}
        joined = " ".join(norm_text(part) for part in [query, *selected_symptoms] if str(part or "").strip())
        for option in domain.get("options", []):
            value_key = norm_text(option.get("value", ""))
            if value_key and value_key in normalized_selected:
                return True
            for keyword in option.get("keywords", []):
                keyword_key = norm_text(keyword)
                if keyword_key and keyword_key in joined:
                    return True
        return False

    def _build_options(
        self,
        rule_result: dict[str, Any],
        query: str,
        selected_symptoms: list[str],
        domain: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        options: list[dict[str, Any]] = []
        selected_joined = " ".join(norm_text(item) for item in selected_symptoms if str(item or "").strip())
        query_joined = norm_text(query)

        if domain:
            options.extend(domain.get("options", []))
        if not options:
            for match in rule_result.get("step2_matches", []) or []:
                options.extend(self._options_from_match(match))
        if not options:
            for match in rule_result.get("step2_matches", []) or []:
                primary = str(match.get("primary_conditions") or "").strip()
                if primary in BROAD_STEP2_CONDITIONS:
                    options.extend(self._options_from_sibling_rules(primary))

        deduped: list[dict[str, str]] = []
        seen = set()
        for option in options:
            normalized = self._normalize_option(option)
            value_key = norm_text(normalized["value"])
            if not value_key or value_key in seen:
                continue
            if value_key in selected_joined:
                continue
            if self._option_matches_text(normalized, query_joined):
                continue
            deduped.append({"label": normalized["label"], "value": normalized["value"]})
            seen.add(value_key)
        return deduped

    def _options_from_match(self, match: dict[str, Any]) -> list[dict[str, Any]]:
        labels: list[dict[str, Any]] = []
        primary = str(match.get("primary_conditions") or "").strip()
        trigger = str(match.get("trigger_condition") or "").strip()
        if primary and primary not in BROAD_STEP2_CONDITIONS:
            labels.extend(self._wrap_terms(split_terms(primary) or [primary]))
        if trigger:
            labels.extend(self._wrap_terms(self._extract_clarifying_terms(trigger)))
        return labels

    def _options_from_sibling_rules(self, primary_condition: str) -> list[dict[str, Any]]:
        labels: list[dict[str, Any]] = []
        for rule in load_step2_rules():
            if str(rule.get("primary_conditions") or "").strip() != primary_condition:
                continue
            trigger = str(rule.get("trigger_condition") or "").strip()
            if trigger:
                labels.extend(self._wrap_terms(self._extract_clarifying_terms(trigger)))
        return labels
    def _wrap_terms(self, terms: list[str]) -> list[dict[str, Any]]:
        wrapped = []
        for term in terms:
            text = str(term or "").strip()
            if text:
                wrapped.append({"label": text, "value": text, "keywords": [text]})
        return wrapped

    def _extract_clarifying_terms(self, text: str) -> list[str]:
        labels: list[str] = []
        tea_token = U(r"\u8336")
        prefix_a = U(r"\u5982\u6709")
        prefix_b = U(r"\u5982\u679c\u6709")
        for part in split_terms(text):
            part = str(part or "").strip()
            if not part or tea_token in part:
                continue
            if part.startswith(prefix_b):
                part = part[len(prefix_b):].strip()
            elif part.startswith(prefix_a):
                part = part[len(prefix_a):].strip()
            if part and tea_token not in part:
                labels.append(part)
        return labels

    def _normalize_option(self, option: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(option, str):
            text = str(option).strip()
            return {"label": text, "value": text, "keywords": [text]}
        label = str(option.get("label") or option.get("value") or "").strip()
        value = str(option.get("value") or label).strip()
        keywords = option.get("keywords") or [label, value]
        return {"label": label, "value": value, "keywords": [str(item).strip() for item in keywords if str(item).strip()]}

    def _option_matches_text(self, option: dict[str, Any], normalized_text: str) -> bool:
        for keyword in option.get("keywords", []):
            keyword_key = norm_text(keyword)
            if keyword_key and keyword_key in normalized_text:
                return True
        return False

    def _build_question(self, query: str, domain: dict[str, Any] | None) -> str:
        if domain and domain.get("question"):
            return str(domain["question"])
        query = str(query or "").strip()
        if query:
            return U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u5173\u4e8e\u300c") + query + U(r"\u300d\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f")
        return U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f")

    def _build_reason(self, candidate_tea_count: int, domain_name: str) -> str:
        if domain_name == "respiratory":
            return U(r"\u547c\u5438\u9053\u76f8\u5173\u63a8\u8350\u91cc\uff0c\u662f\u5426\u6c14\u4e0d\u8db3\u4f1a\u5f71\u54cd\u662f\u5426\u52a0\u4e0a\u5143\u6c14\u8336\uff0c\u6240\u4ee5\u6211\u5148\u5e2e\u60a8\u786e\u8ba4\u4e00\u4e0b\u3002")
        return U(r"\u5f53\u524d\u4ecd\u53ef\u80fd\u5bf9\u5e94 ") + str(candidate_tea_count) + U(r" \u79cd\u8336\u996e\uff0c\u5148\u628a\u4e3b\u8bc9\u6536\u7a84\u4e00\u70b9\uff0c\u518d\u7ed9\u60a8\u66f4\u51c6\u786e\u7684\u63a8\u8350\u3002")

    def _is_respiratory_case(self, rule_result: dict[str, Any], query: str, selected_symptoms: list[str]) -> bool:
        step2_matches = rule_result.get("step2_matches", []) or []
        for match in step2_matches:
            primary = str(match.get("primary_conditions") or "").strip()
            if primary in RESPIRATORY_PRIMARY_CONDITIONS:
                return True
        text = " ".join(str(part or "") for part in [query, *selected_symptoms, *rule_result.get("user_symptom_units", []), *rule_result.get("symptoms", [])])
        normalized_text = norm_text(text)
        return any(norm_text(term) in normalized_text for term in RESPIRATORY_FIRST_STEP_TERMS)

    def _is_renal_case(self, rule_result: dict[str, Any], query: str, selected_symptoms: list[str]) -> bool:
        text = " ".join(str(part or "") for part in [query, *selected_symptoms, *rule_result.get("user_symptom_units", []), *rule_result.get("symptoms", [])])
        normalized_text = norm_text(text)
        return any(norm_text(term) in normalized_text for term in RENAL_FIRST_STEP_TERMS)

    def _is_liver_case(self, rule_result: dict[str, Any], query: str, selected_symptoms: list[str]) -> bool:
        text = " ".join(str(part or "") for part in [query, *selected_symptoms, *rule_result.get("user_symptom_units", []), *rule_result.get("symptoms", [])])
        normalized_text = norm_text(text)
        return any(norm_text(term) in normalized_text for term in LIVER_FIRST_STEP_TERMS)

    def _is_heart_case(self, rule_result: dict[str, Any], query: str, selected_symptoms: list[str]) -> bool:
        text = " ".join(str(part or "") for part in [query, *selected_symptoms, *rule_result.get("user_symptom_units", []), *rule_result.get("symptoms", [])])
        normalized_text = norm_text(text)
        return any(norm_text(term) in normalized_text for term in HEART_FIRST_STEP_TERMS)

    def _is_generic_only(self, query: str, selected_symptoms: list[str], domain: dict[str, Any]) -> bool:
        joined = " ".join(norm_text(part) for part in [query, *selected_symptoms] if str(part or "").strip())
        if not joined:
            return False
        for option in domain.get("options", []):
            for keyword in option.get("keywords", []):
                keyword_key = norm_text(keyword)
                if keyword_key and keyword_key in joined:
                    return False
        return True

    def _user_already_answered_respiratory(self, selected_symptoms: list[str]) -> bool:
        normalized = {norm_text(item) for item in selected_symptoms if str(item or "").strip()}
        return bool(normalized & {norm_text(U(r"\u6c14\u4e0d\u8db3")), norm_text(U(r"\u547c\u5438\u5e73\u7a33"))})
