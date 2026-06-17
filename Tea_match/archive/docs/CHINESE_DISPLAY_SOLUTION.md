# 汉字显示完全解决方案

## 🎯 问题

在 Windows 系统上，`demo_workflow.py` 的输出中汉字显示为乱码（如 `心烦` 显示为 `心烦`）。

这是因为 Windows 命令行默认使用 GBK 编码，而 Python 输出 UTF-8 编码，导致编码不匹配。

## ✅ 解决方案

### 方案 1: 生成 HTML 报告（推荐 ⭐）

生成一个漂亮的 HTML 报告，在浏览器中查看，完全避免编码问题：

```bash
cd D:\bayes\Tea_match
source .venv/Scripts/activate

# 生成 HTML 报告
python generate_html_report.py
```

**输出**：
```
✅ 报告已生成: D:\bayes\Tea_match\test_report.html

💡 请在浏览器中打开此文件
```

然后在浏览器中打开 `test_report.html`，可以看到：
- ✅ 所有汉字正确显示
- ✅ 格式化的表格和结果
- ✅ 完整的 JSON 原始数据
- ✅ 美观的样式和布局

### 方案 2: 使用专用测试脚本

如果不想用浏览器，可以使用 `show_chinese.py` 脚本：

```bash
python show_chinese.py
```

这个脚本会直接在控制台显示汉字（取决于你的终端配置）。

### 方案 3: 将输出重定向到文件

如果终端不支持 UTF-8，可以将输出重定向到文件：

```bash
# 生成 JSON 文件
python disambiguate_complaint.py "心烦" --use-local --pretty > output.json

# 用文本编辑器打开 output.json，汉字会正确显示
```

---

## 📊 完整流程验证

### 测试 1: 模糊诉求识别

```bash
python disambiguate_complaint.py "心烦" --use-local --pretty
```

预期输出（含汉字）：
```json
{
  "complaint": "心烦",
  "is_vague": true,
  "clarification_questions": [
    "您的心烦是否伴随失眠？",
    "是否同时有多梦或易醒的情况？",
    "是否感到容易焦虑或坐立不安？",
    "是否有心悸（心跳不规律）或胸闷感？"
  ]
}
```

### 测试 2: 用户回答推断

```bash
python disambiguate_complaint.py "心烦" \
  --response "是的，最近睡眠不好，经常失眠多梦" \
  --use-local --pretty
```

预期输出（含汉字）：
```json
{
  "complaint": "心烦",
  "user_response": "是的，最近睡眠不好，经常失眠多梦",
  "inferred_symptoms": [
    "失眠",
    "心神不宁"
  ]
}
```

### 测试 3: 诉求拆分

```bash
python understand_query.py "最近觉得心烦，卵巢囊肿，最近容易疲劳" --mock --pretty
```

预期输出（含汉字）：
```json
{
  "complaints": [
    {
      "raw": "心烦",
      "normalized_terms": ["心烦", "心神不宁", ...],
      "confidence": 0.5
    },
    {
      "raw": "卵巢囊肿",
      "normalized_terms": ["卵巢囊肿", "囊肿", ...],
      "confidence": 0.95
    },
    {
      "raw": "容易疲劳",
      "normalized_terms": ["易疲劳", "乏力", ...],
      "confidence": 0.9
    }
  ]
}
```

---

## 🖼️ HTML 报告预览

运行 `python generate_html_report.py` 后，会生成 `test_report.html`，包含：

1. **系统概览**
   - 项目名称和描述
   - 生成时间

2. **测试 1: 模糊诉求识别**
   - 输入：心烦
   - 输出：澄清问题列表

3. **测试 2: 用户回答推断**
   - 输入：原诉求 + 用户回答
   - 输出：推断的规范症状

4. **测试 3: 诉求拆分**
   - 输入：完整用户诉求
   - 输出：拆分和分类结果（表格形式）

5. **系统特性**
   - 本地规则库覆盖情况
   - 性能指标表格

6. **原始 JSON 数据**
   - 所有测试的完整 JSON 输出
   - 格式化显示

---

## 📁 新增文件

```
D:\bayes\Tea_match\
├── show_chinese.py              (新增) - 直接控制台显示
├── generate_html_report.py      (新增) - 生成 HTML 报告
└── test_report.html             (新增) - 生成的 HTML 报告
```

---

## 🚀 推荐使用流程

### 第一次使用（5 分钟）

```bash
# 生成 HTML 报告
python generate_html_report.py

# 在浏览器中打开报告
start test_report.html
```

在浏览器中可以看到所有的汉字和格式化的测试结果。

### 后续使用（快速验证）

如果你只是想快速验证某个功能：

```bash
# 单个测试 - 输出到文件
python disambiguate_complaint.py "心烦" --use-local --pretty > result.json

# 用任何编辑器打开 result.json，汉字完美显示
```

---

## ❓ 常见问题

### Q: 为什么终端显示乱码？
**A**: Windows 命令行默认 GBK 编码。我们提供了 HTML 报告方案完全避免这个问题。

### Q: HTML 报告中的汉字会显示正确吗？
**A**: 是的！HTML 文件以 UTF-8 编码保存，浏览器会自动正确显示汉字。

### Q: 可以直接修改代码让终端显示正确吗？
**A**: 技术上可以，但取决于你的系统和终端配置。HTML 报告是更可靠的方案。

### Q: 如何快速复制 JSON 输出到其他工具？
**A**: 使用重定向：`python ... > output.json`，然后打开 output.json 文件。

---

## 📊 完整验证清单

- [✓] 本地规则库可正确识别模糊诉求
- [✓] 澄清问题显示正确（汉字）
- [✓] 用户回答可正确推断症状
- [✓] 诉求拆分可正确分类
- [✓] JSON 输出格式正确（含汉字）
- [✓] HTML 报告美观且汉字显示完美

---

## 🎯 下一步

1. **立即验证**：
   ```bash
   python generate_html_report.py
   start test_report.html
   ```

2. **查看结果**：
   - 所有测试输出
   - 完整的汉字显示
   - 格式化的表格和 JSON

3. **根据需要选择**：
   - 用 HTML 报告进行展示和交流
   - 用 JSON 输出进行数据处理
   - 用脚本进行自动化测试

---

**🎉 现在所有汉字都能完美显示了！**

生成 HTML 报告，在浏览器中查看，享受完美的界面和完全正确的汉字显示。

