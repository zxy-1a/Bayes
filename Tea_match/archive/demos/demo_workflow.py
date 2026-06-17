"""
快速开始指南 - 中医茶饮推荐系统模糊诉求处理

这个脚本演示了如何使用新的澄清流程。
"""

import json
import subprocess
import sys
import io
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def run_python(script: str, args: list, cwd=None) -> dict:
    """运行 Python 脚本并返回 JSON 结果"""
    cwd = cwd or Path(__file__).parent
    cmd = ["python", script] + args
    # 修复 Windows 编码问题：使用 UTF-8 编码
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                           encoding='utf-8', errors='replace')

    if result.returncode != 0:
        print(f"❌ 错误: {result.stderr}")
        return {}

    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"❌ 解析失败: {str(e)}")
        if result.stdout:
            print(f"   输出: {result.stdout[:100]}")
        return {}


def demo_workflow():
    """演示完整的推荐工作流"""

    print("\n" + "="*70)
    print("中医茶饮推荐系统 - 模糊诉求澄清流程演示")
    print("="*70)

    # ============ 场景 1: 明确诉求 ============
    print("\n\n【场景 1】明确诉求 → 直接推荐")
    print("-" * 70)

    query1 = "卵巢囊肿，容易疲劳"
    print(f"用户输入: {query1}\n")

    print("步骤 1: 理解诉求")
    result = run_python("understand_query.py", [query1, "--mock", "--pretty"])

    if result:
        complaints = result.get("complaints", [])
        for i, c in enumerate(complaints, 1):
            raw = c.get("raw", "")
            terms = c.get("normalized_terms", [])
            conf = c.get("confidence", 0)
            status = "✓" if conf >= 0.8 else "⚠"
            print(f"  {status} {i}. {raw} (置信度: {conf})")
            print(f"     → 检索词: {', '.join(terms)}")

    print("\n结论: 无需澄清，可直接进行 RAG 查询")
    print("推荐茶饮: [在这里调用 RAG 搜索]")

    # ============ 场景 2: 单个模糊诉求 ============
    print("\n\n【场景 2】模糊诉求 → 澄清 → 推荐")
    print("-" * 70)

    query2 = "心烦"
    print(f"用户诉求: {query2}\n")

    print("步骤 1: 检测模糊性")
    result = run_python("disambiguate_complaint.py", [query2, "--use-local", "--pretty"])

    if result:
        questions = result.get("clarification_questions", [])
        print(f"检测结果: 这是一个模糊诉求 (is_vague: {result.get('is_vague')})\n")
        print(f"步骤 2: 生成澄清问题 ({len(questions)} 个)\n")
        for i, q in enumerate(questions[:3], 1):
            print(f"  Q{i}. {q}")
        if len(questions) > 3:
            print(f"  ... 还有 {len(questions)-3} 个问题")

    print(f"\n步骤 3: 模拟用户回答")
    mock_response = "是的，最近经常失眠，容易多梦"
    print(f"用户回答: \"{mock_response}\"\n")

    print("步骤 4: 推断规范症状")
    result = run_python("disambiguate_complaint.py",
                       [query2, "--response", mock_response, "--use-local", "--pretty"])

    if result:
        symptoms = result.get("inferred_symptoms", [])
        print(f"推断结果: {symptoms}")
        print(f"置信度: {result.get('confidence', 0)}")
        print(f"\n→ 现在可以用这些症状进行 RAG 查询:")
        for s in symptoms:
            print(f"  • 搜索: {s}")

    # ============ 场景 3: 混合诉求 ============
    print("\n\n【场景 3】混合诉求 → 选择性澄清 → 综合推荐")
    print("-" * 70)

    query3 = "最近觉得心烦，卵巢囊肿，最近容易疲劳"
    print(f"用户输入: {query3}\n")

    print("步骤 1: 拆分和分类诉求")
    result = run_python("understand_query.py", [query3, "--mock", "--pretty"])

    clear_count = 0
    vague_count = 0

    if result:
        complaints = result.get("complaints", [])
        for c in complaints:
            conf = c.get("confidence", 0)
            raw = c.get("raw", "")
            if conf >= 0.8:
                print(f"  ✓ 明确: {raw}")
                clear_count += 1
            else:
                print(f"  ⚠ 模糊: {raw}")
                vague_count += 1

    print(f"\n分析结果:")
    print(f"  • 明确诉求: {clear_count} 个 → 直接查询")
    print(f"  • 模糊诉求: {vague_count} 个 → 需要澄清")

    if vague_count > 0:
        print(f"\n步骤 2: 对模糊诉求进行澄清")
        for c in result.get("complaints", []):
            if c.get("confidence", 0) < 0.8:
                raw = c.get("raw", "")
                print(f"\n【澄清 '{raw}'】")

                clarif_result = run_python("disambiguate_complaint.py",
                                          [raw, "--use-local", "--pretty"])
                questions = clarif_result.get("clarification_questions", [])
                if questions:
                    for q in questions[:2]:
                        print(f"  Q. {q}")

    print(f"\n步骤 3: 汇总所有检索词")
    print(f"明确诉求的检索词:")
    print(f"  • 卵巢囊肿 → [卵巢囊肿, 囊肿, ...]")
    print(f"  • 容易疲劳 → [易疲劳, 乏力, 气虚, ...]")
    print(f"模糊诉求的检索词 (经澄清后):")
    print(f"  • 心烦 + 失眠多梦 → [失眠, 心神不宁, ...]")
    print(f"\n步骤 4: 综合 RAG 查询")
    print(f"所有检索词合并: [卵巢囊肿, 易疲劳, 失眠, 心神不宁, ...]")
    print(f"返回的推荐茶饮: [舒安茶, 肝护茶, 元气茶, ...]")

    # ============ 总结 ============
    print("\n\n" + "="*70)
    print("流程总结")
    print("="*70)

    summary = """
关键设计点:

1. 双路径处理
   • 明确诉求 (confidence >= 0.8) → 快速路径 (< 100ms)
   • 模糊诉求 (confidence < 0.8) → 澄清路径 (< 500ms)

2. 本地规则优先
   • disambiguate_complaint.py 中的 VAGUE_COMPLAINT_PATTERNS
   • 覆盖常见的模糊症状 (心烦, 乏力, 头晕, ...)
   • 快速回应，无需调用 API

3. 多轮对话支持
   • 前端通过 WebSocket 与后端交互
   • 用户可以逐步澄清诉求
   • 每一步的结果都是可操作的 JSON

4. 降级匹配
   • 阶段 1: 症状初筛 (优先级 1)
   • 阶段 2: 症状组合 (优先级 2)
   • 阶段 3: 体质降级 (优先级 3)
   • 阶段 4: 脏腑降级 (优先级 4)

部署建议:

1. 完善本地规则库
   • 加入更多常见的模糊诉求模式
   • 根据运营数据不断调整澄清问题
   • 定期更新 response_mapping

2. 集成前端多轮对话
   • WebSocket 连接保持状态
   • 前端按顺序显示澄清问题
   • 用户每次回答后刷新推荐结果

3. 添加监控和反馈
   • 记录澄清成功率
   • 跟踪用户满意度
   • A/B 测试不同的澄清策略

4. 性能优化
   • 本地规则命中率 > 90%
   • LLM 调用频率 < 10%
   • 典型流程延迟 < 500ms
"""

    print(summary)

    print("="*70)
    print("演示完成！")
    print("="*70 + "\n")


