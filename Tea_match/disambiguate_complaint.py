"""
针对模糊诉求的澄清模块。
识别口语化、模糊的用户诉求，生成追问，根据回答映射到规范症状。
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from openai import OpenAI


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"

# 模糊诉求的识别和追问规则
VAGUE_COMPLAINT_PATTERNS = {
    "心烦": {
        "keywords": ["心烦", "烦躁", "心烦意乱"],
        "tcm_patterns": ["心烦", "烦"],
        "clarification_questions": [
            "您的心烦是否伴随失眠？",
            "是否同时有多梦或易醒的情况？",
            "是否感到容易焦虑或坐立不安？",
            "是否有心悸（心跳不规律）或胸闷感？",
        ],
        "response_mapping": {
            # 回答 → 规范症状列表
            "失眠|多梦|易醒": ["失眠", "心神不宁"],
            "焦虑|坐立不安|容易发火": ["抑郁", "心神不宁", "烦躁"],
            "心悸|胸闷": ["心悸", "心神不宁"],
            "伴热|口干|便秘": ["心火旺", "失眠"],
        },
        "default_normalized": ["心烦", "心神不宁"],
    },
    "乏力": {
        "keywords": ["乏力", "没劲", "无力", "疲劳"],
        "tcm_patterns": ["乏力", "气虚"],
        "clarification_questions": [
            "这种乏力是全身性的还是特别容易腿软？",
            "是否伴随怕冷或手脚冰凉？",
            "是否容易出汗，或者怕吹风？",
            "是否伴随食欲不振或消化不好？",
        ],
        "response_mapping": {
            "全身|无力": ["气虚", "易疲劳"],
            "腿软|腰酸": ["肾虚", "腰酸腿软"],
            "怕冷|手脚冰凉": ["阳虚", "气虚"],
            "出汗|怕风": ["气虚自汗"],
            "食欲|消化": ["脾胃虚弱", "气虚"],
        },
        "default_normalized": ["易疲劳", "气虚"],
    },
    "头晕": {
        "keywords": ["头晕", "头昏", "眩晕", "头昏眼花"],
        "tcm_patterns": ["头晕"],
        "clarification_questions": [
            "头晕时是否有眼花或视物模糊？",
            "是否伴随高血压或颈椎不适？",
            "是否感到贫血、面色苍白或手脚冰凉？",
            "是否容易疲劳或长期睡眠不足？",
        ],
        "response_mapping": {
            "眼花|视物模糊": ["目眩", "肝血不足"],
            "高血压|颈椎": ["高血压", "清阳不升"],
            "贫血|苍白|冰凉": ["血虚", "阳虚"],
            "疲劳|睡眠": ["气血不足", "气虚"],
        },
        "default_normalized": ["头晕", "清阳不升"],
    },
    "胃不好": {
        "keywords": ["胃不好", "胃不舒服", "胃难受", "胃疼", "胃痛", "消化不好"],
        "tcm_patterns": ["胃", "脾胃"],
        "clarification_questions": [
            "您的胃部不适是否伴随疼痛或胀气？",
            "是否容易反酸、烧心或胃酸过多？",
            "是否伴随食欲不振或消化困难？",
            "是否经常便秘或腹泻？",
        ],
        "response_mapping": {
            "疼痛|胀气|胃痛": ["急慢性胃炎", "胃溃疡"],
            "反酸|烧心|胃酸过多": ["胃酸过多", "反流性食道炎"],
            "食欲|消化|消化不好": ["脾胃虚弱", "消化不良"],
            "便秘": ["便秘"],
        },
        "default_normalized": ["急慢性胃炎", "脾胃虚弱"],
    },
    "不好消化": {
        "keywords": ["消化不好", "消化不了", "难消化", "吃不了", "吃不消"],
        "tcm_patterns": ["脾胃", "消化"],
        "clarification_questions": [
            "消化不好时是否伴随腹胀或腹痛？",
            "是否常常便秘或腹泻？",
            "是否食欲不振或容易腹泻？",
            "是否长期消化不好导致体重下降？",
        ],
        "response_mapping": {
            "腹胀|腹痛": ["脾胃虚弱", "消化不良"],
            "便秘": ["便秘"],
            "腹泻": ["腹泻"],
            "食欲|消化": ["脾胃虚弱"],
        },
        "default_normalized": ["脾胃虚弱", "消化不良"],
    },
    "便秘": {
        "keywords": ["便秘", "排便困难", "大便干燥"],
        "tcm_patterns": ["便秘"],
        "clarification_questions": [
            "便秘时大便是否特别干燥？",
            "是否伴随腹胀或腹痛？",
            "是否容易口干或易上火？",
            "是否同时有便秘和怕冷的情况？",
        ],
        "response_mapping": {
            "干燥|口干": ["大肠燥结", "阴虚"],
            "腹胀|腹痛": ["脾阳虚", "气虚"],
            "上火": ["热结便秘"],
            "怕冷": ["脾阳虚"],
        },
        "default_normalized": ["便秘"],
    },
}

SYSTEM_PROMPT_DISAMBIGUATE = """
你是一个中医茶饮推荐系统的诉求澄清模块。
任务是理解用户对模糊症状的补充描述，根据他们的回答，映射到规范的中医症状或诊断术语。

