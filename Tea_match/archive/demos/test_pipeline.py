"""
综合测试脚本：演示完整的推荐流程

测试场景：
1. 明确诉求 → 直接推荐（快速路径）
2. 模糊诉求 → 澄清 → 推荐（完整路径）
3. 混合诉求 → 部分澄清 → 综合推荐（实际场景）
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_cmd(script: str, args: list[str]) -> str:
    """运行 Python 脚本并返回输出。"""
    cmd = ["python", script] + args
    # 修复 Windows 编码问题：使用 UTF-8 编码
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent,
                           encoding='utf-8', errors='replace')
    return result.stdout or ""


def test_case_1_clear_complaints():
    """测试 1: 明确诉求 - 应该直接推荐"""
    print("\n" + "="*70)
    print("测试 1: 明确诉求 → 直接推荐")
    print("="*70)

    query = "卵巢囊肿，容易疲劳"
    print(f"\n用户输入: {query}\n")

    # 步骤 1: 理解查询
    print("Step 1: 理解诉求")
    output = run_cmd("understand_query.py", [query, "--mock", "--pretty"])
    result = json.loads(output)

    print(f"识别的诉求:")
    for complaint in result.get("complaints", []):
        print(f"  - {complaint['raw']}")
        print(f"    类型: {complaint['type']}")
        print(f"    检索词: {complaint['normalized_terms']}")
        print(f"    置信度: {complaint['confidence']}")

    # 检查是否有模糊诉求
    vague = [c for c in result.get("complaints", []) if c.get("confidence", 0) < 0.8]
    clear = [c for c in result.get("complaints", []) if c.get("confidence", 0) >= 0.8]

    print(f"\n分析: {len(clear)} 个明确诉求, {len(vague)} 个模糊诉求")

    if not vague:
        print("✓ 无需澄清，可以直接进行 RAG 搜索")
    else:
        print("! 发现模糊诉求，需要澄清")


def test_case_2_vague_complaint():
    """测试 2: 模糊诉求 - 需要澄清"""
    print("\n" + "="*70)
    print("测试 2: 模糊诉求 → 澄清 → 推荐")
    print("="*70)

    complaint = "心烦"
    print(f"\n检测模糊诉求: {complaint}\n")

    # 步骤 1: 检测模糊性
    print("Step 1: 检测模糊性和生成澄清问题")
    output = run_cmd("disambiguate_complaint.py", [complaint, "--use-local", "--pretty"])
    result = json.loads(output)

    print(f"原诉求: {result.get('complaint')}")
    print(f"是模糊诉求: {result.get('is_vague')}")

    if result.get("clarification_questions"):
        print(f"\n澄清问题 ({len(result['clarification_questions'])} 个):")
        for i, q in enumerate(result["clarification_questions"][:3], 1):
            print(f"  {i}. {q}")

    # 步骤 2: 模拟用户回答
    print(f"\nStep 2: 模拟用户回答澄清问题")
    mock_response = "是的，最近睡眠不好，经常失眠多梦"
    print(f"用户回答: {mock_response}")

    output = run_cmd("disambiguate_complaint.py", [complaint, "--response", mock_response, "--use-local", "--pretty"])
    result = json.loads(output)

    inferred = result.get("inferred_symptoms", [])
    print(f"\n推断的规范症状: {inferred}")

    # 步骤 3: 搜索推荐
    print(f"\nStep 3: 搜索推荐的茶饮")
    for symptom in inferred:
        print(f"  搜索: {symptom}")
        # 这里应该调用 search_vector_store.py


def test_case_3_mixed_complaints():
    """测试 3: 混合诉求 - 部分明确，部分模糊"""
    print("\n" + "="*70)
    print("测试 3: 混合诉求 → 选择性澄清 → 综合推荐")
    print("="*70)

    query = "最近觉得心烦，卵巢囊肿，最近容易疲劳"
    print(f"\n用户输入: {query}\n")

    # 步骤 1: 拆分和分类
    print("Step 1: 拆分和分类诉求")
    output = run_cmd("understand_query.py", [query, "--mock", "--pretty"])
    result = json.loads(output)

    complaints = result.get("complaints", [])
    print(f"识别 {len(complaints)} 个诉求:\n")

    clear_list = []
    vague_list = []

    for complaint in complaints:
        raw = complaint["raw"]
        confidence = complaint.get("confidence", 0)
        is_vague = confidence < 0.8

        if is_vague:
            vague_list.append((raw, complaint))
            status = "❌ 模糊"
        else:
            clear_list.append((raw, complaint))
            status = "✓ 明确"

        print(f"  {status}: {raw}")
        print(f"    → {complaint['normalized_terms']}")

    # 步骤 2: 对模糊诉求进行澄清
    if vague_list:
        print(f"\n\nStep 2: 澄清 {len(vague_list)} 个模糊诉求")

        for raw, complaint in vague_list:
            print(f"\n【澄清】{raw}")

            output = run_cmd("disambiguate_complaint.py", [raw, "--use-local", "--pretty"])
            result = json.loads(output)

            if result.get("clarification_questions"):
                for q in result["clarification_questions"][:2]:
                    print(f"  ? {q}")

                # 模拟用户回答
                mock_response = "是的，伴随失眠和多梦"
                print(f"  [用户回答] {mock_response}")

                output = run_cmd(
                    "disambiguate_complaint.py",
                    [raw, "--response", mock_response, "--use-local", "--pretty"],
                )
                result = json.loads(output)
                symptoms = result.get("inferred_symptoms", [])
                print(f"  → 推断症状: {symptoms}")

    # 步骤 3: 汇总所有症状
    print(f"\n\nStep 3: 汇总所有检索词")
    all_search_terms = []

    for raw, complaint in clear_list:
        terms = complaint.get("normalized_terms", [])
        all_search_terms.extend(terms)
        print(f"  明确诉求: {raw} → {terms}")

    # 这里应该添加已澄清的模糊诉求的症状

    print(f"\n最终检索词: {all_search_terms}")


def test_case_4_negative_cases():
    """测试 4: 边界情况"""
    print("\n" + "="*70)
    print("测试 4: 边界情况")
    print("="*70)

    test_queries = [
        "不舒服",  # 太模糊
        "最近特别累",  # 口语
        "血压有点高",  # 部分口语
        "",  # 空输入
    ]

    for query in test_queries:
        if not query:
            continue
        print(f"\n测试: {query}")

        try:
            output = run_cmd("understand_query.py", [query, "--mock", "--pretty"])
            result = json.loads(output)
            complaints = result.get("complaints", [])

            if not complaints:
                print("  → 无法识别")
            else:
                for c in complaints:
                    print(f"  → {c['raw']} (conf: {c.get('confidence', 0)})")
        except Exception as e:
            print(f"  → 错误: {e}")


def print_summary():
    """打印系统架构总结"""
    print("\n" + "="*70)
    print("系统架构总结")
    print("="*70)

    summary = """

