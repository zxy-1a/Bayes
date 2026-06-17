"""
多轮澄清对话的 API 设计与前端对接指南

这个模块定义了系统和前端的交互接口。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class ConversationPhase(Enum):
    """对话阶段"""

    INITIAL_INPUT = "initial_input"  # 用户输入初始诉求
    CLARIFYING = "clarifying"  # 系统正在生成澄清问题
    WAITING_RESPONSE = "waiting_response"  # 等待用户回答澄清问题
    PROCESSING = "processing"  # 处理用户回答，推断症状
    SEARCHING = "searching"  # 进行 RAG 检索
    COMPLETE = "complete"  # 推荐完成


@dataclass
class ComplaintSegment:
    """诉求分段"""

    segment_id: int
    raw_text: str
    type: str  # 'clear', 'vague', 'western_disease'
    clarity_score: float  # 0-1


@dataclass
class ClarificationQuestion:
    """澄清问题"""

    question_id: str
    question_text: str
    question_type: str  # 'choice', 'text', 'multi_choice'
    options: list[str] | None = None  # 如果是选择题


@dataclass
class ClarificationContext:
    """澄清的上下文"""

    complaint_segment_id: int
    original_complaint: str
    questions: list[ClarificationQuestion]
    user_responses: dict[str, str] | None = None  # question_id -> response


@dataclass
class RecommendedTea:
    """推荐的茶饮"""

    tea_name: str
    course: str
    matched_symptoms: list[str]
    reason: str  # 推荐理由
    priority: int  # 1-4，越小越优
    confidence: float  # 0-1


class TeaRecommendationAPI:
    """
    API 接口定义。

    前端与后端的交互流程：

    1. 前端调用 start_conversation(user_query)
       ↓ 返回：需要澄清的问题列表（如果有）或直接推荐（如果诉求明确）

    2. 用户回答问题
       前端调用 submit_clarification_response(context_id, responses)
       ↓ 返回：更新后的推荐结果

    3. 获取最终推荐
       前端调用 get_recommendations()
    """

    def __init__(self):
        self.conversation_id: str | None = None
        self.phase = ConversationPhase.INITIAL_INPUT
        self.complaint_segments: list[ComplaintSegment] = []
        self.clarification_contexts: list[ClarificationContext] = []
        self.recommendations: list[RecommendedTea] = []
        self.workflow_trace: list[dict] = []  # 用于调试

    def start_conversation(self, user_query: str) -> dict[str, Any]:
        """
        Step 1: 用户输入初始诉求

        返回：
        {
            "conversation_id": "conv_xxx",
            "phase": "clarifying" | "complete",
            "complaints": [
                {
                    "segment_id": 0,
                    "raw_text": "心烦",
                    "type": "vague",
                    "clarity_score": 0.3
                }
            ],
            "clarification_questions": [
                {
                    "question_id": "q1",
                    "question_text": "您的心烦是否伴随失眠？",
                    "question_type": "choice",
                    "options": ["是", "否", "不太清楚"]
                }
            ],
            "direct_recommendations": [  # 如果有明确诉求，直接推荐
                {
                    "tea_name": "舒安茶",
                    "matched_symptoms": ["卵巢囊肿"]
                }
            ]
        }
        """
        from .recommend_pipeline import TeaRecommendationPipeline
        from .understand_query import build_mock_result, normalize_result

        # 使用 mock 模式快速演示
        understood = normalize_result(build_mock_result(user_query), user_query)
        self.complaint_segments = [
            ComplaintSegment(
                segment_id=i,
                raw_text=c.get("raw", ""),
                type="vague" if c.get("confidence", 0) < 0.8 else "clear",
                clarity_score=c.get("confidence", 0),
            )
            for i, c in enumerate(understood.get("complaints", []))
        ]

        # 收集需要澄清的问题
        clarification_needed = []
        for segment in self.complaint_segments:
            if segment.type == "vague":
                # 这里应该调用 disambiguate_complaint 获取问题
                questions = [
                    ClarificationQuestion(
                        question_id=f"q_{segment.segment_id}_1",
                        question_text=f"请描述您的『{segment.raw_text}』症状，是否伴随其他表现？",
                        question_type="text",
                    )
                ]
                clarification_needed.append(
                    ClarificationContext(
                        complaint_segment_id=segment.segment_id,
                        original_complaint=segment.raw_text,
                        questions=questions,
                    )
                )

        if clarification_needed:
            self.phase = ConversationPhase.CLARIFYING
            self.clarification_contexts = clarification_needed
        else:
            self.phase = ConversationPhase.SEARCHING
            # 直接进行搜索和推荐

        response = {
            "conversation_id": self.conversation_id or "conv_demo",
            "phase": self.phase.value,
            "complaint_segments": [asdict(s) for s in self.complaint_segments],
            "clarification_questions": [
                {
                    "context_id": ctx.complaint_segment_id,
                    "original_complaint": ctx.original_complaint,
                    "questions": [asdict(q) for q in ctx.questions],
                }
                for ctx in clarification_needed
            ],
        }

        self.workflow_trace.append({"step": "start_conversation", "input": user_query, "output": response})
        return response

    def submit_clarification_response(self, responses: dict[str, str]) -> dict[str, Any]:
        """
        Step 2: 用户回答澄清问题

        Input:
        {
            "q_0_1": "是的，最近经常失眠，还容易多梦",
            "q_1_1": "不适用"
        }

        返回：更新的推荐结果
        {
            "phase": "complete",
            "resolved_vague": {
                "心烦": ["失眠", "心神不宁"]
            },
            "recommendations": [
                {
                    "tea_name": "舒安茶",
                    "matched_symptoms": ["失眠", "心神不宁", "卵巢囊肿"],
                    "reason": "...",
                    "priority": 1
                }
            ]
        }
        """
        # 这里应该调用 disambiguate_complaint 推断症状
        # 然后重新进行 RAG 搜索

        self.phase = ConversationPhase.COMPLETE

        return {
            "phase": self.phase.value,
            "resolved_symptoms": {
                "心烦": ["失眠", "心神不宁"],
            },
            "recommendations": [
                asdict(
                    RecommendedTea(
                        tea_name="舒安茶",
                        course="14天",
                        matched_symptoms=["失眠", "心神不宁", "卵巢囊肿"],
                        reason="综合匹配您的所有诉求",
                        priority=1,
                        confidence=0.95,
                    )
                )
            ],
        }

    def get_recommendations(self) -> list[dict]:
        """获取最终推荐列表。"""
        return [asdict(r) for r in self.recommendations]


# 前端示例调用流程
FRONTEND_INTEGRATION_EXAMPLE = """
# React/Vue 前端集成示例

