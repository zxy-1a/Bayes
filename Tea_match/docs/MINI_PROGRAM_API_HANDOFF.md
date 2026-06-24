# 中医茶饮推荐接口对接说明

## 接口地址

- `POST /api/mini_program/recommend`
- `POST /api/recommend`（兼容旧地址）

## 请求方式

- `Content-Type: application/json`

## 请求参数

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `user_id` | string | 用户唯一标识，未传默认 `anonymous` |
| `query` | string | 用户主诉，是主要判断依据 |
| `selected_symptoms` | string[] | 前端点选的症状 |
| `clarification_answers` | string[] | 多轮澄清时的点选结果 |
| `tongue_result` | object | 舌诊 / 面诊接口返回结果 |
| `sublingual_result` | object | 舌底接口返回结果 |
| `pulse_result` | object | 脉诊接口返回结果 |

## 使用原则

1. 主诉优先
2. 舌诊 / 舌底 / 脉诊作为补充输入
3. 诊断结果已映射到《养生茶饮匹配逻辑.xlsx》中的：
   - 第三步：体质兜底
   - 第四步：五脏兜底
4. 不用舌脉结果替代用户主诉做主判断

## 已接入的映射

### 第三步体质兜底

- 气虚
- 阳虚
- 阴虚
- 痰湿
- 湿热
- 血瘠
- 气郁
- 平和
- 特禀(容易过敏)

### 第四步五脏兜底

- 肝
- 心
- 脾
- 肺
- 肾

### 症状提示

- 疲劳乏力
- 失眠
- 食欲不振
- 湿气重
- 血瘠倾向
- 容易上火

## 上游结果如何给我们

小程序同事不需要把图片再传给我们，只需要传三个结果 JSON：

- `tongue_result`
- `sublingual_result`
- `pulse_result`

也就是说，我们接收的是接口返回结果，不是图片。

## 我们当前重点读取的上游字段

### `tongue_result`

- `tizhi_name`
- `char`
- `syndrome`

### `sublingual_result`

- `characters`

### `pulse_result`

- `chishu_zchi / chishu_zguan / chishu_zcun`
- `xushi_zchi / xushi_zguan / xushi_zcun`
- `huamai_*`
- `ximai_*`
- `ruomai_*`
- `shumai_*`
- `semai_*`
- `xianmai_*`

## 建议小程序对接方式

1. 用户输入主诉
2. 小程序内部先调用舌诊 / 舌底 / 脉诊接口
3. 拿到三个结果 JSON 后，与主诉一起调用 `/api/mini_program/recommend`
4. 前端优先展示：
   - `grouped_recommendations`
   - `top_recommendations`
5. 若需要展示舌脉辅助判断，可读取：
   - `diagnostic_summary.constitution_hints`
   - `diagnostic_summary.organ_hints`
   - `diagnostic_summary.symptom_hints`

## 错误响应

```json
{
  "success": false,
  "error": "请输入您的主诉、选择症状或提供舌脉结果"
}
```

## 当前版本结论

我们已经完成并接入：

- 舌 / 面 / 脉结果映射到第三步体质规则
- 舌 / 面 / 脉结果映射到第四步五脏规则

**主诉主导推荐，舌 / 舌底 / 脉作为第三步体质和第四步五脏的兜底增强输入。**