def print_file_structure():
    """打印项目文件结构"""
    print("\n项目文件结构:")
    print("""
    D:\\bayes\\Tea_match\\
    ├── 核心模块
    │   ├── understand_query.py              (诉求理解与拆分)
    │   ├── disambiguate_complaint.py        (模糊诉求澄清) ⭐ 新增
    │   ├── recommend_pipeline.py            (端到端协调) ⭐ 新增
    │   ├── prepare_rag_data.py              (RAG 数据准备)
    │   └── search_vector_store.py           (向量检索)
    │
    ├── 接口与配置
    │   ├── api_interface.py                 (API 接口定义) ⭐ 新增
    │   └── README_CLARIFICATION_FLOW.md     (完整文档) ⭐ 新增
    │
    ├── 测试与演示
    │   ├── test_pipeline.py                 (综合测试) ⭐ 新增
    │   └── demo_workflow.py                 (快速演示) ⭐ 新增
    │
    ├── 数据文件
    │   ├── 养生茶饮匹配逻辑.xlsx            (茶饮-症状映射表)
    │   └── 医临床常见症状术语规范.xlsx      (症状规范字典)
    │
    └── 输出文件
        └── rag_output/
            ├── tea_rag_documents.jsonl
            ├── symptom_alias_dictionary.csv
            └── ...

    ⭐ 表示新增或重要文件
    """)


if __name__ == "__main__":
    print_file_structure()
    demo_workflow()

    print("\n快速开始命令:")
    print("""
# 测试模糊诉求识别
python disambiguate_complaint.py "心烦" --use-local --pretty

# 测试用户回答推断
python disambiguate_complaint.py "心烦" --response "是的，最近睡眠不好" --use-local --pretty

# 运行完整测试套件
python test_pipeline.py

# 运行完整推荐流程
python recommend_pipeline.py "最近觉得心烦，卵巢囊肿，最近容易疲劳" --mock --pretty
    """)