## 1. 初始化对话

```javascript
const api = new TeaRecommendationAPI();

// 用户输入："最近觉得心烦，卵巢囊肿，最近容易疲劳"
const response = await api.startConversation(userQuery);

if (response.phase === 'clarifying') {
  // 显示澄清问题
  response.clarificationQuestions.forEach(ctx => {
    console.log(`原诉求: ${ctx.originalComplaint}`);
    ctx.questions.forEach(q => {
      console.log(`Q: ${q.questionText}`);
      if (q.questionType === 'choice') {
        // 显示选择按钮
        q.options.forEach(opt => console.log(`  [ ${opt} ]`));
      }
    });
  });
} else if (response.phase === 'complete') {
  // 直接显示推荐
  displayRecommendations(response.recommendations);
}
```

## 2. 用户回答问题

```javascript
const userResponses = {
  'q_0_1': '是的，最近经常失眠，还容易多梦',
  'q_1_1': '不适用'
};

const result = await api.submitClarificationResponse(userResponses);

if (result.phase === 'complete') {
  displayRecommendations(result.recommendations);
}
```

## 3. 显示推荐结果

```javascript
function displayRecommendations(teas) {
  teas.forEach(tea => {
    console.log(`${tea.teaName}`);
    console.log(`疗程: ${tea.course}`);
    console.log(`匹配: ${tea.matchedSymptoms.join('、')}`);
    console.log(`理由: ${tea.reason}`);
  });
}
```
"""
