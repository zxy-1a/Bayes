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
DEFAULT_RECOMMENDATION_LIMIT = 3
COMPLEX_RECOMMENDATION_LIMIT = 3
COMPLEX_SYMPTOM_THRESHOLD = 3
SYMPTOM_COMPLEXITY_GROUPS: dict[str, list[str]] = {
    "三高代谢问题": ["血压高", "高血压", "血糖高", "高血糖", "糖尿病", "尿酸高", "高尿酸", "血脂高", "高血脂", "肥胖症"],
    "呼吸道疾病": ["呼吸道疾病", "呼吸不好", "呼吸不畅", "咳嗽", "痰多", "气管炎", "支气管", "气不足", "气短"],
    "消化道疾病": ["消化道疾病", "胃不舒服", "肠胃不好", "脾胃不好", "胃病", "慢性胃病", "胃炎", "肠炎", "肠化生"],
    "便秘": ["便秘", "排便困难", "大便干", "解不出来"],
    "肾结石": ["肾结石", "结石", "尿路结石"],
    "肝病": ["肝病", "肝不好", "肝功能障碍", "脂肪肝", "肝损伤"],
    "痛风": ["痛风", "尿酸高引起关节痛", "脚趾痛"],
    "肺结节": ["肺结节", "肺部结节"],
    "视力模糊": ["视力模糊", "看不清", "眼花", "看东西模糊"],
    "妇科肿瘤": ["妇科肿瘤", "子宫肌瘤", "卵巢囊肿", "卵巢肿瘤", "妇科包块"],
    "乳腺甲状腺结节": ["乳腺结节", "甲状腺结节", "甲状腺炎", "甲减", "甲状腺弥漫性病变"],
    "失眠": ["失眠", "睡不好", "睡不着", "入睡难", "难入睡", "半夜醒", "夜里醒", "容易醒", "多梦", "早醒", "睡眠差"],
    "抑郁症": ["抑郁症", "抑郁", "情绪低落"],
    "学习能力差": ["学习能力差", "注意力差", "记忆力差", "学东西慢"],
    "小孩发育迟缓": ["小孩发育迟缓", "发育迟缓", "长得慢", "发育慢"],
    "儿童消化不良及消瘦": ["儿童消化不良", "孩子消化不良", "小孩消化不良", "宝宝消化不良", "儿童消化差又瘦", "孩子消化差又瘦", "小孩消化差又瘦", "儿童吃了不吸收又瘦", "孩子吃了不吸收又瘦", "小孩吃了不吸收又瘦", "儿童吃不胖", "孩子吃不胖", "小孩吃不胖", "小朋友消化不良又瘦"],
    "饭后饱胀": ["饭后饱胀", "吃完饭胀", "餐后腹胀", "饭后胀", "饭后胃胀"],
    "食欲不振": ["食欲不振", "没胃口", "胃口差", "不想吃饭", "吃不下饭", "没食欲"],
    "贫血": ["贫血", "血虚", "脸色白", "头晕乏力"],
    "反复感冒": ["反复感冒", "总感冒", "经常感冒", "老是感冒"],
    "疲劳乏力": ["疲劳乏力", "疲劳", "乏力", "容易累", "总是累", "没劲", "没力气", "体力差"],
    "功血": ["功血", "月经过多", "经量过多"],
    "心肌缺血": ["心肌缺血", "心脏供血不足", "冠心病", "胸口发紧"],
    "胆结石胆囊炎": ["胆结石", "胆囊炎", "胆不好", "胆囊不好"],
    "头发稀少掉发": ["头发稀少", "掉发", "脱发", "头发少"],
    "过敏性鼻炎": ["过敏性鼻炎", "鼻炎", "鼻子过敏", "鼻塞流涕"],
    "耳鸣": ["耳鸣", "耳朵嗡嗡响", "耳朵响"],
    "反复口腔溃疡": ["反复口腔溃疡", "口腔溃疡", "嘴巴起泡", "嘴里溃疡"],
    "容易上火": ["容易上火", "上火", "火气大"],
    "胃火大": ["胃火大", "胃热", "胃里有火", "胃火旺"],
    "肾火大": ["肾火大", "肾火旺", "虚火大"],
    "腿脚不灵活": ["腿脚不灵活", "腿脚不好使", "腿脚无力", "走路不利索"],
    "眼部不适": ["眼干", "眼涩", "眼疲劳", "视疲劳", "明目"],
    "情绪心神": ["心烦", "烦躁", "易怒", "焦虑", "情绪", "胸闷", "心慌"],
    "湿热湿气": ["湿热", "湿气", "口苦", "口黏", "痰湿", "苔黄腻", "苔厚腻"],
    "肾系问题": ["肾", "肾虚", "肾亏", "肾气", "腰酸", "腰膝酸软", "夜尿", "尿频"],
}


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
        diagnostic_constitutions: list[str] | None = None,
        diagnostic_organs: list[str] | None = None,
        diagnostic_symptom_hints: list[str] | None = None,
    ) -> dict[str, Any]:
        all_symptoms = self.collect_search_terms(complaints)
        diagnostic_constitutions = [str(item or "").strip() for item in (diagnostic_constitutions or []) if str(item or "").strip()]
        diagnostic_organs = [str(item or "").strip() for item in (diagnostic_organs or []) if str(item or "").strip()]
        diagnostic_symptom_hints = [str(item or "").strip() for item in (diagnostic_symptom_hints or []) if str(item or "").strip()]

        for term in diagnostic_symptom_hints:
            if term not in all_symptoms:
                all_symptoms.append(term)

        organ_hint_terms = self.collect_organ_hint_terms(query, complaints, semantic_terms or [])
        for term in diagnostic_organs:
            if term not in organ_hint_terms:
                organ_hint_terms.append(term)
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
        fatty_liver_terms = {
            r"\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
            r"\u8f7b\u5ea6\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
            r"\u4e2d\u5ea6\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
            r"\u91cd\u5ea6\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
            r"\u4e2d\u91cd\u5ea6\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
            r"\u8102\u80aa\u809d\u4e25\u91cd".encode("ascii").decode("unicode_escape"),
        }
        has_fatty_liver = any(term in all_symptoms for term in fatty_liver_terms)
        if has_fatty_liver:
            step2_matches = [
                rule
                for rule in step2_matches
                if str(rule.get("primary_conditions", "")).strip() != r"\u809d\u75c5".encode("ascii").decode("unicode_escape")
            ]
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

        vision_blur_terms = {r"\u89c6\u529b\u6a21\u7cca".encode("ascii").decode("unicode_escape")}
        diabetic_vision_terms = {r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2".encode("ascii").decode("unicode_escape")}
        has_plain_vision_blur = any(term in all_symptoms for term in vision_blur_terms)
        has_diabetic_vision_blur = any(term in all_symptoms for term in diabetic_vision_terms)
        if has_plain_vision_blur and not has_diabetic_vision_blur:
            for tea_name in [r"\u6851\u83ca\u8336".encode("ascii").decode("unicode_escape"), r"\u5143\u6c14\u8336".encode("ascii").decode("unicode_escape")]:
                self.add_tea(
                    all_teas,
                    tea_name,
                    r"\u7b2c\u4e00\u6b65\u75c7\u72b6\u521d\u7b5b\uff1a\u89c6\u529b\u6a21\u7cca".encode("ascii").decode("unicode_escape"),
                    stage_priority=1,
                    stage_score=78,
                    weight=0.95,
                )
        if has_diabetic_vision_blur:
            for tea_name in [r"\u7518\u5e73\u8336".encode("ascii").decode("unicode_escape"), r"\u6851\u83ca\u8336".encode("ascii").decode("unicode_escape")]:
                self.add_tea(
                    all_teas,
                    tea_name,
                    r"\u7b2c\u4e8c\u6b65\u7ec4\u5408\u89c4\u5219\uff1a\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2".encode("ascii").decode("unicode_escape"),
                    stage_priority=2,
                    stage_score=82,
                    weight=0.9,
                )

        from fallback_rule_matcher import match_fallback_rules

        if has_fatty_liver:
            for tea_name in [
                r"\u98ce\u6e05\u8336".encode("ascii").decode("unicode_escape"),
                r"\u77f3\u659b\u8336".encode("ascii").decode("unicode_escape"),
            ]:
                self.add_tea(
                    all_teas,
                    tea_name,
                    r"\u7b2c\u4e8c\u6b65\u7ec4\u5408\u89c4\u5219\uff1a\u8102\u80aa\u809d".encode("ascii").decode("unicode_escape"),
                    stage_priority=2,
                    stage_score=82,
                    weight=0.9,
                )
        specific_step2_matches = [
            match
            for match in step2_matches
            if self.is_specific_step2_match(match)
        ]

        fallback_matches = []
        fallback_terms = list(all_symptoms)
        for term in [*diagnostic_constitutions, *diagnostic_organs]:
            if term and term not in fallback_terms:
                fallback_terms.append(term)
        all_fallback_matches = match_fallback_rules(combined_query, fallback_terms)
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
            fallback_matches = []
            if not specific_step2_matches and not has_fatty_liver:
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

        user_symptom_units = self.collect_user_symptom_units(query, selected_symptoms, complaints)
        user_symptom_groups = self.collect_user_symptom_groups(user_symptom_units)
        limit = self.determine_recommendation_limit(user_symptom_groups, all_teas)
        candidate_tea_names = list(all_teas.keys())
        return {
            "symptoms": all_symptoms,
            "first_step_matches": first_step_matches,
            "step2_matches": step2_matches,
            "fallback_matches": fallback_matches,
            "diagnostic_constitutions": diagnostic_constitutions,
            "diagnostic_organs": diagnostic_organs,
            "diagnostic_symptom_hints": diagnostic_symptom_hints,
            "user_symptom_units": user_symptom_units,
            "user_symptom_groups": user_symptom_groups,
            "recommendation_limit": limit,
            "candidate_tea_count": len(candidate_tea_names),
            "candidate_tea_names": candidate_tea_names,
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
    def collect_user_symptom_units(
        query: str,
        selected_symptoms: list[str],
        complaints: list[dict[str, Any]],
    ) -> list[str]:
        symptom_units: list[str] = []
        seen = set()

        def append_term(value: object) -> None:
            text = str(value or "").strip()
            if text and text not in seen:
                symptom_units.append(text)
                seen.add(text)

        for symptom in selected_symptoms:
            append_term(symptom)

        for complaint in complaints:
            if not isinstance(complaint, dict):
                continue
            raw = str(complaint.get("raw") or "").strip()
            if raw:
                append_term(raw)
                continue
            normalized_terms = complaint.get("normalized_terms") or []
            if isinstance(normalized_terms, str):
                normalized_terms = [normalized_terms]
            for term in normalized_terms:
                append_term(term)

        if not symptom_units and query.strip():
            append_term(query)

        return symptom_units

    @staticmethod
    def collect_user_symptom_groups(user_symptom_units: list[str]) -> list[str]:
        groups: list[str] = []
        seen = set()

        for unit in user_symptom_units:
            group = RuleRagRecommender.classify_symptom_group(unit)
            if group and group not in seen:
                groups.append(group)
                seen.add(group)

        return groups

    @staticmethod
    def classify_symptom_group(term: str) -> str:
        text = str(term or "").strip()
        if not text:
            return ""
        for group_name, keywords in SYMPTOM_COMPLEXITY_GROUPS.items():
            if any(keyword and keyword in text for keyword in keywords):
                return group_name
        return text

    @staticmethod
    def determine_recommendation_limit(
        user_symptom_groups: list[str],
        all_teas: dict[str, dict[str, Any]],
    ) -> int:
        if len(user_symptom_groups) >= COMPLEX_SYMPTOM_THRESHOLD and len(all_teas) > DEFAULT_RECOMMENDATION_LIMIT:
            return COMPLEX_RECOMMENDATION_LIMIT
        return DEFAULT_RECOMMENDATION_LIMIT

    @staticmethod
    def is_specific_step2_match(match: dict[str, Any]) -> bool:
        primary = str(match.get("primary_conditions") or "").strip()
        trigger = str(match.get("trigger_condition") or "").strip()
        broad_conditions = {"血压高、血糖高、尿酸高、血脂高", "呼吸道疾病", "消化道疾病", "乳腺结节、甲状腺结节"}
        if primary and primary not in broad_conditions:
            return True
        return bool(trigger and primary in broad_conditions)

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




