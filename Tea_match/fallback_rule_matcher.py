from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).parent
CONSTITUTION_PATH = BASE_DIR / "rag_output" / "step3_constitution_fallback.csv"
ORGAN_PATH = BASE_DIR / "rag_output" / "step4_organ_fallback.csv"
STRIP_RE = re.compile(r"[\s，,、；;：:。.!！？?（）()\[\]【】<>《》]+")

CONSTITUTION_ALIASES = {
    "气虚": ["气虚", "气虚体质", "气不足", "气短", "没力气", "容易累", "容易疲劳", "说话没劲"],
    "阳虚": ["阳虚", "阳虚体质", "怕冷", "手脚冷", "手脚冰凉", "畏寒", "身体发冷"],
    "痰湿": ["痰湿", "痰湿体质", "湿气重", "有湿气", "身体沉重", "痰多", "舌苔厚腻"],
    "湿热": ["湿热", "湿热体质", "体内湿热", "又湿又热", "容易长痘", "口苦口黏", "小便黄", "舌苔黄腻"],
    "血瘀": ["血瘀", "血瘀体质", "淤血", "血液循环不好", "脸色暗", "舌头紫暗", "有瘀斑"],
    "平和": ["平和", "平和体质", "体质平和", "没什么问题", "正常体质"],
    "特禀(容易过敏)": ["特禀", "特禀体质", "容易过敏", "过敏体质", "敏感体质", "一过敏就不舒服"],
    "阴虚": ["阴虚", "阴虚体质", "口干", "咽干", "潮热", "盗汗", "手心热", "五心烦热"],
    "气郁": ["气郁", "气郁体质", "肝郁", "心情郁闷", "胸闷", "爱叹气", "情绪压抑", "容易生闷气"],
}

ORGAN_ALIASES = {
    "肝": [
        "肝",
        "肝不好",
        "肝问题",
        "肝不太好",
        "肝有问题",
        "肝脏不好",
        "肝脏有问题",
        "肝功能不好",
        "肝功能差",
        "肝功能障碍",
        "肝功能异常",
        "肝功能不正常",
        "肝火旺",
        "肝郁",
        "护肝",
        "转氨酶高",
    ],
    "心": [
        "心",
        "心不好",
        "心问题",
        "心不太好",
        "心有问题",
        "心脏不好",
        "心脏有问题",
        "心功能不好",
        "心功能差",
        "心功能障碍",
        "心功能异常",
        "心慌",
        "心烦",
        "胸闷",
        "胸口不舒服",
        "心脏亚健康",
    ],
    "脾": [
        "脾",
        "脾不好",
        "脾问题",
        "脾胃不好",
        "脾胃问题",
        "脾胃虚弱",
        "脾胃差",
        "胃不好",
        "胃问题",
        "胃不太好",
        "胃有问题",
        "消化不好",
        "消化问题",
        "消化差",
        "脾虚",
        "胃虚",
        "胃弱",
        "运化不好",
    ],
    "肺": [
        "肺",
        "肺不好",
        "肺问题",
        "肺不太好",
        "肺有问题",
        "肺功能不好",
        "肺功能差",
        "肺功能障碍",
        "肺部不好",
        "呼吸不好",
        "呼吸不顺",
        "呼吸道问题",
        "气管不好",
        "肺气不足",
        "容易咳嗽",
    ],
    "肾": [
        "肾",
        "肾不好",
        "肾问题",
        "肾不太好",
        "肾有问题",
        "肾脏不好",
        "肾脏有问题",
        "肾功能不好",
        "肾功能差",
        "肾功能障碍",
        "肾功能异常",
        "肾功能不全",
        "肾虚",
        "肾亏",
        "肾气不足",
        "肾气亏",
        "肾气虚",
        "肾阳虚",
        "肾阴虚",
        "腰酸",
        "腰酸腿软",
        "腰膝酸软",
        "夜尿多",
        "尿频",
    ],
}


def norm_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return STRIP_RE.sub("", text)


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def condition_matches(condition: str, haystack: str, aliases: dict[str, list[str]]) -> bool:
    normalized_haystack = norm_text(haystack)
    candidates = aliases.get(condition, [condition])
    return any(norm_text(candidate) in normalized_haystack for candidate in candidates if candidate)


def match_fallback_rules(query: str, normalized_terms: Iterable[str]) -> list[dict[str, object]]:
    haystack = " ".join([query, *[str(term) for term in normalized_terms if term]])
    matches: list[dict[str, object]] = []

    for row in load_rows(CONSTITUTION_PATH):
        condition = row.get("fallback_condition", "")
        if not condition_matches(condition, haystack, CONSTITUTION_ALIASES):
            continue
        matches.append(
            {
                "fallback_type": "constitution",
                "condition": condition,
                "tea_name": row.get("tea_name", ""),
                "priority": int(row.get("priority") or 3),
                "weight": float(row.get("weight") or 0.6),
                "source": "step3_constitution_fallback",
            }
        )

    for row in load_rows(ORGAN_PATH):
        condition = row.get("fallback_condition", "")
        if not condition_matches(condition, haystack, ORGAN_ALIASES):
            continue
        matches.append(
            {
                "fallback_type": "organ",
                "condition": condition,
                "tea_name": row.get("tea_name", ""),
                "priority": int(row.get("priority") or 4),
                "weight": float(row.get("weight") or 0.6),
                "source": "step4_organ_fallback",
            }
        )

    return [match for match in matches if match["tea_name"]]
