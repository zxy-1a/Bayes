"""
整合流程：从用户诉求 → 模糊诉求识别 → 澄清 → 症状标准化 → RAG 检索 → 茶饮推荐

这是一个协调器模块，组织多个子模块的调用。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_understand_query(query: str, use_mock: bool = False) -> dict[str, Any]:
    """调用 understand_query.py 拆分和规范化诉求。"""
    cmd = ["python", "understand_query.py", query]
    if use_mock:
        cmd.append("--mock")
    cmd.append("--pretty")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent,
                           encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"Error in understand_query: {result.stderr}", file=sys.stderr)
        return {"error": "understand_query failed"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid json from understand_query"}


def run_disambiguate_complaint(
    complaint: str, response: str = "", use_local: bool = True
) -> dict[str, Any]:
    """调用 disambiguate_complaint.py 处理模糊诉求。"""
    cmd = ["python", "disambiguate_complaint.py", complaint]
    if response:
        cmd.extend(["--response", response])
    if use_local:
        cmd.append("--use-local")
    cmd.append("--pretty")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent,
                           encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"Error in disambiguate_complaint: {result.stderr}", file=sys.stderr)
        return {"error": "disambiguate_complaint failed"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid json from disambiguate_complaint"}


def run_search_vector_store(query: str) -> dict[str, Any]:
    """调用 search_vector_store.py 进行 RAG 检索。"""
    cmd = ["python", "search_vector_store.py", query, "--pretty"]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent,
                           encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"Warning in search_vector_store: {result.stderr}", file=sys.stderr)
        return {"results": []}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"results": []}


def analyze_complaints_for_clarity(complaints: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    分析诉求列表，分离出明确症状和模糊诉求。

    Returns:
        (clear_complaints, vague_complaints)
    """
    clear = []
    vague = []

    # 模糊诉求的关键词（可扩展）
    vague_keywords = ["烦", "没劲", "不舒服", "难受", "闷", "胀", "怪", "晕"]

    for complaint in complaints:
        raw = str(complaint.get("raw", ""))
        # 如果诉求很短、或包含模糊词汇，标记为模糊
        if len(raw) < 4 or any(kw in raw for kw in vague_keywords):
            vague.append(complaint)
        else:
            clear.append(complaint)

    return clear, vague


def recommend_teas_from_search_results(results: list[dict]) -> list[dict]:
    """从 RAG 搜索结果提取茶饮推荐。"""
    recommendations = []
    seen_teas = set()

    for item in results:
        metadata = item.get("metadata", {})
        tea_name = metadata.get("tea_name")
        if tea_name and tea_name not in seen_teas:
            seen_teas.add(tea_name)
            recommendations.append(
                {
                    "tea_name": tea_name,
                    "course": metadata.get("course", ""),
                    "symptom": metadata.get("symptom", ""),
                    "doc_type": metadata.get("doc_type", ""),
                    "priority": metadata.get("priority", 999),
                    "content_snippet": item.get("content", "")[:200],
                }
            )

    # 按优先级排序
    recommendations.sort(key=lambda x: x["priority"])
    return recommendations


def build_clarification_response(vague_complaint: dict) -> dict[str, Any]:
    """为模糊诉求生成澄清问题。"""
    raw = vague_complaint.get("raw", "")
    result = run_disambiguate_complaint(raw, use_local=True)

    return {
        "original_complaint": raw,
        "is_vague": True,
        "clarification_questions": result.get("clarification_questions", []),
        "pattern_detected": result.get("source") == "local_rules",
        "status": "awaiting_user_response",
    }


def consolidate_recommended_symptoms(vague_resolved: list[str]) -> list[str]:
    """
    将模糊诉求的澄清结果合并成推荐的规范症状列表。
    """
    all_symptoms = []
    for symptom_group in vague_resolved:
        if isinstance(symptom_group, list):
            all_symptoms.extend(symptom_group)
        else:
            all_symptoms.append(symptom_group)
    return list(set(all_symptoms))  # 去重


def interactive_clarification_round(vague_complaint: dict) -> list[str]:
    """
    交互式澄清一个模糊诉求。
    模拟用户交互（实际应用中由前端或多轮对话系统驱动）。
    """
    raw = vague_complaint.get("raw", "")
    clarif_result = build_clarification_response(vague_complaint)

    questions = clarif_result.get("clarification_questions", [])
    if not questions:
        # 无法澄清，返回默认推断
        result = run_disambiguate_complaint(raw, use_local=True)
        return result.get("inferred_symptoms", [raw])

    # 模拟：在实际系统中，这里应该由对话系统或 WebSocket 处理
    print(f"\n【澄清模糊诉求】 {raw}", file=sys.stderr)
    for i, q in enumerate(questions[:2], 1):  # 最多问2个问题
        print(f"  问题 {i}: {q}", file=sys.stderr)

    # 模拟用户回答（实际应用中由前端提供）
    # 这里为了演示，假设用户回答包含某些关键词
    mock_response = "是的，最近睡眠不好，容易多梦"
    print(f"  [假设用户回答] {mock_response}", file=sys.stderr)

    # 根据回答推断症状
    disambig_result = run_disambiguate_complaint(raw, response=mock_response, use_local=True)
    return disambig_result.get("inferred_symptoms", [raw])


