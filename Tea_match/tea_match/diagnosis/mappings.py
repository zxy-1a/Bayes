from __future__ import annotations

# Step-3 constitution names are aligned with rag_output/step3_constitution_fallback.csv.
CONSTITUTION_ALIAS_MAP: dict[str, str] = {
    "平和质": "平和",
    "气虚质": "气虚",
    "阳虚质": "阳虚",
    "阴虚质": "阴虚",
    "痰湿质": "痰湿",
    "湿热质": "湿热",
    "血瘀质": "血瘀",
    "气郁质": "气郁",
    "特禀质": "特禀(容易过敏)",
    "特禀": "特禀(容易过敏)",
}

# Keep the exported rule names and tea targets here so the diagnosis layer can stay
# consistent with the existing step-3 / step-4 fallback logic.
STEP3_CONSTITUTION_TO_TEAS: dict[str, list[str]] = {
    "气虚": ["元气茶", "舒安茶", "橘红茶"],
    "阳虚": ["六宝茶", "固本茶", "元气茶"],
    "痰湿": ["香橼茶", "橘红茶", "石斛茶", "清平茶", "散云茶", "元气茶"],
    "湿热": ["六宝茶", "石斛茶", "茯清茶", "香橼茶", "参灵茶", "元气茶"],
    "血瘀": ["元气茶", "参灵茶", "石斛茶", "风清茶"],
    "平和": ["六宝茶", "元气茶", "清和茶"],
    "特禀(容易过敏)": ["石斛茶", "散云茶", "橘红茶", "元气茶"],
    "阴虚": ["石斛茶", "散云茶", "平澜茶", "元气茶"],
    "气郁": ["舒安茶", "石斛茶", "元气茶", "参灵茶", "风清茶"],
}

STEP4_ORGAN_TO_TEAS: dict[str, list[str]] = {
    "肝": ["石斛茶", "桑菊茶", "甘平茶", "元气茶"],
    "心": ["参灵茶", "风清茶", "舒安茶", "元气茶"],
    "脾": ["香橼茶", "舒安茶", "石斛茶", "元气茶"],
    "肺": ["橘红茶", "元气茶"],
    "肾": ["茯清茶", "固本茶", "六宝茶", "元气茶"],
}

# Tongue-body / coating evidence -> step-3 constitution.
TONGUE_CONSTITUTION_RULES: dict[str, list[str]] = {
    "气虚": ["齿痕舌", "胖大舌", "淡舌", "淡白舌", "白苔", "薄苔"],
    "阳虚": ["淡白舌", "胖大舌", "白滑苔", "滑苔", "白苔"],
    "痰湿": ["滑苔", "苔腻", "白苔", "胖大舌", "白滑苔"],
    "湿热": ["黄苔", "厚苔", "黄腻苔", "红舌", "有点刺", "点刺舌"],
    "血瘀": ["紫舌", "暗舌", "瘀点舌", "瘀斑舌", "舌下淤堵"],
    "平和": ["薄苔", "非剥苔", "苔不腻腐"],
    "特禀(容易过敏)": ["点刺舌", "有点刺", "红舌"],
    "阴虚": ["红舌", "裂纹舌", "有裂纹", "少苔", "剥苔"],
    "气郁": ["舌边红", "薄黄苔", "红舌"],
}

# Pulse evidence -> step-3 constitution.
PULSE_CONSTITUTION_RULES: dict[str, list[str]] = {
    "气虚": ["虚脉", "弱脉", "细弱脉"],
    "阳虚": ["迟脉", "沉迟脉", "弱脉"],
    "痰湿": ["滑脉"],
    "湿热": ["数脉", "滑数脉"],
    "血瘀": ["涩脉", "弦涩脉", "沉涩脉"],
    "阴虚": ["细脉", "数脉", "细数脉"],
    "气郁": ["弦脉"],
}

# Combined diagnostic evidence -> step-4 organs.
ORGAN_RULES: dict[str, list[str]] = {
    "肝": ["弦脉", "目干", "目涩", "眼干", "眼疲劳", "红舌", "气郁"],
    "心": ["心烦", "失眠", "心悸", "数脉", "细脉", "红舌", "心肾不交", "血瘀"],
    "脾": ["齿痕舌", "胖大舌", "白苔", "食欲不振", "疲劳乏力", "气虚", "痰湿"],
    "肺": ["咳嗽", "痰多", "滑脉", "鼻炎", "过敏", "白苔", "特禀(容易过敏)"],
    "肾": ["耳鸣", "腰酸", "腰膝酸软", "迟脉", "虚脉", "细脉", "阴虚", "阳虚"],
}

# Diagnostic evidence -> symptom/complaint hints for LLM understanding.
SYMPTOM_RULES: dict[str, list[str]] = {
    "疲劳乏力": ["虚脉", "弱脉", "齿痕舌", "胖大舌", "气虚"],
    "失眠": ["心肾不交", "数脉", "细脉", "红舌", "阴虚"],
    "食欲不振": ["齿痕舌", "胖大舌", "白苔", "脾"],
    "湿气重": ["滑苔", "苔腻", "痰湿", "胖大舌"],
    "血瘀倾向": ["舌下淤堵", "涩脉", "瘀点舌", "瘀斑舌", "血瘀"],
    "容易上火": ["红舌", "黄苔", "点刺舌", "湿热", "阴虚"],
}

# Pulse field name -> likely pulse label. The real API may return more fields;
# this is just the current draft based on the sample docs.
PULSE_FIELD_LABELS: dict[str, str] = {
    "chishu_zchi": "迟脉",
    "chishu_zguan": "迟脉",
    "chishu_zcun": "迟脉",
    "xushi_zchi": "虚脉",
    "xushi_zguan": "常脉",
    "xushi_zcun": "常脉",
    "huamai_zchi": "滑脉",
    "huamai_zguan": "滑脉",
    "huamai_zcun": "滑脉",
    "ximai_zchi": "细脉",
    "ximai_zguan": "细脉",
    "ximai_zcun": "细脉",
    "ruomai_zchi": "弱脉",
    "ruomai_zguan": "弱脉",
    "ruomai_zcun": "弱脉",
    "shumai_zchi": "数脉",
    "shumai_zguan": "数脉",
    "shumai_zcun": "数脉",
    "semai_zchi": "涩脉",
    "semai_zguan": "涩脉",
    "semai_zcun": "涩脉",
    "xianmai_zchi": "弦脉",
    "xianmai_zguan": "弦脉",
    "xianmai_zcun": "弦脉",
}

DEFAULT_SIGN_PROBABILITY_THRESHOLD = 0.85
DEFAULT_WEAK_SIGN_THRESHOLD = 0.6
