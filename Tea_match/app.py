from __future__ import annotations

import io
import os
import sys
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from tea_match.services.recommendation_service import RecommendationService

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

app = Flask(__name__)
CORS(app)
recommendation_service = RecommendationService()


def normalize_selected_symptoms(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []

    selected: list[str] = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            selected.append(text)
            seen.add(text)
    return selected


@app.route("/", methods=["GET"])
def index():
    return get_frontend_html()


@app.route("/api/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json(silent=True) or {}
        user_query = str(data.get("query") or "").strip()
        selected_symptoms = normalize_selected_symptoms(data.get("selected_symptoms"))
        user_id = str(data.get("user_id") or "anonymous").strip() or "anonymous"

        if not user_query and not selected_symptoms:
            return jsonify({"success": False, "error": "请输入您的主诉或选择症状"}), 400

        result = recommendation_service.recommend(user_id, user_query, selected_symptoms)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/feedback", methods=["POST"])
def feedback():
    try:
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "anonymous").strip() or "anonymous"
        recommendation_id = str(data.get("recommendation_id") or "").strip()
        tea_name = str(data.get("tea_name") or "").strip()
        effect = str(data.get("effect") or "").strip()
        notes = str(data.get("notes") or "").strip()
        adverse_reaction = str(data.get("adverse_reaction") or "").strip()
        days_used = data.get("days_used")

        if not recommendation_id or not tea_name or not effect:
            return jsonify({"success": False, "error": "缺少 recommendation_id、tea_name 或 effect"}), 400

        if days_used not in (None, ""):
            try:
                days_used = int(days_used)
            except (TypeError, ValueError):
                days_used = None
        else:
            days_used = None

        result = recommendation_service.collect_feedback(
            user_id=user_id,
            recommendation_id=recommendation_id,
            tea_name=tea_name,
            effect=effect,
            notes=notes,
            days_used=days_used,
            adverse_reaction=adverse_reaction,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


def get_frontend_html() -> str:
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中医茶饮推荐系统</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            min-height: 100vh;
            font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
            background: #f5f3ee;
            color: #262a24;
            padding: 24px;
        }
        .container {
            width: min(980px, 100%);
            margin: 0 auto;
            background: #fffdfa;
            border: 1px solid #e7dfd2;
            border-radius: 12px;
            box-shadow: 0 16px 45px rgba(77, 61, 39, 0.12);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #2f6f5e 0%, #8c6b35 100%);
            color: #fff;
            padding: 34px 36px;
        }
        header h1 { font-size: 30px; font-weight: 700; margin-bottom: 8px; }
        header p { opacity: 0.92; line-height: 1.7; }
        .content { padding: 34px 36px 40px; }
        .input-section { margin-bottom: 28px; }
        label { display: block; margin-bottom: 10px; font-weight: 700; }
        .input-group { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
        #userInput {
            min-width: 0;
            padding: 14px 15px;
            border: 1px solid #d8d0c3;
            border-radius: 8px;
            font-size: 16px;
            font-family: inherit;
            background: #fff;
        }
        #userInput:focus { outline: 2px solid rgba(47, 111, 94, 0.25); border-color: #2f6f5e; }
        button {
            border: 0;
            border-radius: 8px;
            font-family: inherit;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
        }
        .submit-button {
            padding: 0 28px;
            background: #2f6f5e;
            color: #fff;
            font-size: 16px;
            font-weight: 700;
        }
        .submit-button:hover { background: #275d4f; box-shadow: 0 8px 20px rgba(47, 111, 94, 0.2); transform: translateY(-1px); }
        .example-text { color: #736b60; font-size: 14px; margin-top: 8px; }
        .option-panel { margin-top: 18px; padding: 18px; background: #f7f3ec; border: 1px solid #e5dacb; border-radius: 8px; }
        .option-title { font-weight: 700; margin-bottom: 12px; color: #3a3d35; }
        .symptom-options { display: flex; flex-wrap: wrap; gap: 10px; }
        .symptom-option {
            padding: 9px 14px;
            background: #fffdfa;
            color: #3d463d;
            border: 1px solid #d7cbb9;
            font-size: 14px;
            font-weight: 600;
        }
        .symptom-option:hover { border-color: #2f6f5e; transform: translateY(-1px); }
        .symptom-option.selected { background: #2f6f5e; color: #fff; border-color: #2f6f5e; }
        .loading, .results-section, .error { display: none; }
        .loading.show, .results-section.show, .error.show { display: block; }
        .loading { padding: 18px; color: #2f6f5e; font-weight: 700; }
        .error { background: #fff0ee; color: #a53024; padding: 14px 16px; border-left: 4px solid #c74335; border-radius: 8px; margin: 18px 0; }
        .user-query { background: #f7f3ec; padding: 14px 16px; border-left: 4px solid #2f6f5e; border-radius: 8px; margin-bottom: 18px; }
        .selected-summary, .memory-summary { margin-top: 8px; color: #5d665d; font-size: 14px; }
        .recommendations h2 { font-size: 22px; margin-bottom: 18px; }
        .recommendation-item { border: 1px solid #e2d8ca; border-radius: 8px; padding: 18px; margin-bottom: 14px; background: #fff; }
        .recommendation-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
        .rank { width: 34px; height: 34px; border-radius: 50%; background: #2f6f5e; color: #fff; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; }
        .rank.first { background: #b9842d; }
        .rank.second { background: #697a72; }
        .rank.third { background: #8d5d35; }
        .tea-name { font-size: 22px; font-weight: 700; }
        .match-info { margin-bottom: 12px; }
        .match-count { display: inline-block; background: #e9f3ee; color: #24584a; padding: 6px 11px; border-radius: 999px; font-size: 13px; font-weight: 700; }
        .reason { line-height: 1.7; color: #55584f; }
        .reason-label { color: #2f6f5e; font-weight: 700; }
        .symptoms-list { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee5da; color: #60645c; }
        .symptom-tag { display: inline-block; background: #f0eadf; color: #5c513f; padding: 4px 9px; border-radius: 999px; margin: 6px 6px 0 0; font-size: 13px; }
        .feedback-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
        .feedback-button { padding: 7px 11px; background: #f0eadf; color: #4d463a; border: 1px solid #d9ccb8; font-size: 13px; font-weight: 700; }
        .feedback-button:hover { background: #e6ddcf; transform: translateY(-1px); }
        .feedback-status { color: #2f6f5e; font-size: 13px; margin-left: 6px; }
        .no-results { background: #fff8e6; color: #7a5414; padding: 18px; border-left: 4px solid #c9902e; border-radius: 8px; font-weight: 700; }
        .footer { border-top: 1px solid #e8dfd2; padding: 18px 36px; color: #777066; font-size: 13px; text-align: center; }
        @media (max-width: 720px) {
            body { padding: 12px; }
            header, .content { padding: 24px 20px; }
            .input-group { grid-template-columns: 1fr; }
            .submit-button { min-height: 46px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>中医茶饮推荐系统</h1>
            <p>根据用户主诉、已选择症状、历史反馈和本地规则知识库进行茶饮匹配。</p>
        </header>

        <div class="content">
            <div class="input-section">
                <label for="userInput">请描述您的主诉</label>
                <div class="input-group">
                    <input id="userInput" type="text" placeholder="例如：我的胃不舒服，吃完饭觉得很胀">
                    <button class="submit-button" type="button" onclick="submitQuery()">获取推荐</button>
                </div>
                <p class="example-text">可以直接输入一句话，也可以同时点击下方症状选项。</p>

                <div class="option-panel">
                    <div class="option-title">常见症状/体质/五脏方向</div>
                    <div class="symptom-options">
                        <button class="symptom-option" type="button" data-value="失眠">失眠</button>
                        <button class="symptom-option" type="button" data-value="易怒">易怒</button>
                        <button class="symptom-option" type="button" data-value="口苦">口苦</button>
                        <button class="symptom-option" type="button" data-value="饭后饱胀">饭后饱胀</button>
                        <button class="symptom-option" type="button" data-value="反酸">反酸</button>
                        <button class="symptom-option" type="button" data-value="食欲不振">食欲不振</button>
                        <button class="symptom-option" type="button" data-value="疲劳乏力">疲劳乏力</button>
                        <button class="symptom-option" type="button" data-value="便秘">便秘</button>
                        <button class="symptom-option" type="button" data-value="眼干">眼干</button>
                        <button class="symptom-option" type="button" data-value="眼疲劳">眼疲劳</button>
                        <button class="symptom-option" type="button" data-value="湿热体质">湿热体质</button>
                        <button class="symptom-option" type="button" data-value="气虚体质">气虚体质</button>
                        <button class="symptom-option" type="button" data-value="肝功能障碍">肝功能障碍</button>
                        <button class="symptom-option" type="button" data-value="肾功能障碍">肾功能障碍</button>
                    </div>
                </div>
            </div>

            <div id="loading" class="loading">正在分析主诉并匹配茶饮...</div>
            <div id="error" class="error"></div>

            <div id="results" class="results-section">
                <div class="user-query">
                    <strong>您的输入：</strong><span id="queryText"></span>
                    <div id="selectedSummary" class="selected-summary"></div>
                    <div id="memorySummary" class="memory-summary"></div>
                </div>
                <div class="recommendations">
                    <h2 id="recommendationsTitle">为您推荐的茶饮：</h2>
                    <div id="recommendationsList"></div>
                </div>
            </div>
        </div>

        <div class="footer">推荐结果用于养生茶饮匹配参考，不替代医疗诊断和治疗。</div>
    </div>

    <script>
        const selectedSymptoms = new Set();
        let latestRecommendationId = '';

        function getUserId() {
            let userId = localStorage.getItem('tea_user_id');
            if (!userId) {
                userId = 'web_' + Math.random().toString(16).slice(2) + Date.now().toString(16);
                localStorage.setItem('tea_user_id', userId);
            }
            return userId;
        }

        function toggleSymptomOption(button) {
            const value = button.dataset.value;
            if (selectedSymptoms.has(value)) {
                selectedSymptoms.delete(value);
                button.classList.remove('selected');
            } else {
                selectedSymptoms.add(value);
                button.classList.add('selected');
            }
        }

        async function submitQuery() {
            const userInput = document.getElementById('userInput');
            const query = userInput.value.trim();
            const selected = Array.from(selectedSymptoms);

            if (!query && selected.length === 0) {
                showError('请输入您的主诉或选择症状');
                return;
            }

            document.getElementById('loading').classList.add('show');
            document.getElementById('results').classList.remove('show');
            document.getElementById('error').classList.remove('show');

            try {
                const response = await fetch('/api/recommend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: getUserId(), query, selected_symptoms: selected })
                });
                const data = await response.json();
                document.getElementById('loading').classList.remove('show');

                if (data.success) {
                    latestRecommendationId = data.recommendation_id || '';
                    displayResults(data);
                } else {
                    showError(data.error || '推荐失败，请稍后重试');
                }
            } catch (error) {
                document.getElementById('loading').classList.remove('show');
                showError('网络错误：' + error.message);
            }
        }

        function displayResults(data) {
            const selected = data.selected_symptoms || [];
            const queryText = data.query || (selected.length ? '仅选择症状' : '');
            document.getElementById('queryText').textContent = queryText;
            document.getElementById('selectedSummary').textContent = selected.length ? '已选择：' + selected.join('、') : '';
            const memory = data.memory_summary || {};
            const preferred = memory.preferred_teas || [];
            const avoid = memory.avoid_teas || [];
            const memoryText = [];
            if (preferred.length) memoryText.push('历史反馈较好：' + preferred.join('、'));
            if (avoid.length) memoryText.push('需谨慎：' + avoid.join('、'));
            document.getElementById('memorySummary').textContent = memoryText.join('；');

            const recommendationsList = document.getElementById('recommendationsList');
            const recommendationsTitle = document.getElementById('recommendationsTitle');
            const recommendations = data.top_recommendations || [];
            const recommendationCount = recommendations.length;
            recommendationsList.innerHTML = '';

            if (recommendationCount === 0) {
                recommendationsTitle.textContent = '为您推荐的茶饮：';
                recommendationsList.innerHTML = '<div class="no-results">搜索不到结果？请换一个说法</div>';
                document.getElementById('results').classList.add('show');
                return;
            }

            recommendationsTitle.textContent = `为您推荐的 ${recommendationCount} 种茶饮：`;
            recommendations.forEach((rec, index) => {
                const rankClass = index === 0 ? 'first' : (index === 1 ? 'second' : (index === 2 ? 'third' : ''));
                const symptoms = rec.match_symptoms || [];
                recommendationsList.innerHTML += `
                    <div class="recommendation-item">
                        <div class="recommendation-head">
                            <span class="rank ${rankClass}">${rec.rank}</span>
                            <span class="tea-name">${rec.name}</span>
                        </div>
                        <div class="match-info"><span class="match-count">${rec.match_count} 个匹配依据</span></div>
                        <div class="reason"><span class="reason-label">推荐原因：</span>${rec.reason}</div>
                        <div class="symptoms-list">
                            <strong>匹配依据：</strong>
                            ${symptoms.map(s => `<span class="symptom-tag">${s}</span>`).join('')}
                        </div>
                        <div class="feedback-actions">
                            <button class="feedback-button" type="button" onclick="sendFeedback('${rec.name}', 'effective', this)">有效</button>
                            <button class="feedback-button" type="button" onclick="sendFeedback('${rec.name}', 'ineffective', this)">没效果</button>
                            <button class="feedback-button" type="button" onclick="sendFeedback('${rec.name}', 'adverse', this)">不适</button>
                            <span class="feedback-status"></span>
                        </div>
                    </div>
                `;
            });
            document.getElementById('results').classList.add('show');
        }

        async function sendFeedback(teaName, effect, button) {
            if (!latestRecommendationId) return;
            const status = button.parentElement.querySelector('.feedback-status');
            status.textContent = '提交中...';
            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: getUserId(),
                        recommendation_id: latestRecommendationId,
                        tea_name: teaName,
                        effect: effect
                    })
                });
                const data = await response.json();
                status.textContent = data.success ? '已记录' : (data.error || '记录失败');
            } catch (error) {
                status.textContent = '记录失败';
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
        }

        document.querySelectorAll('.symptom-option').forEach(button => {
            button.addEventListener('click', () => toggleSymptomOption(button));
        });

        document.getElementById('userInput').addEventListener('keydown', event => {
            if (event.key === 'Enter') submitQuery();
        });

        window.addEventListener('load', () => document.getElementById('userInput').focus());
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("中医茶饮推荐系统 - 后端服务启动")
    print("=" * 70)
    port = int(os.getenv("PORT", "5000"))
    print(f"前端访问地址: http://localhost:{port}")
    print(f"API 端点: http://localhost:{port}/api/recommend")
    print("=" * 70 + "\n")
    try:
        app.run(debug=False, host="0.0.0.0", port=port)
    finally:
        print("\n" + "=" * 70)
        print("中医茶饮推荐系统 - 后端服务关闭")
        print("=" * 70)
