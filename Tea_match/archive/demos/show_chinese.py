"""
修复 JSON 输出乱码问题 - 正确显示汉字

这个脚本处理 subprocess 输出中的编码问题，确保 JSON 中的汉字正确显示。
"""

import json
import subprocess
import sys
import io
from pathlib import Path

# 修复 Windows 编码问题 - 确保 stdout 使用 UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors='replace')


def run_command_with_correct_encoding(cmd: list, cwd=None) -> dict:
    """
    运行命令并正确处理 UTF-8 编码。

    关键参数:
    - encoding='utf-8': 指定 UTF-8 编码
    - errors='replace': 遇到无法解码的字符时用替换符
    """
    cwd = cwd or Path(__file__).parent

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        encoding='utf-8',      # ← 最关键：明确使用 UTF-8
        errors='replace'       # ← 备选方案：替换无法解码的字符
    )

    if result.returncode != 0:
        print(f"❌ 错误: {result.stderr}", file=sys.stderr)
        return {}

    try:
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return {}


def test_disambiguate():
    """测试模糊诉求识别 - 应该显示汉字"""
    print("\n" + "="*70)
    print("测试 1: 模糊诉求识别（汉字显示）")
    print("="*70)

    result = run_command_with_correct_encoding(
        ["python", "disambiguate_complaint.py", "心烦", "--use-local", "--pretty"]
    )

    if result:
        print("\n✓ 模糊诉求:")
        print(f"  诉求: {result.get('complaint', 'N/A')}")
        print(f"  是模糊诉求: {result.get('is_vague', False)}")

        questions = result.get('clarification_questions', [])
        if questions:
            print(f"\n✓ 澄清问题 ({len(questions)} 个):")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")

    return result


def test_disambiguate_with_response():
    """测试用户回答推断 - 应该显示汉字"""
    print("\n" + "="*70)
    print("测试 2: 用户回答推断（汉字显示）")
    print("="*70)

    result = run_command_with_correct_encoding(
        ["python", "disambiguate_complaint.py", "心烦",
         "--response", "是的，最近睡眠不好，经常失眠多梦",
         "--use-local", "--pretty"]
    )

    if result:
        print("\n✓ 诉求:")
        print(f"  原始: {result.get('complaint', 'N/A')}")
        print(f"  回答: {result.get('user_response', 'N/A')}")

        symptoms = result.get('inferred_symptoms', [])
        if symptoms:
            print(f"\n✓ 推断的规范症状:")
            for symptom in symptoms:
                print(f"  • {symptom}")

    return result


def test_understand_query():
    """测试诉求理解 - 应该显示汉字"""
    print("\n" + "="*70)
    print("测试 3: 诉求理解（汉字显示）")
    print("="*70)

    result = run_command_with_correct_encoding(
        ["python", "understand_query.py",
         "最近觉得心烦，卵巢囊肿，最近容易疲劳",
         "--mock", "--pretty"]
    )

    if result:
        complaints = result.get('complaints', [])
        print(f"\n✓ 识别了 {len(complaints)} 个诉求:")

        for complaint in complaints:
            raw = complaint.get('raw', 'N/A')
            conf = complaint.get('confidence', 0)
            status = "✓ 明确" if conf >= 0.8 else "⚠ 模糊"

            print(f"\n  {status}: {raw}")
            print(f"    置信度: {conf}")

            terms = complaint.get('normalized_terms', [])
            if terms:
                print(f"    检索词: {', '.join(terms)}")

    return result


def test_recommend_pipeline():
    """测试推荐流程 - 应该显示汉字"""
    print("\n" + "="*70)
    print("测试 4: 推荐流程（汉字显示）")
    print("="*70)

    result = run_command_with_correct_encoding(
        ["python", "recommend_pipeline.py",
         "最近觉得心烦，卵巢囊肿，最近容易疲劳",
         "--mock", "--pretty"]
    )

    if result:
        # 显示第一步：诉求理解
        step1 = result.get('step1_parse', {})
        print(f"\n✓ Step 1: 诉求理解")
        print(f"  明确诉求: {step1.get('clear_count', 0)} 个")
        print(f"  模糊诉求: {step1.get('vague_count', 0)} 个")

        # 显示第二步：澄清
        step2 = result.get('step2_clarify', {})
        resolved = step2.get('resolved_vague', {})
        if resolved:
            print(f"\n✓ Step 2: 澄清结果")
            for original, symptoms in resolved.items():
                print(f"  {original} → {symptoms}")

        # 显示第三步：搜索
        step3 = result.get('step3_search', {})
        print(f"\n✓ Step 3: 搜索")
        print(f"  检索词数: {step3.get('total_results', 0)}")

        # 显示第四步：推荐
        step4 = result.get('step4_recommend', {})
        print(f"\n✓ Step 4: 推荐")
        print(f"  推荐茶饮数: {step4.get('total_recommendations', 0)}")

    return result


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("汉字显示修复 - JSON 输出验证")
    print("="*70)

    # 测试 1
    test_disambiguate()

    # 测试 2
    test_disambiguate_with_response()

    # 测试 3
    test_understand_query()

    # 测试 4
    test_recommend_pipeline()

    print("\n" + "="*70)
    print("✅ 所有测试完成！")
    print("="*70)

    print("\n📝 说明:")
    print("  • 上述所有输出应该显示汉字，而不是乱码")
    print("  • 如果仍然显示乱码，可能是终端编码问题")
    print("  • 可以将输出重定向到文件查看:")
    print("    python show_chinese.py > output.txt")


if __name__ == "__main__":
    main()