原始模糊诉求: {complaint}

用户的回答：{response}

请输出一个 JSON：
{{
  "complaint": "原始诉求",
  "user_response": "用户回答",
  "inferred_symptoms": ["推断出的规范症状1", "推断出的规范症状2"],
  "confidence": 0.0-1.0,
  "reasoning": "推断的理由"
}}

推断症状时：
- 参考用户回答中的关键词（失眠、多梦、焦虑、怕冷、出汗等）
- 映射到中医规范症状（失眠、心神不宁、气虚、阳虚、肾虚等）
- 可以推断多个相关症状
- 如果用户回答和原诉求无关，置信度较低
""".strip()

SYSTEM_PROMPT_DETECT_VAGUE = """
你是一个中医症状识别模块。
任务是识别用户诉求中哪些是明确的、可以直接在知识库中查找的，哪些是模糊的、需要澄清的。

用户诉求：{complaint}

输出 JSON：
{{
  "complaint": "完整诉求",
  "segments": [
    {{
      "segment": "诉求片段",
      "clarity": "clear|vague|unknown",
      "reason": "判断理由",
      "if_vague": {{
        "likely_pattern": "心烦|乏力|头晕等模糊诉求模式",
        "suggested_questions": ["澄清问题1", "澄清问题2"]
      }}
    }}
  ]
}}

clarity 级别：
- clear: 明确的症状或疾病，可直接查库（如"卵巢囊肿"、"容易疲劳"）
- vague: 口语化、不够具体的表述，需要澄清（如"心烦"、"没劲儿"、"不舒服"）
- unknown: 完全无法理解的内容
""".strip()


def api_key_from_env() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")


def detect_vague_complaints(query: str, model: str, base_url: str, api_key: str) -> dict[str, Any]:
    """使用 LLM 识别诉求中的模糊部分。"""
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = SYSTEM_PROMPT_DETECT_VAGUE.format(complaint=query)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content.strip().lstrip("```json").rstrip("```"))
    except json.JSONDecodeError:
        return {"complaint": query, "segments": [], "error": "parse failed"}


def disambiguate_response(complaint: str, response: str, model: str, base_url: str, api_key: str) -> dict[str, Any]:
    """根据用户对澄清问题的回答，推断规范症状。"""
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = SYSTEM_PROMPT_DISAMBIGUATE.format(complaint=complaint, response=response)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content.strip().lstrip("```json").rstrip("```"))
    except json.JSONDecodeError:
        return {"complaint": complaint, "user_response": response, "error": "parse failed"}


def get_local_clarification_questions(complaint: str) -> list[str] | None:
    """从本地规则库查询澄清问题（快速路径）。"""
    for pattern_key, pattern_config in VAGUE_COMPLAINT_PATTERNS.items():
        if any(keyword in complaint for keyword in pattern_config["keywords"]):
            return pattern_config["clarification_questions"]
    return None


def map_response_to_symptoms(complaint: str, response: str) -> list[str] | None:
    """根据本地规则，将用户回答映射到规范症状。"""
    for pattern_key, pattern_config in VAGUE_COMPLAINT_PATTERNS.items():
        if any(keyword in complaint for keyword in pattern_config["keywords"]):
            for regex_pattern, symptoms in pattern_config["response_mapping"].items():
                if any(keyword in response for keyword in regex_pattern.split("|")):
                    return symptoms
            # 没有匹配到映射，使用默认
            return pattern_config["default_normalized"]
    return None


def main() -> None:
    # 设置 stdout 编码
    import sys
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(description="Disambiguate vague complaints for tea recommendation.")
    parser.add_argument("complaint", help="Vague complaint text.")
    parser.add_argument("--response", help="User's response to clarification questions (optional).")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=api_key_from_env())
    parser.add_argument("--use-local", action="store_true", help="Use local rules only, no API calls.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    args = parser.parse_args()

    if args.response:
        # 模式2：已有用户回答，直接推断症状
        if args.use_local:
            symptoms = map_response_to_symptoms(args.complaint, args.response)
            result = {
                "complaint": args.complaint,
                "user_response": args.response,
                "inferred_symptoms": symptoms or [],
                "source": "local_rules",
            }
        else:
            if not args.api_key:
                raise SystemExit("Missing API key. Use --use-local or set DASHSCOPE_API_KEY.")
            result = disambiguate_response(args.complaint, args.response, args.model, args.base_url, args.api_key)

    else:
        # 模式1：检测模糊诉求、生成澄清问题
        questions = get_local_clarification_questions(args.complaint)
        if questions:
            result = {
                "complaint": args.complaint,
                "is_vague": True,
                "clarification_questions": questions,
                "source": "local_rules",
                "next_step": "Ask these questions and call with --response <answer>",
            }
        else:
            if args.use_local:
                result = {
                    "complaint": args.complaint,
                    "is_vague": None,
                    "source": "local_rules",
                    "note": "No local pattern matched",
                }
            else:
                if not args.api_key:
                    raise SystemExit("Missing API key. Use --use-local or set DASHSCOPE_API_KEY.")
                result = detect_vague_complaints(args.complaint, args.model, args.base_url, args.api_key)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
