from __future__ import annotations

import argparse
import io
import json
import os
import sys

from tea_match.services.recommendation_service import RecommendationService

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def format_sources(sources: list[str]) -> str:
    return "、".join(str(item) for item in sources if str(item).strip()) or "本地规则/知识库匹配"


def main() -> None:
    parser = argparse.ArgumentParser(description="Show tea recommendations through the production workflow.")
    parser.add_argument("query", help="用户主诉")
    parser.add_argument("--selected-symptoms", nargs="*", default=[], help="前端已选择的症状按钮")
    parser.add_argument("--user-id", default="cli_user", help="memory 用户 ID")
    parser.add_argument("--mock", action="store_true", help="使用本地 mock 理解，不调用 Qwen")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    args = parser.parse_args()

    if args.mock:
        os.environ["USE_MOCK_UNDERSTANDING"] = "1"

    service = RecommendationService()
    try:
        result = service.recommend(args.user_id, args.query, args.selected_symptoms)
    except Exception as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print("推荐失败：" + str(exc))
        raise SystemExit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    recommendations = result.get("top_recommendations", []) or []
    print("\n" + "=" * 70)
    print("中医茶饮推荐系统 - 推荐结果")
    print("=" * 70)
    print(f"用户诉求：{result.get('query', '')}")
    selected = result.get("selected_symptoms", []) or []
    if selected:
        print("已选择症状：" + "、".join(selected))

    if not recommendations:
        print("\n搜索不到结果？请换一个说法")
        return

    print(f"\n为您推荐的 {len(recommendations)} 种茶饮：\n")
    for rec in recommendations:
        print(f"{rec.get('rank')}. {rec.get('name')}")
        print(f"   推荐原因：{rec.get('reason', '与您的主诉匹配')}")
        print(f"   匹配依据：{format_sources(rec.get('match_symptoms', []) or [])}")
        print(f"   阶段优先级：第 {rec.get('stage_priority', '-')} 优先级")

    print("=" * 70)


if __name__ == "__main__":
    main()