流程架构 (Multi-stage Pipeline):

┌─────────────────────────────────────────────────────────────┐
│ 用户输入: "最近觉得心烦，卵巢囊肿，最近容易疲劳"          │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────▼──────────┐
        │ Stage 1: 拆分诉求   │ (understand_query.py)
        └─────────┬──────────┘
                  │
        ┌─────────▼─────────────────┐
        │ 分类: 明确 vs 模糊         │
        │ - 卵巢囊肿 ✓ 明确         │
        │ - 容易疲劳 ✓ 明确         │
        │ - 心烦 ❌ 模糊             │
        └─────────┬─────────────────┘
                  │
        ┌─────────▼──────────────────────┐
        │ Stage 2: 澄清模糊诉求          │ (disambiguate_complaint.py)
        │ 心烦 → Q1: 伴随失眠吗?        │
        │      → Q2: 容易焦虑吗?        │
        │ 用户回答 → 推断症状            │
        └─────────┬──────────────────────┘
                  │
        ┌─────────▼───────────────────────────┐
        │ Stage 3: 合并症状 + RAG 检索         │
        │ 检索词: [卵巢囊肿, 易疲劳,           │
        │         失眠, 心神不宁, ...]         │
        └─────────┬───────────────────────────┘
                  │
        ┌─────────▼──────────────────────┐
        │ Stage 4: 推荐                   │
        │ 舒安茶: 失眠 + 心神不宁 + ...  │
        │ 肝护茶: 卵巢囊肿 + ...          │
        │ 元气茶: 易疲劳 + ...            │
        └─────────┬──────────────────────┘
                  │
        ┌─────────▼─────────────────────┐
        │ 返回: [舒安茶, 肝护茶, 元气茶] │
        └───────────────────────────────┘

核心模块:

1. understand_query.py (诉求理解)
   - 输入: 原始用户输入
   - 输出: 拆分的诉求列表，每个诉求标有类型和置信度

2. disambiguate_complaint.py (模糊诉求澄清)
   - 输入: 模糊诉求 + (可选) 用户回答
   - 输出: 澄清问题 或 推断的规范症状

3. prepare_rag_data.py (RAG 数据准备)
   - 构建茶饮-症状知识库

4. search_vector_store.py (RAG 检索)
   - 输入: 症状关键词
   - 输出: 推荐的茶饮列表

5. recommend_pipeline.py (端到端协调)
   - 整合以上所有模块

关键设计点:

✓ 模糊诉求识别: 基于诉求长度、关键词、置信度
✓ 多轮澄清: 用户可通过对话逐步澄清诉求
✓ 本地规则优先: 快速路径，无需调用 API
✓ LLM 增强: 当本地规则不匹配时，调用模型
✓ RAG 匹配: 症状 → 知识库 → 茶饮推荐
✓ 混合场景: 同一个查询中支持明确 + 模糊的混合处理

部署建议:

- 本地规则库 (disambiguate_complaint.py) 定期更新
- RAG 知识库 (prepare_rag_data.py) 基于运营数据优化
- LLM 调用添加缓存以降低成本
- 前端通过 WebSocket 或 Server-Sent Events 实现多轮对话
"""

    print(summary)


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("中医茶饮推荐系统 - 综合测试")
    print("="*70)

    test_case_1_clear_complaints()
    test_case_2_vague_complaint()
    test_case_3_mixed_complaints()
    test_case_4_negative_cases()

    print_summary()

    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    main()
