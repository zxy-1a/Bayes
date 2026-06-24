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


def normalize_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


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
@app.route("/api/mini_program/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json(silent=True) or {}
        user_query = str(data.get("query") or "").strip()
        selected_symptoms = normalize_selected_symptoms(data.get("selected_symptoms"))
        clarification_answers = normalize_selected_symptoms(data.get("clarification_answers"))
        focus_symptoms = normalize_selected_symptoms(data.get("focus_symptoms"))
        tongue_result = normalize_json_dict(data.get("tongue_result"))
        sublingual_result = normalize_json_dict(data.get("sublingual_result"))
        pulse_result = normalize_json_dict(data.get("pulse_result"))
        user_id = str(data.get("user_id") or "anonymous").strip() or "anonymous"

        if not user_query and not selected_symptoms and not clarification_answers and not focus_symptoms and not tongue_result and not sublingual_result and not pulse_result:
            return jsonify({"success": False, "error": "请输入您的主诉、选择症状或提供舌脉结果"}), 400

        result = recommendation_service.recommend(
            user_id,
            user_query,
            selected_symptoms,
            clarification_answers=clarification_answers,
            focus_symptoms=focus_symptoms,
            tongue_result=tongue_result,
            sublingual_result=sublingual_result,
            pulse_result=pulse_result,
        )
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
    <title>中医茶饮智能推荐</title>
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
        .content { padding: 28px 32px 32px; }
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
        .ghost-button { padding: 10px 14px; background: #f0eadf; color: #4d463a; border: 1px solid #d9ccb8; font-size: 14px; font-weight: 700; }
        .ghost-button:hover { background: #e6ddcf; transform: translateY(-1px); }
        .example-text { color: #736b60; font-size: 14px; margin-top: 8px; }
        .option-panel { margin-top: 18px; padding: 18px; background: #f7f3ec; border: 1px solid #e5dacb; border-radius: 8px; }
        .option-title { font-weight: 700; margin-bottom: 12px; color: #3a3d35; }
        .symptom-options, .clarification-options { display: flex; flex-wrap: wrap; gap: 10px; }
        .symptom-option, .clarification-button {
            padding: 9px 14px;
            background: #fffdfa;
            color: #3d463d;
            border: 1px solid #d7cbb9;
            font-size: 14px;
            font-weight: 600;
        }
        .symptom-option:hover, .clarification-button:hover { border-color: #2f6f5e; transform: translateY(-1px); }
        .symptom-option.selected { background: #2f6f5e; color: #fff; border-color: #2f6f5e; }
        .clarification-button.selected { background: #2f6f5e; color: #fff; border-color: #2f6f5e; }
        .clarification-hint { margin-top: 10px; color: #6b6458; font-size: 13px; }
        .loading, .results-section, .error, .clarification-section { display: none; }
        .loading.show, .results-section.show, .error.show, .clarification-section.show { display: block; }
        .loading { padding: 18px; color: #2f6f5e; font-weight: 700; }
        .error { background: #fff0ee; color: #a53024; padding: 14px 16px; border-left: 4px solid #c74335; border-radius: 8px; margin: 18px 0; }
        .clarification-card { background: #f7f3ec; border: 1px solid #e5dacb; border-radius: 8px; padding: 18px; margin-bottom: 18px; }
        .clarification-reason { color: #7b6a52; font-size: 14px; line-height: 1.6; margin-bottom: 10px; }
        .clarification-question { font-size: 20px; font-weight: 700; color: #2a3028; margin-bottom: 14px; }
        .clarification-summary { margin-top: 12px; color: #5d665d; font-size: 14px; }
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
        .chat-shell { display: flex; flex-direction: column; gap: 14px; }
        .chat-toolbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
        .toolbar-actions { display: flex; flex-wrap: wrap; gap: 8px; }
        .symptom-picker { padding: 16px; background: #f7f3ec; border: 1px solid #e5dacb; border-radius: 10px; }
        .active-symptoms { margin-top: 12px; color: #5f675e; font-size: 14px; min-height: 22px; }
        .active-chip { display: inline-block; background: #e9f3ee; color: #24584a; padding: 5px 10px; border-radius: 999px; margin: 0 8px 8px 0; font-size: 13px; font-weight: 700; }
        .chat-messages { min-height: 58vh; max-height: 64vh; overflow-y: auto; padding: 6px 4px 10px; display: flex; flex-direction: column; gap: 14px; }
        .message-row { display: flex; width: 100%; }
        .message-row.assistant { justify-content: flex-start; }
        .message-row.user { justify-content: flex-end; }
        .bubble { max-width: min(760px, 86%); border-radius: 14px; padding: 14px 16px; line-height: 1.7; box-shadow: 0 8px 24px rgba(77, 61, 39, 0.08); }
        .assistant-bubble { background: #f7f3ec; border: 1px solid #e5dacb; color: #31362f; }
        .user-bubble { background: #2f6f5e; color: #fff; }
        .message-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; opacity: 0.85; }
        .message-meta { margin-top: 10px; color: #6c675e; font-size: 13px; }
        .message-row.user .message-meta { color: rgba(255,255,255,0.82); }
        .composer { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: stretch; }
        .composer-surface { min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 10px 12px; border: 1px solid #d8d0c3; border-radius: 10px; background: #fff; }
        .composer-surface:focus-within { outline: 2px solid rgba(47, 111, 94, 0.25); border-color: #2f6f5e; }
        .input-chips { display: contents; }
        .input-chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 6px 10px; border: 1px solid #c9ddcf; border-radius: 999px; background: #e9f3ee; color: #24584a; font-size: 13px; font-weight: 700; }
        .input-chip-text { white-space: nowrap; }
        .input-chip-remove { width: 18px; height: 18px; border-radius: 50%; border: 0; background: rgba(36, 88, 74, 0.12); color: #24584a; font-size: 12px; font-weight: 700; padding: 0; display: inline-flex; align-items: center; justify-content: center; }
        .input-chip-remove:hover { background: rgba(36, 88, 74, 0.2); transform: none; }
        .composer-input { flex: 1 1 240px; min-width: 180px; padding: 6px 2px; border: 0; font-size: 16px; font-family: inherit; background: transparent; }
        .composer-input:focus { outline: none; }
        .grouped-recommendations { display: flex; flex-direction: column; gap: 18px; margin-top: 16px; }
        .group-section { border-top: 1px solid #eadfce; padding-top: 16px; }
        .group-section:first-child { border-top: 0; padding-top: 0; }
        .group-title { font-size: 18px; font-weight: 700; color: #2a3028; margin-bottom: 8px; }
        .group-meta { color: #6b6458; font-size: 13px; margin-bottom: 12px; }
        .clarification-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
        .clarification-button { padding: 9px 14px; background: #fffdfa; color: #3d463d; border: 1px solid #d7cbb9; font-size: 14px; font-weight: 600; }
        .assistant-card-list { margin-top: 14px; display: flex; flex-direction: column; gap: 12px; }
        .chat-card { background: #fffdfa; border: 1px solid #e2d8ca; border-radius: 10px; padding: 16px; }
        .loading { display: none; padding: 12px 14px; color: #2f6f5e; font-weight: 700; }
        .loading.show { display: block; }
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
            <h1>中医茶饮智能推荐系统</h1>
            <p>根据用户主诉、已选择症状、进行茶饮匹配；当主诉仍较宽泛时，会先进一步澄清再推荐。</p>
        </header>

        <div class="content">
            <div class="chat-shell">
                <div class="chat-toolbar">
                    <div>
                        <div class="option-title">聊天式问诊入口</div>
                        <p class="example-text">请直接向系统描述您的主诉，或选择下方症状</p>
                    </div>
                    <div class="toolbar-actions">
                        <button class="ghost-button" type="button" onclick="clearSelectedSymptoms()">清空症状</button>
                        <button class="ghost-button" type="button" onclick="resetConversation()">重新开始</button>
                    </div>
                </div>

                <div class="symptom-picker">
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
                    <div id="activeSymptoms" class="active-symptoms">当前未选择额外症状按键</div>
                </div>

                <div id="chatMessages" class="chat-messages"></div>
                <div id="loading" class="loading">系统正在分析您的主诉...</div>
                <div id="error" class="error"></div>

                <div class="composer">
                    <div class="composer-surface">
                        <div id="selectedInputChips" class="input-chips"></div>
                        <input id="userInput" class="composer-input" type="text" placeholder="例如：我的胃不舒服，吃完饭觉得很胀">
                    </div>
                    <button class="submit-button" type="button" onclick="submitChat()">发送</button>
                </div>
            </div>
        </div>

        <div class="footer">推荐结果用于养生茶饮匹配参考，不替代医疗诊断和治疗。</div>
    </div>

            <script>
        const selectedSymptoms = new Set();
        const sessionRecommendedTeas = new Set();
        let sessionSymptomHistory = [];
        let sessionRecommendationGroups = [];
        let sessionPriorityPrompted = false;
        let clarificationAnswers = [];
        let focusSymptoms = [];
        let pendingFocusSelection = [];
        let latestRecommendationId = '';
        let pendingClarification = null;
        let baseQuery = '';

        function getUserId() {
            let userId = localStorage.getItem('tea_user_id');
            if (!userId) {
                userId = 'web_' + Math.random().toString(16).slice(2) + Date.now().toString(16);
                localStorage.setItem('tea_user_id', userId);
            }
            return userId;
        }

        function escapeHtml(text) {
            return String(text || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function scrollChatToBottom() {
            const chat = document.getElementById('chatMessages');
            chat.scrollTop = chat.scrollHeight;
        }

        function setLoading(show) {
            const loading = document.getElementById('loading');
            loading.classList.toggle('show', Boolean(show));
            if (show) scrollChatToBottom();
        }

        function setError(message) {
            const error = document.getElementById('error');
            if (!message) {
                error.textContent = '';
                error.classList.remove('show');
                return;
            }
            error.textContent = message;
            error.classList.add('show');
        }

        function renderSelectedInputChips() {
            const container = document.getElementById('selectedInputChips');
            if (!container) return;
            container.innerHTML = '';
            Array.from(selectedSymptoms).forEach(value => {
                const chip = document.createElement('span');
                chip.className = 'input-chip';

                const textNode = document.createElement('span');
                textNode.className = 'input-chip-text';
                textNode.textContent = value;

                const removeButton = document.createElement('button');
                removeButton.type = 'button';
                removeButton.className = 'input-chip-remove';
                removeButton.setAttribute('aria-label', `\u5220\u9664${value}`);
                removeButton.textContent = '\u00d7';
                removeButton.addEventListener('click', () => removeSelectedSymptom(value));

                chip.appendChild(textNode);
                chip.appendChild(removeButton);
                container.appendChild(chip);
            });
        }

        function updateSelectedSymptomsUI() {
            document.querySelectorAll('.symptom-option').forEach(button => {
                const value = button.dataset.value;
                button.classList.toggle('selected', selectedSymptoms.has(value));
            });
            renderSelectedInputChips();
            const active = Array.from(selectedSymptoms);
            const activeSymptoms = document.getElementById('activeSymptoms');
            if (!active.length) {
                activeSymptoms.textContent = '\u5f53\u524d\u672a\u9009\u62e9\u989d\u5916\u75c7\u72b6\u6309\u952e';
                return;
            }
            activeSymptoms.innerHTML = active.map(item => `<span class="active-chip">${escapeHtml(item)}</span>`).join('');
        }

        function resetSessionPriorityState() {
            sessionRecommendedTeas.clear();
            sessionSymptomHistory = [];
            sessionRecommendationGroups = [];
            sessionPriorityPrompted = false;
        }

        function clearConversationState() {
            clarificationAnswers = [];
            focusSymptoms = [];
            pendingFocusSelection = [];
            pendingClarification = null;
            latestRecommendationId = '';
            baseQuery = '';
            resetSessionPriorityState();
            setError('');
            setLoading(false);
        }

        function prepareNextRound() {
            selectedSymptoms.clear();
            updateSelectedSymptomsUI();
            clarificationAnswers = [];
            focusSymptoms = [];
            pendingFocusSelection = [];
            pendingClarification = null;
            baseQuery = '';
            setError('');
        }

        function appendMessage(role, html) {
            const row = document.createElement('div');
            row.className = `message-row ${role}`;
            row.innerHTML = html;
            document.getElementById('chatMessages').appendChild(row);
            scrollChatToBottom();
        }

        function appendWelcomeMessage() {
            appendMessage('assistant', `
                <div class="bubble assistant-bubble">
                    <div class="message-title">\u667a\u80fd\u95ee\u8bca</div>
                    <div>\u60a8\u597d\uff0c\u60a8\u53ef\u4ee5\u50cf\u804a\u5929\u4e00\u6837\u76f4\u63a5\u63cf\u8ff0\u4e3b\u8bc9\u3002\u6211\u4f1a\u5411\u60a8\u63a8\u8350\u9002\u5408\u7684\u8336\u996e\u3002</div>
                    <div class="message-meta">\u4f8b\u5982\uff1a\u80c3\u4e0d\u8212\u670d\u3001\u6700\u8fd1\u603b\u89c9\u5f97\u5fc3\u70e6\u3001\u6e7f\u70ed\u4f53\u8d28\u3001\u80be\u529f\u80fd\u969c\u788d\u3002</div>
                </div>
            `);
        }

        function appendUserMessage(text) {
            appendMessage('user', `
                <div class="bubble user-bubble">
                    <div>${escapeHtml(text)}</div>
                </div>
            `);
        }

        function buildUserMessageText(text, selected) {
            const parts = [];
            if (selected.length) parts.push(selected.join('\uff1b'));
            if (text) parts.push(text);
            return parts.join('\uff1b');
        }

        function buildSelectionSummary(selected, clarified) {
            const parts = [];
            if (selected.length) parts.push('\u5df2\u9009\u75c7\u72b6\uff1a' + selected.join('\u3001'));
            if (clarified.length) parts.push('\u5df2\u786e\u8ba4\uff1a' + clarified.join('\u3001'));
            return parts.join('\uff1b');
        }

        function appendClarificationMessage(data) {
            const clarification = data.clarification || {};
            const options = clarification.options || [];
            const selected = data.selected_symptoms || [];
            const clarified = data.clarification_answers || [];
            const summary = buildSelectionSummary(selected, clarified);
            const groupLabel = clarification.group_label ? `\u5f53\u524d\u4f18\u5148\u786e\u8ba4\uff1a${clarification.group_label}` : '';

            if (clarification.mode === 'symptom_focus') {
                pendingFocusSelection = [];
                const optionsHtml = options.map(option => {
                    const label = escapeHtml(option.label || option.value || '');
                    const value = escapeHtml(option.value || option.label || '');
                    return `<button class="clarification-button" type="button" data-focus-value="${value}" onclick="toggleFocusSymptomOption(this)">${label}</button>`;
                }).join('');
                appendMessage('assistant', `
                    <div class="bubble assistant-bubble">
                        <div class="message-title">\u667a\u80fd\u95ee\u8bca</div>
                        <div>${escapeHtml(clarification.question || '\u8bf7\u9009\u62e9 1~2 \u4e2a\u60a8\u6700\u60f3\u4f18\u5148\u6539\u5584\u7684\u75c7\u72b6')}</div>
                        <div class="message-meta">${escapeHtml([clarification.reason || '', groupLabel, summary].filter(Boolean).join('\uff1b'))}</div>
                        <div class="clarification-actions">${optionsHtml}</div>
                        <div class="clarification-hint">\u6700\u591a\u53ea\u80fd\u9009 2 \u4e2a\u75c7\u72b6</div>
                        <div class="clarification-actions">
                            <button class="ghost-button" type="button" onclick="submitSymptomFocusSelection()">\u6309\u8fd9 1~2 \u4e2a\u75c7\u72b6\u7ee7\u7eed\u63a8\u8350</button>
                        </div>
                    </div>
                `);
                return;
            }

            const optionsHtml = options.map(option => {
                const label = escapeHtml(option.label || option.value || '');
                const value = escapeHtml(option.value || option.label || '');
                return `<button class="clarification-button" type="button" onclick="submitClarificationChoice('${value}', '${label}')">${label}</button>`;
            }).join('');
            appendMessage('assistant', `
                <div class="bubble assistant-bubble">
                    <div class="message-title">\u667a\u80fd\u95ee\u8bca</div>
                    <div>${escapeHtml(clarification.question || '\u8bf7\u518d\u786e\u8ba4\u4e00\u4e0b\u60a8\u7684\u60c5\u51b5')}</div>
                    <div class="message-meta">${escapeHtml([clarification.reason || '', groupLabel, summary].filter(Boolean).join('\uff1b'))}</div>
                    <div class="clarification-actions">${optionsHtml}</div>
                </div>
            `);
        }

        function extractTeaNamesFromData(data) {
            const groupedRecommendations = data.grouped_recommendations || [];
            const directRecommendations = data.top_recommendations || [];
            const names = [];
            groupedRecommendations.forEach(group => {
                (group.recommendations || []).forEach(item => {
                    if (item && item.name) names.push(item.name);
                });
            });
            directRecommendations.forEach(item => {
                if (item && item.name) names.push(item.name);
            });
            return dedupe(names);
        }

        function extractSymptomOptionsFromData(data) {
            const groupedRecommendations = data.grouped_recommendations || [];
            const options = [];
            groupedRecommendations.forEach(group => {
                const label = String(group.group_label || '').trim();
                if (label) options.push(label);
                (group.matched_terms || []).forEach(term => {
                    const text = String(term || '').trim();
                    if (text) options.push(text);
                });
            });
            if (!options.length) {
                (data.selected_symptoms || []).forEach(item => options.push(item));
                (data.all_selected_symptoms || []).forEach(item => options.push(item));
                (data.complaints || []).forEach(item => {
                    const raw = String((item || {}).raw || '').trim();
                    if (raw) options.push(raw);
                });
            }
            return dedupe(options);
        }

        function rememberRecommendationContext(data) {
            extractTeaNamesFromData(data).forEach(name => sessionRecommendedTeas.add(name));
            extractSymptomOptionsFromData(data).forEach(item => {
                if (!sessionSymptomHistory.includes(item)) sessionSymptomHistory.push(item);
            });
            const groups = data.grouped_recommendations || [];
            groups.forEach(group => {
                const label = String(group.group_label || '').trim();
                const matchedTerms = dedupe([
                    label,
                    ...((group.matched_terms || []).map(item => String(item || '').trim()).filter(Boolean)),
                ]);
                const existing = sessionRecommendationGroups.find(item => item.group_label === label);
                if (existing) {
                    existing.matched_terms = dedupe([...(existing.matched_terms || []), ...matchedTerms]);
                    existing.recommendations = dedupeRecommendations([...(existing.recommendations || []), ...((group.recommendations || []).filter(Boolean))]);
                    return;
                }
                sessionRecommendationGroups.push({
                    group_label: label,
                    matched_terms: matchedTerms,
                    recommendations: dedupeRecommendations((group.recommendations || []).filter(Boolean)),
                });
            });
        }

        function dedupeRecommendations(items) {
            const results = [];
            const seen = new Set();
            (items || []).forEach(item => {
                if (!item || !item.name) return;
                const key = String(item.name).trim();
                if (!key || seen.has(key)) return;
                seen.add(key);
                results.push(item);
            });
            return results;
        }

        function buildPriorityRecommendationData(focusValues) {
            const normalizedFocus = new Set((focusValues || []).map(item => String(item || '').trim()).filter(Boolean));
            const matchedGroups = sessionRecommendationGroups.filter(group => {
                const candidates = [
                    String(group.group_label || '').trim(),
                    ...((group.matched_terms || []).map(item => String(item || '').trim()).filter(Boolean)),
                ];
                return candidates.some(item => normalizedFocus.has(item));
            });
            const groupedRecommendations = matchedGroups.map(group => ({
                group_label: group.group_label,
                matched_terms: group.matched_terms || [],
                recommendations: dedupeRecommendations(group.recommendations || []).slice(0, 3),
            }));
            const topRecommendations = dedupeRecommendations(
                groupedRecommendations.flatMap(group => group.recommendations || [])
            ).slice(0, 3);
            return {
                success: true,
                selected_symptoms: [],
                clarification_answers: [],
                focus_symptoms: [...normalizedFocus],
                memory_summary: {},
                grouped_recommendations: groupedRecommendations,
                top_recommendations: topRecommendations,
                local_priority_result: true,
            };
        }

        function shouldPromptPrioritySelection() {
            return sessionRecommendedTeas.size > 3 && sessionSymptomHistory.length >= 2 && !sessionPriorityPrompted;
        }

        function buildPriorityPromptData() {
            return {
                clarification: {
                    mode: 'symptom_focus',
                    question: '\u63a8\u8350\u7684\u8336\u996e\u592a\u591a\u53ef\u80fd\u4f1a\u9020\u6210\u8c03\u7406\u4e0d\u591f\u51c6\u786e\u5662\uff0c\u8bf7\u6839\u636e\u4f18\u5148\u7ea7\u9009\u62e9 1~2 \u79cd\u75c7\u72b6\uff0c\u6211\u4f1a\u4e3a\u60a8\u7efc\u5408\u53c2\u8003\u51fa\u6700\u5408\u9002\u7684\u8336\u996e\u3002',
                    reason: '\u5f53\u524d\u9875\u9762\u91cc\u7d2f\u8ba1\u5173\u8054\u5230\u7684\u4e0d\u91cd\u590d\u8336\u996e\u5df2\u7ecf\u8d85\u8fc7 3 \u79cd\uff0c\u5148\u6536\u7a84\u4f18\u5148\u75c7\u72b6\u4f1a\u66f4\u51c6\u786e\u3002',
                    options: sessionSymptomHistory.map(item => ({ label: item, value: item })),
                    max_select: 2,
                },
                selected_symptoms: [],
                clarification_answers: [],
            };
        }

        function maybePromptPrioritySelection() {
            if (!shouldPromptPrioritySelection()) return false;
            sessionPriorityPrompted = true;
            pendingClarification = { mode: 'symptom_focus' };
            appendClarificationMessage(buildPriorityPromptData());
            return true;
        }

        function buildRecommendationCards(recommendations) {
            return (recommendations || []).map((rec, index) => {
                const rankClass = index === 0 ? 'first' : (index === 1 ? 'second' : (index === 2 ? 'third' : ''));
                const symptoms = rec.match_symptoms || [];
                return `
                    <div class="recommendation-item">
                        <div class="recommendation-head">
                            <span class="rank ${rankClass}">${rec.rank}</span>
                            <span class="tea-name">${escapeHtml(rec.name)}</span>
                        </div>
                        
                        <div class="reason"><span class="reason-label">\u63a8\u8350\u539f\u56e0\uff1a</span>${escapeHtml(rec.reason)}</div>
                        <div class="symptoms-list">
                            <strong>\u5339\u914d\u4f9d\u636e\uff1a</strong>
                            ${symptoms.map(item => `<span class="symptom-tag">${escapeHtml(item)}</span>`).join('')}
                        </div>
                        
                    </div>
                `;
            }).join('');
        }

        function appendRecommendationMessage(data) {
            const recommendations = data.top_recommendations || [];
            const groupedRecommendations = data.grouped_recommendations || [];
            const selected = data.selected_symptoms || [];
            const clarified = data.clarification_answers || [];
            const memory = data.memory_summary || {};
            const preferred = memory.preferred_teas || [];
            const avoid = memory.avoid_teas || [];
            const summary = buildSelectionSummary(selected, clarified);
            const memoryParts = [];
            if (preferred.length) memoryParts.push('\u5386\u53f2\u53cd\u9988\u8f83\u597d\uff1a' + preferred.join('\u3001'));
            if (avoid.length) memoryParts.push('\u9700\u8c28\u614e\uff1a' + avoid.join('\u3001'));
            const intro = groupedRecommendations.length > 1
                ? '\u5df2\u6309\u4e0d\u540c\u75c7\u72b6\u65b9\u5411\u5206\u522b\u4e3a\u60a8\u6574\u7406\u63a8\u8350\u3002'
                : (recommendations.length ? `\u5df2\u4e3a\u60a8\u6574\u7406\u51fa ${recommendations.length} \u79cd\u66f4\u5339\u914d\u7684\u8336\u996e\u3002` : '\u641c\u7d22\u4e0d\u5230\u7ed3\u679c\uff1f\u8bf7\u6362\u4e00\u4e2a\u8bf4\u6cd5\u3002');

            let cardsHtml = '';
            if (groupedRecommendations.length) {
                cardsHtml = `
                    <div class="grouped-recommendations">
                        ${groupedRecommendations.map(group => `
                            <div class="group-section">
                                <div class="group-title">\u9488\u5bf9\u300c${escapeHtml(group.group_label || '\u5f53\u524d\u4e3b\u8bc9')}\u300d</div>
                                <div class="group-meta">${escapeHtml((group.matched_terms || []).join('\u3001'))}</div>
                                ${buildRecommendationCards(group.recommendations || [])}
                            </div>
                        `).join('')}
                    </div>
                `;
            } else if (recommendations.length) {
                cardsHtml = `<div class="assistant-card-list">${buildRecommendationCards(recommendations)}</div>`;
            }

            appendMessage('assistant', `
                <div class="bubble assistant-bubble">
                    <div class="message-title">\u667a\u80fd\u95ee\u8bca</div>
                    <div>${escapeHtml(intro)}</div>
                    <div class="message-meta">${escapeHtml([summary, ...memoryParts].filter(Boolean).join('\uff1b'))}</div>
                    ${cardsHtml}
                </div>
            `);

            if (recommendations.length || groupedRecommendations.length) {
                const usedFocusSymptoms = (data.focus_symptoms || []).length > 0;
                const isLocalPriorityResult = Boolean(data.local_priority_result);
                if (!isLocalPriorityResult) {
                    rememberRecommendationContext(data);
                }
                prepareNextRound();
                if (usedFocusSymptoms) {
                    resetSessionPriorityState();
                }
                if (!usedFocusSymptoms && !isLocalPriorityResult && maybePromptPrioritySelection()) {
                    return;
                }
                appendMessage('assistant', `
                    <div class="bubble assistant-bubble">
                        <div class="message-title">智能问诊</div>
                        <div>还需要我为您推荐什么吗？如果您有新的主诉，直接继续告诉我，我会为您开启新一轮问答。</div>
                        <div class="message-meta">上一轮已确认的症状不会自动带入，您也可以重新点击上方症状按键。</div>
                    </div>
                `);
            }
        }

        function resetConversation() {
            selectedSymptoms.clear();
            updateSelectedSymptomsUI();
            clearConversationState();
            document.getElementById('chatMessages').innerHTML = '';
            document.getElementById('userInput').value = '';
            appendWelcomeMessage();
        }

        function clearSelectedSymptoms() {
            selectedSymptoms.clear();
            updateSelectedSymptomsUI();
            clarificationAnswers = [];
            focusSymptoms = [];
            pendingFocusSelection = [];
            pendingClarification = null;
            latestRecommendationId = '';
            baseQuery = '';
            setError('');
        }

        function removeSelectedSymptom(value) {
            selectedSymptoms.delete(value);
            clarificationAnswers = [];
            focusSymptoms = [];
            pendingFocusSelection = [];
            pendingClarification = null;
            latestRecommendationId = '';
            baseQuery = '';
            setError('');
            updateSelectedSymptomsUI();
            document.getElementById('userInput').focus();
        }

        function toggleSymptomOption(button) {
            const value = button.dataset.value;
            if (selectedSymptoms.has(value)) {
                selectedSymptoms.delete(value);
            } else {
                selectedSymptoms.add(value);
            }
            clarificationAnswers = [];
            focusSymptoms = [];
            pendingFocusSelection = [];
            pendingClarification = null;
            latestRecommendationId = '';
            baseQuery = '';
            setError('');
            updateSelectedSymptomsUI();
            document.getElementById('userInput').focus();
        }

        function dedupe(items) {
            return Array.from(new Set((items || []).filter(Boolean)));
        }

        function toggleFocusSymptomOption(button) {
            const value = button.dataset.focusValue;
            const exists = pendingFocusSelection.includes(value);
            if (exists) {
                pendingFocusSelection = pendingFocusSelection.filter(item => item !== value);
                button.classList.remove('selected');
                setError('');
                return;
            }
            if (pendingFocusSelection.length >= 2) {
                setError('最多只能选择 2 个症状，请先取消一个再继续。');
                return;
            }
            pendingFocusSelection.push(value);
            button.classList.add('selected');
            setError('');
        }

        async function submitSymptomFocusSelection() {
            if (!pendingFocusSelection.length) {
                setError('\u8bf7\u5148\u9009\u62e9 1~2 \u4e2a\u60a8\u6700\u60f3\u4f18\u5148\u6539\u5584\u7684\u75c7\u72b6\u3002');
                return;
            }
            focusSymptoms = [...pendingFocusSelection];
            appendUserMessage('\u4f18\u5148\u75c7\u72b6\uff1a' + focusSymptoms.join('\u3001'));
            setError('');
            pendingClarification = null;
            const data = buildPriorityRecommendationData(focusSymptoms);
            if (!data.grouped_recommendations.length && !data.top_recommendations.length) {
                setError('\u6ca1\u6709\u627e\u5230\u8fd9\u4e9b\u4f18\u5148\u75c7\u72b6\u5bf9\u5e94\u7684\u5df2\u63a8\u8350\u8336\u996e\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u3002');
                return;
            }
            appendRecommendationMessage(data);
        }

        async function requestRecommendation() {
            const selected = Array.from(selectedSymptoms);
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: getUserId(),
                    query: baseQuery,
                    selected_symptoms: selected,
                    clarification_answers: clarificationAnswers,
                    focus_symptoms: focusSymptoms,
                })
            });
            return response.json();
        }

        async function submitChat() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            const selected = Array.from(selectedSymptoms);
            const isClarificationReply = Boolean(pendingClarification);

            if (pendingClarification && pendingClarification.mode === 'symptom_focus') {
                setError('请先用上方按钮选择 1~2 个优先症状。');
                return;
            }
            if (isClarificationReply && !text) {
                setError('请直接点击上方选项，或补充一句更具体的描述。');
                return;
            }
            if (!isClarificationReply && !text && !selected.length) {
                setError('请输入您的主诉或先选择症状按键。');
                return;
            }

            if (!isClarificationReply) {
                baseQuery = text;
                clarificationAnswers = [];
                focusSymptoms = [];
                pendingFocusSelection = [];
            } else {
                clarificationAnswers = dedupe([...clarificationAnswers, text]);
            }

            const userText = buildUserMessageText(text, selected) || `\u6211\u8865\u5145\u8fd9\u4e9b\u75c7\u72b6\uff1a${selected.join('\u3001')}`;
            appendUserMessage(userText);
            input.value = '';
            setError('');
            setLoading(true);

            try {
                const data = await requestRecommendation();
                setLoading(false);
                if (!data.success) {
                    setError(data.error || '推荐失败，请稍后重试。');
                    return;
                }
                if (data.needs_clarification) {
                    pendingClarification = data.clarification || {};
                    appendClarificationMessage(data);
                    return;
                }
                pendingClarification = null;
                latestRecommendationId = data.recommendation_id || '';
                appendRecommendationMessage(data);
            } catch (error) {
                setLoading(false);
                setError('网络错误：' + error.message);
            }
        }

        async function submitClarificationChoice(value, label) {
            clarificationAnswers = dedupe([...clarificationAnswers, value]);
            appendUserMessage(label || value);
            setError('');
            setLoading(true);
            try {
                const data = await requestRecommendation();
                setLoading(false);
                if (!data.success) {
                    setError(data.error || '推荐失败，请稍后重试。');
                    return;
                }
                if (data.needs_clarification) {
                    pendingClarification = data.clarification || {};
                    appendClarificationMessage(data);
                    return;
                }
                pendingClarification = null;
                latestRecommendationId = data.recommendation_id || '';
                appendRecommendationMessage(data);
            } catch (error) {
                setLoading(false);
                setError('网络错误：' + error.message);
            }
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

        document.querySelectorAll('.symptom-option').forEach(button => {
            button.addEventListener('click', () => toggleSymptomOption(button));
        });

        document.getElementById('userInput').addEventListener('keydown', event => {
            if (event.key === 'Enter') submitChat();
        });

        window.addEventListener('load', () => {
            updateSelectedSymptomsUI();
            appendWelcomeMessage();
            document.getElementById('userInput').focus();
        });
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









