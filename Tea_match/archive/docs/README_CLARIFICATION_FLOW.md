# 中医茶饮推荐系统 - 架构与部署文档

## 核心问题回答

你遇到的问题是**模糊诉求匹配失败**。"心烦" 这个词在表格中没有原话，但它实际上可以映射到多个医学症状（失眠、抑郁、心神不宁等），需要进一步澄清。

### 为什么这个方案更好？

**传统匹配流程（有问题）：**
```
用户输入 → 词汇映射 → 查表 → 如果没有原话 → 失败 ❌
```

**新的澄清流程（推荐）：**
```
用户输入
    ↓
识别明确 vs 模糊
    ↓
【明确】直接 RAG 查询 ✓
【模糊】生成澄清问题 → 等待用户回答 → 推断规范症状 → RAG 查询 ✓
    ↓
合并结果 → 推荐茶饮
```

---

## 系统架构

### 模块职责

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `understand_query.py` | 拆分和初步规范化用户诉求 | "心烦、卵巢囊肿、疲劳" | 多个诉求对象，各有类型和置信度 |
| `disambiguate_complaint.py` | 处理模糊诉求：生成澄清问题或推断症状 | 模糊词 + 可选的用户回答 | 澄清问题列表 或 推断的规范症状 |
| `prepare_rag_data.py` | 构建 RAG 知识库 | Excel 表格 | JSONL 文档 + 别名字典 |
| `search_vector_store.py` | 向量检索推荐茶饮 | 症状关键词 | 匹配的茶饮列表 |
| `recommend_pipeline.py` | 端到端协调 | 用户诉求 | 推荐茶饮列表 |
| `api_interface.py` | 前端 API 定义 | HTTP 请求 | JSON 响应 |

---

## 实现细节

### 1. 模糊诉求识别逻辑

```python
# 三个判断维度
def is_vague(complaint: str) -> bool:
    # (1) 长度太短
    if len(complaint) < 4:
        return True
    
    # (2) 包含模糊关键词
    vague_keywords = ["烦", "没劲", "不舒服", "难受", "闷"]
    if any(kw in complaint for kw in vague_keywords):
        return True
    
    # (3) LLM 置信度较低
    if llm_confidence_score < 0.8:
        return True
    
    return False
```

### 2. 澄清问题的构造

针对"心烦"的例子：

```json
{
  "complaint": "心烦",
  "clarification_questions": [
    "您的心烦是否伴随失眠？",
    "是否同时有多梦或易醒的情况？",
    "是否感到容易焦虑或坐立不安？",
    "是否有心悸（心跳不规律）或胸闷感？"
  ],
  "response_mapping": {
    "失眠|多梦|易醒": ["失眠", "心神不宁"],
    "焦虑|坐立不安": ["抑郁", "心神不宁"],
    "心悸|胸闷": ["心悸", "心神不宁"]
  }
}
```

当用户回答"是的，最近睡眠不好，经常失眠多梦"时：
- 系统识别关键词：`失眠`、`多梦`
- 映射到规范症状：`["失眠", "心神不宁"]`
- 用这些症状进行 RAG 查询

### 3. 多阶段匹配管道

```
阶段 1: 明确症状初筛 (优先级 = 1)
  ↓ 成功 → 推荐对应茶饮
  ↓ 失败 → 进入阶段 2

阶段 2: 症状组合规则 (优先级 = 2)
  ↓ 成功 → 考虑组合和附加茶饮
  ↓ 失败 → 进入阶段 3

阶段 3: 体质降级 (优先级 = 3)
  ↓ 仅在前两阶段无匹配时使用

阶段 4: 脏腑降级 (优先级 = 4)
  ↓ 最后备选
```

---

## 使用示例

### 本地测试（无需 API）

```bash
# 测试 1: 识别明确诉求
python understand_query.py "卵巢囊肿，容易疲劳" --mock --pretty

# 测试 2: 处理模糊诉求
python disambiguate_complaint.py "心烦" --use-local --pretty

# 测试 3: 用户回答澄清问题
python disambiguate_complaint.py "心烦" \
  --response "是的，最近睡眠不好，经常失眠多梦" \
  --use-local --pretty

# 测试 4: 端到端流程
python test_pipeline.py
```

### 实际场景集成

```python
from recommend_pipeline import TeaRecommendationPipeline

pipeline = TeaRecommendationPipeline(use_mock_understand=False)

# 第 1 步：用户输入
result = pipeline.step1_parse_query("最近觉得心烦，卵巢囊肿，最近容易疲劳")
# 输出：识别出 3 个诉求，其中 1 个模糊（心烦）

# 第 2 步：澄清模糊诉求
# → 系统生成问题给前端展示
# → 用户回答问题
# → 系统推断症状
result = pipeline.step2_clarify_vague()

# 第 3 步：搜索
result = pipeline.step3_normalize_and_search()

# 第 4 步：推荐
result = pipeline.step4_recommend()
```

---

## 前端集成指南

### 对话流程示意

