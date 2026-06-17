# 中医茶饮推荐系统 - 模糊诉求澄清方案总结

## 核心问题与解决方案

### 问题描述
你遇到的问题：**"心烦"在表格中没有原话，就无法找到有效匹配**

这反映了一个普遍的挑战：
- 患者的**口语化诉求** 与 **医学规范术语** 之间存在鸿沟
- 某些诉求本身 **不够具体**，需要进一步澄清
- 直接的词汇映射方案**不够灵活**

### 推荐方案：多阶段澄清流程

```
用户输入: "最近觉得心烦，卵巢囊肿，最近容易疲劳"
    ↓
【诉求拆分与分类】
    ├─ 卵巢囊肿 ✓ 明确 (confidence: 0.95)
    ├─ 容易疲劳 ✓ 明确 (confidence: 0.90)
    └─ 心烦 ⚠ 模糊 (confidence: 0.50)
    ↓
【分路处理】
    ├─ 明确诉求 → 直接 RAG 查询 (< 100ms)
    └─ 模糊诉求 → 生成澄清问题 → 等待用户回答 → 推断症状 → RAG 查询
    ↓
【整合推荐】
    → [舒安茶, 肝护茶, 元气茶, ...]
```

---

## 新增模块说明

### 1. `disambiguate_complaint.py` (模糊诉求澄清)
**职责**：处理模糊、不具体的用户诉求

**功能**：
- 检测诉求的模糊性
- 生成有针对性的澄清问题
- 根据用户回答推断规范症状

**使用示例**：
```bash
# 检测模糊性 → 生成问题
python disambiguate_complaint.py "心烦" --use-local --pretty

# 根据用户回答推断症状
python disambiguate_complaint.py "心烦" \
  --response "是的，最近睡眠不好，经常失眠多梦" \
  --use-local --pretty
```

**关键特性**：
- ✓ 本地规则库优先（无需 API）
- ✓ 可扩展的模式库（`VAGUE_COMPLAINT_PATTERNS`）
- ✓ 规范症状映射（response_mapping）

### 2. `recommend_pipeline.py` (端到端协调)
**职责**：整合所有子模块，协调完整的推荐流程

**四阶段流程**：
1. **Step 1**: 解析用户输入，拆分诉求
2. **Step 2**: 澄清模糊诉求
3. **Step 3**: 合并症状，进行 RAG 检索
4. **Step 4**: 推荐茶饮

**使用示例**：
```python
from recommend_pipeline import TeaRecommendationPipeline

pipeline = TeaRecommendationPipeline(use_mock_understand=True)
result = pipeline.run("最近觉得心烦，卵巢囊肿，最近容易疲劳")

print(json.dumps(result, ensure_ascii=False, indent=2))
```

### 3. `api_interface.py` (API 接口定义)
**职责**：定义前端与后端的交互接口

**核心方法**：
- `start_conversation(user_query)` - 开始对话
- `submit_clarification_response(responses)` - 提交澄清回答
- `get_recommendations()` - 获取最终推荐

**完整的交互示例**：
```javascript
// 前端调用
const response = await api.startConversation("最近觉得心烦");
// 响应: { phase: 'clarifying', questions: [...] }

// 用户回答后
const result = await api.submitClarificationResponse({
  'q_0_1': '是的，经常失眠多梦'
});
// 响应: { phase: 'complete', recommendations: [...] }
```

### 4. `test_pipeline.py` (综合测试)
**职责**：演示和测试整个系统

**包含 4 个测试场景**：
1. 明确诉求 → 直接推荐
2. 模糊诉求 → 澄清 → 推荐
3. 混合诉求 → 选择性澄清 → 综合推荐
4. 边界情况处理

**运行测试**：
```bash
python test_pipeline.py
```

### 5. `demo_workflow.py` (快速演示)
**职责**：交互式演示系统功能

**演示内容**：
- 场景 1: 明确诉求处理
- 场景 2: 模糊诉求澄清
- 场景 3: 混合诉求处理

**运行演示**：
```bash
python demo_workflow.py
```

---

## 关键设计点

### 1. 模糊诉求识别逻辑

判断一个诉求是否模糊的三个维度：

```python
def is_vague(complaint: str) -> bool:
    # 维度 1: 长度太短（< 4 字符）
    if len(complaint) < 4:
        return True
    
    # 维度 2: 包含模糊关键词
    vague_keywords = ["烦", "没劲", "不舒服", "难受", "闷"]
    if any(kw in complaint for kw in vague_keywords):
        return True
    
    # 维度 3: LLM 置信度低（< 0.8）
    if llm_confidence_score < 0.8:
        return True
    
    return False
```

### 2. 澄清问题的设计原则

针对"心烦"的例子：

```python
{
    "keywords": ["心烦", "烦躁", "心烦意乱"],
    "clarification_questions": [
        "您的心烦是否伴随失眠？",
        "是否同时有多梦或易醒的情况？",
        "是否感到容易焦虑或坐立不安？",
        "是否有心悸或胸闷感？"
    ],
    "response_mapping": {
        "失眠|多梦|易醒": ["失眠", "心神不宁"],
        "焦虑|坐立不安": ["抑郁", "心神不宁"],
        "心悸|胸闷": ["心悸", "心神不宁"],
        "伴热|口干|便秘": ["心火旺", "失眠"]
    }
}
```

