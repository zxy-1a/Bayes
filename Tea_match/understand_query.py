from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from typing import Any

from openai import OpenAI


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"

SYSTEM_PROMPT = """
你是一个中医茶饮推荐系统的 query understanding 模块，只负责理解用户主诉，不直接推荐茶饮。

输入可能包含：
- free_text: 用户自由输入的主诉
- selected_symptoms: 用户在前端点击确认的症状/病症/体质/五脏选项

任务：
1. 将用户一句话拆成多个独立诉求，保持原文顺序。
2. 将口语化表达归一成适合检索知识库的候选词。
3. 把 selected_symptoms 视为用户确认过的高置信度信息，必须并入输出。
4. 识别诉求类型：symptom、western_disease、tcm_pattern、constitution、organ、lifestyle、unknown。
5. 输出必须是严格 JSON，不要输出 Markdown，不要解释。

归一原则：
- 每个诉求保留 raw 原文片段。
- normalized_terms 放 3 到 8 个检索候选词，包含原词、常见同义词、可能匹配知识库的专业词或功能词。
- 不要编造具体茶饮名称，不要直接给茶饮推荐。
- 对西医疾病可以保留疾病名，也可补充中医/业务检索方向，例如“结节病”“囊肿”“气虚”“明目”“缓解眼疲劳”等。
- selected_symptoms 的 confidence 应高于自由文本推断，一般设为 0.95。
- 如果一句话里有多个疾病或症状，必须拆成多个 complaint。

返回 JSON schema：
{
  "query": "用户原句",
  "selected_symptoms": ["用户点击项"],
  "complaints": [
    {
      "order": 1,
      "raw": "原文片段",
      "type": "symptom",
      "normalized_terms": ["检索词1", "检索词2"],
      "search_query": "用于向量检索的一行文本",
      "confidence": 0.0,
      "source": ["free_text"],
      "notes": "简短说明，可为空"
    }
  ]
}
""".strip()

MOCK_EXPANSIONS = [
    (
        ("眼睛干燥", "眼睛干", "眼干", "干眼", "眼涩", "眼睛涩", "视疲劳", "眼疲劳"),
        ["眼睛干燥", "眼干", "眼涩", "干眼", "缓解眼疲劳", "护肝明目", "明目"],
        "symptom",
    ),
    (
        ("卵巢囊肿",),
        ["卵巢囊肿", "囊肿", "各类结节病", "女性癥瘕", "瘀阻"],
        "western_disease",
    ),
    (
        ("容易疲劳", "易疲劳", "乏力", "没劲", "气不足", "气虚"),
        ["易疲劳", "乏力", "气虚", "气不足", "改善心肺功能弱"],
        "symptom",
    ),
]

SPLIT_RE = re.compile(r"[，,、；;。\.\n\r]+|(?:同时)?(?:伴有|合并)|以及|还有|并且|且|和")


def api_key_from_env() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")


def split_query(query: str) -> list[str]:
    parts = [part.strip() for part in SPLIT_RE.split(query)]
    return [part for part in parts if part]


def selected_type(term: str) -> str:
    if "体质" in term or term in {"气虚", "阳虚", "痰湿", "湿热", "血瘀", "阴虚", "气郁", "平和"}:
        return "constitution"
    if any(organ in term for organ in ["肝", "心", "脾", "肺", "肾"]):
        return "organ"
    if any(word in term for word in ["囊肿", "结节", "炎", "病", "结石", "甲减", "贫血"]):
        return "western_disease"
    return "symptom"


def build_mock_result(query: str, selected_symptoms: list[str] | None = None) -> dict[str, Any]:
    selected_symptoms = selected_symptoms or []
    complaints = []
    for idx, raw in enumerate(split_query(query), start=1):
        normalized_terms = [raw]
        complaint_type = "unknown"
        for triggers, terms, matched_type in MOCK_EXPANSIONS:
            if any(trigger in raw for trigger in triggers):
                normalized_terms = terms
                complaint_type = matched_type
                break
        complaints.append(
            {
                "order": idx,
                "raw": raw,
                "type": complaint_type,
                "normalized_terms": normalized_terms,
                "search_query": " ".join(normalized_terms),
                "confidence": 0.6 if complaint_type == "unknown" else 0.9,
                "source": ["free_text"],
                "notes": "mock fallback",
            }
        )

    result = {"query": query, "selected_symptoms": selected_symptoms, "complaints": complaints}
    return append_selected_complaints(result, selected_symptoms)


def parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def understand_with_qwen(
    query: str,
    selected_symptoms: list[str],
    model: str,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    payload = {
        "free_text": query,
        "selected_symptoms": selected_symptoms,
    }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return parse_json_response(content)


def append_selected_complaints(result: dict[str, Any], selected_symptoms: list[str]) -> dict[str, Any]:
    if not selected_symptoms:
        result.setdefault("selected_symptoms", [])
        return result

    complaints = result.setdefault("complaints", [])
    existing_terms = set()
    for item in complaints:
        if not isinstance(item, dict):
            continue
        existing_terms.add(str(item.get("raw", "")).strip())
        for term in item.get("normalized_terms", []) or []:
            existing_terms.add(str(term).strip())

    next_order = len(complaints) + 1
    for symptom in selected_symptoms:
        symptom = str(symptom).strip()
        if not symptom or symptom in existing_terms:
            continue
        complaints.append(
            {
                "order": next_order,
                "raw": symptom,
                "type": selected_type(symptom),
                "normalized_terms": [symptom],
                "search_query": symptom,
                "confidence": 0.95,
                "source": ["selected_symptoms"],
                "notes": "user selected option",
            }
        )
        next_order += 1
        existing_terms.add(symptom)

    result["selected_symptoms"] = selected_symptoms
    return result


def normalize_result(result: dict[str, Any], query: str, selected_symptoms: list[str] | None = None) -> dict[str, Any]:
    selected_symptoms = selected_symptoms or []
    result.setdefault("query", query)
    result = append_selected_complaints(result, selected_symptoms)
    complaints = result.get("complaints")
    if not isinstance(complaints, list):
        result["complaints"] = []
        return result

    normalized = []
    for idx, item in enumerate(complaints, start=1):
        if not isinstance(item, dict):
            continue
        raw = str(item.get("raw") or "").strip()
        terms = item.get("normalized_terms") or []
        if isinstance(terms, str):
            terms = [terms]
        terms = [str(term).strip() for term in terms if str(term).strip()]
        if raw and raw not in terms:
            terms.insert(0, raw)
        search_query = str(item.get("search_query") or " ".join(terms)).strip()
        source = item.get("source") or []
        if isinstance(source, str):
            source = [source]
        normalized.append(
            {
                "order": int(item.get("order") or idx),
                "raw": raw,
                "type": str(item.get("type") or "unknown"),
                "normalized_terms": terms,
                "search_query": search_query,
                "confidence": float(item.get("confidence") or 0),
                "source": [str(x) for x in source],
                "notes": str(item.get("notes") or ""),
            }
        )
    result["complaints"] = sorted(normalized, key=lambda item: item["order"])
    result["selected_symptoms"] = selected_symptoms
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Understand customer complaints with Qwen and output structured JSON.")
    parser.add_argument("query", help="Customer complaint text.")
    parser.add_argument("--selected-symptoms", nargs="*", default=[], help="Symptoms/options selected by the user in frontend.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=api_key_from_env())
    parser.add_argument("--mock", action="store_true", help="Use local mock rules instead of calling Qwen.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    selected_symptoms = [item.strip() for item in args.selected_symptoms if item.strip()]
    if args.mock:
        result = build_mock_result(args.query, selected_symptoms)
    else:
        if not args.api_key:
            raise SystemExit("Missing API key. Set DASHSCOPE_API_KEY or QWEN_API_KEY, or run with --mock.")
        result = understand_with_qwen(args.query, selected_symptoms, args.model, args.base_url, args.api_key)

    result = normalize_result(result, args.query, selected_symptoms)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()