```
1️⃣ 用户输入初始诉求
   "最近觉得心烦，卵巢囊肿，最近容易疲劳"
        ↓
2️⃣ 后端返回澄清问题
   "您的心烦是否伴随失眠？"
   "是否容易焦虑？"
        ↓
3️⃣ 用户选择或输入回答
   "是的，经常失眠多梦"
        ↓
4️⃣ 后端返回最终推荐
   ✓ 舒安茶 (失眠 + 心神不宁)
   ✓ 肝护茶 (卵巢囊肿)
   ✓ 元气茶 (易疲劳)
```

### API 调用示例（Node.js / React）

```javascript
// 初始化对话
const response = await fetch('/api/tea-recommendation/start', {
  method: 'POST',
  body: JSON.stringify({
    user_query: "最近觉得心烦，卵巢囊肿，最近容易疲劳"
  })
});

const data = await response.json();
// data.phase === 'clarifying'
// data.clarification_questions = [...]

// 用户回答后提交
const submitResponse = await fetch('/api/tea-recommendation/submit', {
  method: 'POST',
  body: JSON.stringify({
    conversation_id: data.conversation_id,
    responses: {
      'q_0_1': '是的，经常失眠多梦'
    }
  })
});

const result = await submitResponse.json();
// result.phase === 'complete'
// result.recommendations = [...]
```

---

## 配置与优化

### 本地规则库的维护

`disambiguate_complaint.py` 中的 `VAGUE_COMPLAINT_PATTERNS` 应该定期更新：

```python
VAGUE_COMPLAINT_PATTERNS = {
    "心烦": {
        "keywords": ["心烦", "烦躁"],
        "clarification_questions": [
            "您的心烦是否伴随失眠？",
            # ... 定期添加新问题
        ],
        "response_mapping": {
            "失眠|多梦": ["失眠", "心神不宁"],
            # ... 根据实际运营数据调整
        }
    }
}
```

### 缓存策略

- **短期缓存**（5 分钟）：LLM API 调用结果
- **长期缓存**（1 天）：RAG 检索结果
- **本地规则优先**：本地规则匹配时不调用 LLM

### 成本控制

```python
# 分阶段降级
if local_rules_match:
    use_local_rules()  # 免费
elif cache_hit:
    use_cache()  # 使用已缓存的 LLM 结果
else:
    call_qwen_api()  # 最后才调用 API，¥ 计费
```

---

## 性能指标

### 典型场景的预期表现

| 场景 | 延迟 | 备注 |
|------|------|------|
| 明确诉求 → 直接推荐 | < 100ms | 本地规则 + 向量检索 |
| 单个模糊诉求 → 澄清 | < 50ms | 本地规则库查询 |
| 用户回答 → 推断 | < 200ms | 包括 LLM 调用 |
| 完整流程 | < 500ms | 所有步骤总和 |

---

## 故障排查

### 场景 1：模糊诉求未被识别

**问题**：某个应该澄清的诉求被误判为明确

**解决**：
1. 检查 `understand_query.py` 的 `MOCK_EXPANSIONS`
2. 调整置信度阈值 (default: 0.8)
3. 在 `VAGUE_COMPLAINT_PATTERNS` 中添加新模式

### 场景 2：澄清问题的回答映射不准确

**问题**：用户回答 "失眠" 但系统没有正确映射到 "心神不宁"

**解决**：
1. 检查 `response_mapping` 的正则表达式
2. 添加更多关键词变体
3. 考虑使用 LLM 进行语义理解

### 场景 3：推荐的茶饮不相关

**问题**：匹配到了症状，但推荐的茶饮不合适

**解决**：
1. 检查 RAG 知识库是否构建正确（`prepare_rag_data.py`）
2. 验证症状别名映射（`symptom_alias_dictionary.csv`）
3. 调整 RAG 向量模型或搜索阈值

---

## 未来优化方向

1. **主动学习**：收集用户反馈，持续改进澄清问题
2. **多语言支持**：方言 → 标准话 → 规范术语
3. **图结构推理**：构建症状-茶饮关系图，支持更复杂的组合推理
4. **个性化推荐**：基于用户历史、口碑、体质等进行排序
5. **A/B 测试框架**：对比不同的澄清策略效果

---

## 部署清单

- [ ] 本地规则库 (`VAGUE_COMPLAINT_PATTERNS`) 完整度 > 80%
- [ ] RAG 知识库已构建 (`rag_output/tea_rag_documents.jsonl`)
- [ ] 向量索引已导入 (`vector_store/` 目录)
- [ ] LLM API 密钥已配置
- [ ] 前端 API 路由已实现
- [ ] 多轮对话系统已集成（WebSocket 或 Server-Sent Events）
- [ ] 日志和监控已配置
- [ ] 灾备测试已完成

---

## 参考文件

- 核心实现：`disambiguate_complaint.py`、`recommend_pipeline.py`
- 数据处理：`prepare_rag_data.py`
- 测试验证：`test_pipeline.py`
- API 定义：`api_interface.py`