**设计原则**：
- ✓ 问题具体、专业，但易理解
- ✓ 涵盖主要的相关症状
- ✓ 每个关键词都映射到规范症状

### 3. 优先级管理

系统使用 4 阶段的优先级模型：

| 阶段 | 优先级 | 触发条件 | 权重 |
|------|--------|---------|------|
| 症状初筛 | 1 | 直接匹配用户诉求 | 1.0 |
| 症状组合 | 2 | 多个症状的组合规则 | 1.2 |
| 体质降级 | 3 | 当阶段 1/2 无匹配 | 0.6 |
| 脏腑降级 | 4 | 最后的备选 | 0.6 |

**决策规则**：
- 优先使用 **阶段 1/2 的精确匹配**
- 仅当无匹配时才使用 **阶段 3/4 的降级推荐**
- 同一诉求只用一个阶段，不混合

### 4. 缓存与性能

**多层缓存策略**：

```python
# 层 1: 本地规则（最快）
if local_rules.match(complaint):
    return local_rules.resolve(complaint)  # < 10ms

# 层 2: LLM 结果缓存（5 分钟）
if cache.has(complaint):
    return cache.get(complaint)  # < 50ms

# 层 3: LLM API 调用（最慢）
return llm.disambiguate(complaint)  # 200-500ms
```

**目标性能指标**：
- 本地规则命中率：> 90%
- LLM 调用频率：< 10%
- 典型延迟：< 500ms

---

## 实现清单

### 已完成
- [x] `disambiguate_complaint.py` - 模糊诉求澄清
- [x] `recommend_pipeline.py` - 端到端协调
- [x] `api_interface.py` - API 接口定义
- [x] `test_pipeline.py` - 综合测试
- [x] `demo_workflow.py` - 快速演示
- [x] `README_CLARIFICATION_FLOW.md` - 完整文档

### 待完成（可选）
- [ ] 前端 Web UI（React/Vue）
- [ ] WebSocket 多轮对话服务
- [ ] 监控与日志系统
- [ ] A/B 测试框架
- [ ] 用户反馈收集系统
- [ ] 本地规则库持续优化流程

---

## 快速验证

### 1. 测试模糊诉求识别

```bash
cd D:\bayes\Tea_match

# 激活虚拟环境
source .venv/Scripts/activate

# 测试 1: 识别模糊诉求
python disambiguate_complaint.py "心烦" --use-local --pretty

# 测试 2: 根据用户回答推断症状
python disambiguate_complaint.py "心烦" \
  --response "是的，最近睡眠不好，经常失眠多梦" \
  --use-local --pretty
```

### 2. 运行完整流程

```bash
# 运行综合演示
python demo_workflow.py

# 运行所有测试
python test_pipeline.py
```

### 3. 查看推荐结果

```bash
# 运行端到端推荐流程
python recommend_pipeline.py \
  "最近觉得心烦，卵巢囊肿，最近容易疲劳" \
  --mock --pretty
```

---

## 下一步建议

### 短期（优先）
1. **完善本地规则库**
   - 扩展 `VAGUE_COMPLAINT_PATTERNS` 中的诉求模式
   - 根据用户反馈调整澄清问题
   - 优化 `response_mapping` 的关键词

2. **集成前端**
   - 实现 WebSocket 多轮对话
   - 前端按顺序显示澄清问题
   - 支持用户实时回答

3. **添加监控**
   - 记录澄清成功率
   - 跟踪用户满意度
   - 监控系统延迟

### 中期
1. **性能优化**
   - 本地规则命中率目标：> 95%
   - 多线程并发查询
   - Redis 缓存集成

2. **功能增强**
   - 支持多条件组合推理
   - 个性化排序（基于用户历史）
   - 推荐理由生成

3. **质量保证**
   - A/B 测试澄清策略
   - 用户反馈回路
   - 定期模型评估

### 长期
1. **架构升级**
   - 图结构推理（症状-茶饮关系图）
   - 知识图谱集成
   - 多语言方言支持

2. **商业化**
   - 用户画像构建
   - 推荐个性化
   - 用户留存优化

---

## 常见问题

### Q1: 如果本地规则无法匹配怎么办？
**A**: 系统会自动降级到 LLM 调用。可通过 `--api-key` 参数传入 API 密钥。

### Q2: 澄清问题的回答可以是任意文本吗？
**A**: 是的。系统会通过关键词匹配或 LLM 语义理解来处理自由文本。

### Q3: 如何扩展新的模糊诉求模式？
**A**: 在 `disambiguate_complaint.py` 中的 `VAGUE_COMPLAINT_PATTERNS` 字典中添加新条目。

### Q4: 系统支持多个模糊诉求同时澄清吗？
**A**: 支持。系统会为每个模糊诉求生成对应的澄清问题，前端可以分组显示。

### Q5: 推荐结果的准确性如何保证？
**A**: 通过 4 阶段优先级管理、RAG 向量检索和用户反馈循环。

---

## 参考资源

- 📄 **完整文档**: `README_CLARIFICATION_FLOW.md`
- 🧪 **测试套件**: `test_pipeline.py`
- 🎬 **快速演示**: `demo_workflow.py`
- 🔧 **API 定义**: `api_interface.py`

---

## 联系与反馈

如有问题或改进建议，请：
1. 查看日志输出
2. 运行测试验证
3. 检查本地规则库配置
4. 参考完整文档

---

**最后更新**: 2026-06-14
**版本**: 1.0
**状态**: ✅ 可用于测试