class TeaRecommendationPipeline:
    """完整的推荐流程管理器。"""

    def __init__(self, use_mock_understand: bool = False):
        self.use_mock_understand = use_mock_understand
        self.clear_complaints = []
        self.vague_complaints = []
        self.resolved_vague = {}
        self.search_results = {}
        self.recommendations = []

    def step1_parse_query(self, user_query: str) -> dict[str, Any]:
        """第一步：解析用户输入，拆分诉求。"""
        print(f"\n=== Step 1: Parse Query ===", file=sys.stderr)
        print(f"Input: {user_query}", file=sys.stderr)

        result = run_understand_query(user_query, use_mock=self.use_mock_understand)
        complaints = result.get("complaints", [])
        self.clear_complaints, self.vague_complaints = analyze_complaints_for_clarity(complaints)

        print(f"Clear complaints: {len(self.clear_complaints)}", file=sys.stderr)
        print(f"Vague complaints: {len(self.vague_complaints)}", file=sys.stderr)

        return {
            "original_query": user_query,
            "total_complaints": len(complaints),
            "clear_count": len(self.clear_complaints),
            "vague_count": len(self.vague_complaints),
            "all_complaints": complaints,
        }

    def step2_clarify_vague(self) -> dict[str, Any]:
        """第二步：对模糊诉求进行澄清。"""
        print(f"\n=== Step 2: Clarify Vague Complaints ===", file=sys.stderr)

        clarifications = []
        for vague in self.vague_complaints:
            clarif = build_clarification_response(vague)
            clarifications.append(clarif)
            print(f"Vague: {vague.get('raw')}", file=sys.stderr)
            print(f"  Questions: {clarif['clarification_questions']}", file=sys.stderr)

            # 模拟澄清过程（实际中由多轮对话驱动）
            resolved = interactive_clarification_round(vague)
            self.resolved_vague[vague.get("raw")] = resolved
            print(f"  Resolved to: {resolved}", file=sys.stderr)

        return {
            "vague_clarifications": clarifications,
            "resolved_vague": self.resolved_vague,
        }

    def step3_normalize_and_search(self) -> dict[str, Any]:
        """第三步：合并明确和已澄清的诉求，进行 RAG 检索。"""
        print(f"\n=== Step 3: Normalize and Search ===", file=sys.stderr)

        # 收集所有要检索的症状
        all_search_terms = []

        # 明确诉求
        for complaint in self.clear_complaints:
            search_terms = complaint.get("normalized_terms", [])
            all_search_terms.extend(search_terms)
            print(f"Clear complaint search: {complaint.get('raw')} -> {search_terms}", file=sys.stderr)

        # 已澄清的模糊诉求
        for original, resolved_symptoms in self.resolved_vague.items():
            all_search_terms.extend(resolved_symptoms)
            print(f"Vague complaint resolved: {original} -> {resolved_symptoms}", file=sys.stderr)

        # 对每个症状进行 RAG 检索
        all_results = []
        for term in all_search_terms:
            results = run_search_vector_store(term)
            items = results.get("results", [])
            all_results.extend(items)
            print(f"Search '{term}': {len(items)} results", file=sys.stderr)

        self.search_results = all_results
        return {
            "search_terms": all_search_terms,
            "total_results": len(all_results),
        }

    def step4_recommend(self) -> dict[str, Any]:
        """第四步：从搜索结果提取推荐茶饮。"""
        print(f"\n=== Step 4: Recommend Teas ===", file=sys.stderr)

        recommendations = recommend_teas_from_search_results(self.search_results)
        self.recommendations = recommendations

        for rec in recommendations[:5]:  # 显示前5个
            print(f"✓ {rec['tea_name']}: {rec['symptom']}", file=sys.stderr)

        return {
            "recommended_teas": recommendations,
            "total_recommendations": len(recommendations),
        }

    def run(self, user_query: str) -> dict[str, Any]:
        """执行完整流程。"""
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Tea Recommendation Pipeline", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        step1 = self.step1_parse_query(user_query)
        step2 = self.step2_clarify_vague()
        step3 = self.step3_normalize_and_search()
        step4 = self.step4_recommend()

        return {
            "query": user_query,
            "step1_parse": step1,
            "step2_clarify": step2,
            "step3_search": step3,
            "step4_recommend": step4,
            "final_recommendations": self.recommendations,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end tea recommendation pipeline with vague complaint disambiguation."
    )
    parser.add_argument("query", help="Customer complaint.")
    parser.add_argument("--mock", action="store_true", help="Use mock rules.")
    parser.add_argument("--no-clarify", action="store_true", help="Skip clarification step.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output.")

    args = parser.parse_args()

    pipeline = TeaRecommendationPipeline(use_mock_understand=args.mock)
    result = pipeline.run(args.query)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
