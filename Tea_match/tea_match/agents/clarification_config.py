from __future__ import annotations

from typing import Any


def U(text: str) -> str:
    return text.encode("ascii").decode("unicode_escape")


MAX_OPTIONS = 8

BROAD_STEP2_CONDITIONS = {
    U(r"\u8840\u538b\u9ad8\u3001\u8840\u7cd6\u9ad8\u3001\u5c3f\u9178\u9ad8\u3001\u8840\u8102\u9ad8"),
    U(r"\u547c\u5438\u9053\u75be\u75c5"),
    U(r"\u6d88\u5316\u9053\u75be\u75c5"),
    U(r"\u4e73\u817a\u7ed3\u8282\u3001\u7532\u72b6\u817a\u7ed3\u8282"),
}

RESPIRATORY_PRIMARY_CONDITIONS = {
    U(r"\u547c\u5438\u9053\u75be\u75c5"),
    U(r"\u53cd\u590d\u611f\u5192"),
    U(r"\u8fc7\u654f\u6027\u9f3b\u708e"),
    U(r"\u80ba\u7ed3\u8282"),
}

RESPIRATORY_FIRST_STEP_TERMS = {
    U(r"\u611f\u5192"), U(r"\u6d41\u611f"), U(r"\u54bd\u708e"), U(r"\u652f\u6c14\u7ba1\u708e"),
    U(r"\u6162\u6027\u652f\u6c14\u7ba1\u708e"), U(r"\u80ba\u6c14\u80bf"), U(r"\u80ba\u7ed3\u8282"),
    U(r"\u80ba\u4e0d\u597d"), U(r"\u80ba\u529f\u80fd\u969c\u788d"), U(r"\u80ba\u529f\u80fd\u5dee"),
}

RENAL_FIRST_STEP_TERMS = {
    U(r"\u80be\u4e0d\u597d"), U(r"\u80be\u529f\u80fd\u969c\u788d"), U(r"\u80be\u865a"), U(r"\u80be\u708e"),
    U(r"\u80be\u7ed3\u77f3"), U(r"\u80be\u706b\u5927"),
}

LIVER_FIRST_STEP_TERMS = {
    U(r"\u809d\u4e0d\u597d"), U(r"\u809d\u529f\u80fd\u969c\u788d"), U(r"\u809d\u529f\u80fd\u5f02\u5e38"),
    U(r"\u809d\u75c5"), U(r"\u8102\u80aa\u809d"), U(r"\u80c6\u7ed3\u77f3"), U(r"\u80c6\u56ca\u708e"),
    U(r"\u80c6\u4e0d\u597d"), U(r"\u5bb9\u6613\u4e0a\u706b"), U(r"\u809d\u706b\u5927"), U(r"\u809d\u706b\u65fa"),
}

HEART_FIRST_STEP_TERMS = {
    U(r"\u5fc3\u4e0d\u597d"), U(r"\u5fc3\u810f\u4e0d\u597d"), U(r"\u5fc3\u529f\u80fd\u969c\u788d"),
    U(r"\u5fc3\u529f\u80fd\u4e0d\u597d"), U(r"\u5fc3\u808c\u7f3a\u8840"), U(r"\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"),
    U(r"\u5931\u7720"), U(r"\u8033\u9e23"), U(r"\u6291\u90c1\u75c7"), U(r"\u5fc3\u614c"), U(r"\u80f8\u95f7"),
}

DOMAIN_CONFIGS: dict[str, dict[str, Any]] = {
    "digestive": {
        "broad_conditions": {U(r"\u6d88\u5316\u9053\u75be\u75c5")},
        "trigger_aliases": {
            U(r"\u80c3\u4e0d\u8212\u670d"), U(r"\u80c3\u4e0d\u597d"), U(r"\u80c3\u96be\u53d7"), U(r"\u80a0\u80c3\u4e0d\u597d"),
            U(r"\u813e\u80c3\u4e0d\u597d"), U(r"\u813e\u4e0d\u597d"), U(r"\u6d88\u5316\u4e0d\u597d"), U(r"\u996d\u540e\u80c0"), U(r"\u53cd\u9178"),
            U(r"\u70e7\u5fc3"), U(r"\u98df\u6b32\u5dee"), U(r"\u6ca1\u80c3\u53e3"), U(r"\u80c3\u70ed"), U(r"\u80c3\u706b\u5927"),
            U(r"\u4fbf\u79d8"), U(r"\u80a0\u708e"), U(r"\u80a0\u5316\u751f"),
        },
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u813e\u80c3/\u6d88\u5316\u60c5\u51b5\uff1f"),
        "options": [
            {"label": U(r"\u996d\u540e\u9971\u80c0"), "value": U(r"\u996d\u540e\u9971\u80c0"), "keywords": [U(r"\u996d\u540e\u9971\u80c0"), U(r"\u5403\u5b8c\u996d\u80c0"), U(r"\u996d\u540e\u80c0")]},
            {"label": U(r"\u53cd\u9178\u70e7\u5fc3"), "value": U(r"\u53cd\u9178"), "keywords": [U(r"\u53cd\u9178"), U(r"\u70e7\u5fc3"), U(r"\u80c3\u9178")]},
            {"label": U(r"\u98df\u6b32\u4e0d\u632f"), "value": U(r"\u98df\u6b32\u4e0d\u632f"), "keywords": [U(r"\u98df\u6b32\u4e0d\u632f"), U(r"\u6ca1\u80c3\u53e3"), U(r"\u5403\u4e0d\u4e0b\u996d")]},
            {"label": U(r"\u513f\u7ae5\u6d88\u5316\u4e0d\u826f\u53ca\u6d88\u7626"), "value": U(r"\u513f\u7ae5\u6d88\u5316\u4e0d\u826f\u53ca\u6d88\u7626"), "keywords": [U(r"\u513f\u7ae5\u6d88\u5316\u4e0d\u826f"), U(r"\u5b69\u5b50\u6d88\u5316\u4e0d\u826f")]},
            {"label": U(r"\u80c3\u706b\u5927/\u80c3\u70ed"), "value": U(r"\u80c3\u706b\u5927"), "keywords": [U(r"\u80c3\u706b\u5927"), U(r"\u80c3\u70ed")]},
            {"label": U(r"\u4fbf\u79d8"), "value": U(r"\u4fbf\u79d8"), "keywords": [U(r"\u4fbf\u79d8"), U(r"\u6392\u4fbf\u56f0\u96be")]},
            {"label": U(r"\u840e\u7f29\u6027\u80c3\u708e"), "value": U(r"\u840e\u7f29\u6027\u80c3\u708e"), "keywords": [U(r"\u840e\u7f29\u6027\u80c3\u708e")]},
            {"label": U(r"\u6162\u6027\u80a0\u708e"), "value": U(r"\u6162\u6027\u80a0\u708e"), "keywords": [U(r"\u6162\u6027\u80a0\u708e")]},
            {"label": U(r"\u80a0\u5316\u751f"), "value": U(r"\u80a0\u5316\u751f"), "keywords": [U(r"\u80a0\u5316\u751f")]},
        ],
        "sort_hints": [],
    },
    "bitter_mouth": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u53e3\u82e6"), U(r"\u5634\u91cc\u53d1\u82e6"), U(r"\u5634\u5df4\u53d1\u82e6"), U(r"\u53e3\u82e6\u53e3\u9ecf"),
            U(r"\u5634\u91cc\u82e6"), U(r"\u53e3\u91cc\u53d1\u82e6"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u53e3\u82e6\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u504f\u6e7f\u70ed/\u6e7f\u6c14\u91cd"), "value": U(r"\u6e7f\u70ed"), "keywords": [U(r"\u6e7f\u70ed"), U(r"\u6e7f\u6c14\u91cd"), U(r"\u53e3\u82e6\u53e3\u9ecf")]},
            {"label": U(r"\u504f\u809d\u706b\u65fa/\u5bb9\u6613\u4e0a\u706b"), "value": U(r"\u5bb9\u6613\u4e0a\u706b"), "keywords": [U(r"\u5bb9\u6613\u4e0a\u706b"), U(r"\u809d\u706b\u5927"), U(r"\u809d\u706b\u65fa"), U(r"\u706b\u6c14\u5927")]},
            {"label": U(r"\u504f\u813e\u80c3\u6e7f\u70ed/\u80c3\u706b\u5927"), "value": U(r"\u80c3\u706b\u5927"), "keywords": [U(r"\u80c3\u706b\u5927"), U(r"\u80c3\u70ed"), U(r"\u813e\u80c3\u6e7f\u70ed"), U(r"\u80c3\u4e0d\u8212\u670d")]},
        ],
        "sort_hints": [],
    },
    "irritability": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u6613\u6012"), U(r"\u5bb9\u6613\u751f\u6c14"), U(r"\u7231\u53d1\u813e\u6c14"), U(r"\u706b\u6c14\u5927"),
            U(r"\u8107\u6c14\u66b4"), U(r"\u70e6\u8e81\u6613\u6012"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u6613\u6012\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u504f\u809d\u706b\u65fa/\u5bb9\u6613\u4e0a\u706b"), "value": U(r"\u5bb9\u6613\u4e0a\u706b"), "keywords": [U(r"\u5bb9\u6613\u4e0a\u706b"), U(r"\u809d\u706b\u5927"), U(r"\u809d\u706b\u65fa"), U(r"\u706b\u6c14\u5927")]},
            {"label": U(r"\u504f\u6e7f\u70ed/\u53e3\u82e6\u5fc3\u70e6"), "value": U(r"\u6e7f\u70ed"), "keywords": [U(r"\u6e7f\u70ed"), U(r"\u53e3\u82e6"), U(r"\u53e3\u82e6\u53e3\u9ecf"), U(r"\u53e3\u9ecf")]},
            {"label": U(r"\u504f\u7761\u7720\u5dee/\u60c5\u7eea\u70e6\u8e81"), "value": U(r"\u5931\u7720"), "keywords": [U(r"\u5931\u7720"), U(r"\u7761\u4e0d\u597d"), U(r"\u70e6\u8e81"), U(r"\u60c5\u7eea\u4f4e\u843d")]},
        ],
        "sort_hints": [],
    },
    "restlessness": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u5fc3\u70e6"), U(r"\u5fc3\u91cc\u70e6"), U(r"\u70e6\u8e81"), U(r"\u70e6\u5f97\u5f88"),
            U(r"\u603b\u89c9\u5f97\u5fc3\u91cc\u70e6"), U(r"\u60c5\u7eea\u70e6\u8e81"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u5fc3\u70e6\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u504f\u5fc3\u706b\u504f\u65fa/\u5fc3\u91cc\u70e6\u70ed"), "value": U(r"\u5fc3\u70e6"), "keywords": [U(r"\u5fc3\u706b"), U(r"\u70e6\u70ed"), U(r"\u5fc3\u91cc\u70ed")]},
            {"label": U(r"\u504f\u6e7f\u70ed/\u53e3\u82e6\u5fc3\u70e6"), "value": U(r"\u6e7f\u70ed"), "keywords": [U(r"\u6e7f\u70ed"), U(r"\u53e3\u82e6"), U(r"\u53e3\u82e6\u53e3\u9ecf"), U(r"\u53e3\u9ecf")]},
            {"label": U(r"\u504f\u5931\u7720/\u60c5\u7eea\u70e6\u8e81"), "value": U(r"\u5931\u7720"), "keywords": [U(r"\u5931\u7720"), U(r"\u7761\u4e0d\u597d"), U(r"\u591a\u68a6"), U(r"\u60c5\u7eea\u70e6\u8e81")]},
        ],
        "sort_hints": [],
    },
    "anxiety": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u7126\u8651"), U(r"\u5fc3\u91cc\u603b\u662f\u5f88\u6162"), U(r"\u5bb9\u6613\u7d27\u5f20"), U(r"\u603b\u662f\u62c5\u5fc3"),
            U(r"\u5fc3\u795e\u4e0d\u5b81"), U(r"\u5fc3\u91cc\u4e0d\u8e0f\u5b9e"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u7126\u8651\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u504f\u5931\u7720/\u5fc3\u795e\u4e0d\u5b81"), "value": U(r"\u5931\u7720"), "keywords": [U(r"\u5931\u7720"), U(r"\u7761\u4e0d\u597d"), U(r"\u5fc3\u795e\u4e0d\u5b81"), U(r"\u591a\u68a6")]},
            {"label": U(r"\u504f\u60c5\u7eea\u4f4e\u843d/\u6291\u90c1"), "value": U(r"\u6291\u90c1\u75c7"), "keywords": [U(r"\u6291\u90c1"), U(r"\u60c5\u7eea\u4f4e\u843d"), U(r"\u6291\u90c1\u75c7")]},
            {"label": U(r"\u504f\u5fc3\u614c\u80f8\u95f7/\u5fc3\u7cfb\u4e0d\u9002"), "value": U(r"\u5fc3\u808c\u7f3a\u8840"), "keywords": [U(r"\u5fc3\u614c"), U(r"\u80f8\u95f7"), U(r"\u5fc3\u808c\u7f3a\u8840")]},
        ],
        "sort_hints": [],
    },
    "chest_tightness": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u80f8\u95f7"), U(r"\u80f8\u53e3\u53d1\u7d27"), U(r"\u80f8\u53e3\u4e0d\u8212\u670d"), U(r"\u80f8\u53e3\u5835"),
            U(r"\u5598\u4e0d\u8fc7\u6c14"), U(r"\u80f8\u53e3\u538b\u5f97\u614c"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u80f8\u95f7\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u504f\u5fc3\u808c\u7f3a\u8840/\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"), "value": U(r"\u5fc3\u808c\u7f3a\u8840"), "keywords": [U(r"\u5fc3\u808c\u7f3a\u8840"), U(r"\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"), U(r"\u5fc3\u614c")]},
            {"label": U(r"\u504f\u7126\u8651\u7d27\u5f20/\u60c5\u7eea\u6027\u80f8\u95f7"), "value": U(r"\u7126\u8651"), "keywords": [U(r"\u7126\u8651"), U(r"\u7d27\u5f20"), U(r"\u60c5\u7eea\u6027\u80f8\u95f7")]},
            {"label": U(r"\u504f\u547c\u5438\u4e0d\u7545/\u6c14\u4e0d\u8db3"), "value": U(r"\u6c14\u4e0d\u8db3"), "keywords": [U(r"\u6c14\u4e0d\u8db3"), U(r"\u6c14\u77ed"), U(r"\u5598\u4e0d\u8fc7\u6c14")]},
        ],
        "sort_hints": [],
    },
    "respiratory": {
        "broad_conditions": {U(r"\u547c\u5438\u9053\u75be\u75c5")},
        "trigger_aliases": {
            U(r"\u547c\u5438\u4e0d\u597d"), U(r"\u611f\u5192"), U(r"\u6d41\u611f"), U(r"\u54bd\u708e"), U(r"\u652f\u6c14\u7ba1\u708e"),
            U(r"\u6162\u6027\u652f\u6c14\u7ba1\u708e"), U(r"\u80ba\u6c14\u80bf"), U(r"\u80ba\u7ed3\u8282"), U(r"\u8fc7\u654f\u6027\u9f3b\u708e"),
            U(r"\u9f3b\u708e"), U(r"\u80ba\u4e0d\u597d"), U(r"\u80ba\u529f\u80fd\u969c\u788d"), U(r"\u80ba\u529f\u80fd\u5dee"),
            U(r"\u6c14\u4e0d\u8db3"), U(r"\u6c14\u77ed"), U(r"\u5598"), U(r"\u54b3\u55fd"), U(r"\u75f0\u591a"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u7c7b\u547c\u5438\u9053\u95ee\u9898\u76ee\u524d\u6709\u6ca1\u6709\u660e\u663e\u6c14\u4e0d\u8db3\u3001\u6c14\u77ed\u6216\u5bb9\u6613\u5598\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u6709\u6c14\u4e0d\u8db3/\u6c14\u77ed\uff0c\u60f3\u8865\u6c14"), "value": U(r"\u6c14\u4e0d\u8db3"), "keywords": [U(r"\u6c14\u4e0d\u8db3"), U(r"\u6c14\u77ed"), U(r"\u5bb9\u6613\u5598")]},
            {"label": U(r"\u6682\u65f6\u6ca1\u6709\u660e\u663e\u6c14\u4e0d\u8db3"), "value": U(r"\u547c\u5438\u5e73\u7a33"), "keywords": [U(r"\u547c\u5438\u5e73\u7a33"), U(r"\u6ca1\u6709\u660e\u663e\u6c14\u77ed")]},
        ],
        "sort_hints": [],
    },
    "sleep": {
        "broad_conditions": set(),
        "trigger_aliases": {U(r"\u7761\u4e0d\u597d"), U(r"\u5931\u7720"), U(r"\u534a\u591c\u9192"), U(r"\u591a\u68a6"), U(r"\u6291\u90c1")},
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u76ee\u524d\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u7761\u7720/\u60c5\u7eea\u72b6\u6001\uff1f"),
        "options": [
            {"label": U(r"\u5165\u7761\u56f0\u96be/\u7761\u4e0d\u8e0f\u5b9e"), "value": U(r"\u5931\u7720"), "keywords": [U(r"\u5931\u7720"), U(r"\u7761\u4e0d\u7740"), U(r"\u591a\u68a6")]},
            {"label": U(r"\u5931\u7720\u4e14\u5e38\u5934\u6655"), "value": U(r"\u8111\u4f9b\u8840\u4e0d\u8db3"), "keywords": [U(r"\u8111\u4f9b\u8840\u4e0d\u8db3"), U(r"\u5934\u6655")]},
            {"label": U(r"\u60c5\u7eea\u4f4e\u843d/\u6291\u90c1"), "value": U(r"\u6291\u90c1\u75c7"), "keywords": [U(r"\u6291\u90c1\u75c7"), U(r"\u60c5\u7eea\u4f4e\u843d")]},
            {"label": U(r"\u6ce8\u610f\u529b\u5dee/\u5b66\u4e60\u80fd\u529b\u5dee"), "value": U(r"\u5b66\u4e60\u80fd\u529b\u5dee"), "keywords": [U(r"\u5b66\u4e60\u80fd\u529b\u5dee"), U(r"\u6ce8\u610f\u529b\u4e0d\u96c6\u4e2d")]},
        ],
        "sort_hints": [],
    },
    "metabolic": {
        "broad_conditions": {U(r"\u8840\u538b\u9ad8\u3001\u8840\u7cd6\u9ad8\u3001\u5c3f\u9178\u9ad8\u3001\u8840\u8102\u9ad8")},
        "trigger_aliases": {U(r"\u4e09\u9ad8"), U(r"\u8840\u538b\u9ad8"), U(r"\u8840\u7cd6\u9ad8"), U(r"\u7cd6\u5c3f\u75c5"), U(r"\u8840\u8102\u9ad8"), U(r"\u5c3f\u9178\u9ad8"), U(r"\u80a5\u80d6"), U(r"\u75db\u98ce")},
        "question": U(r"\u4e3a\u4e86\u66f4\u51c6\u786e\u63a8\u8350\uff0c\u60f3\u786e\u8ba4\u4e00\u4e0b\u60a8\u76ee\u524d\u66f4\u4e3b\u8981\u662f\u54ea\u4e00\u7c7b\u4e09\u9ad8/\u4ee3\u8c22\u95ee\u9898\uff1f"),
        "options": [
            {"label": U(r"\u8840\u538b\u9ad8\u66f4\u7a81\u51fa"), "value": U(r"\u4e25\u91cd\u9ad8\u8840\u538b"), "keywords": [U(r"\u8840\u538b\u9ad8"), U(r"\u9ad8\u8840\u538b")]},
            {"label": U(r"\u8840\u7cd6\u9ad8/\u7cd6\u5c3f\u75c5\u66f4\u7a81\u51fa"), "value": U(r"\u4e25\u91cd\u8840\u7cd6\u9ad8"), "keywords": [U(r"\u8840\u7cd6\u9ad8"), U(r"\u7cd6\u5c3f\u75c5")]},
            {"label": U(r"\u8840\u8102\u9ad8\u66f4\u7a81\u51fa"), "value": U(r"\u4e25\u91cd\u9ad8\u8840\u8102"), "keywords": [U(r"\u8840\u8102\u9ad8"), U(r"\u9ad8\u8840\u8102")]},
            {"label": U(r"\u5c3f\u9178\u9ad8/\u75db\u98ce\u66f4\u7a81\u51fa"), "value": U(r"\u4e25\u91cd\u9ad8\u5c3f\u9178"), "keywords": [U(r"\u5c3f\u9178\u9ad8"), U(r"\u75db\u98ce")]},
            {"label": U(r"\u4f53\u91cd\u8d85\u6807/\u80a5\u80d6"), "value": U(r"\u80a5\u80d6\u75c7"), "keywords": [U(r"\u80a5\u80d6"), U(r"\u4f53\u91cd\u8d85\u6807")]},
        ],
        "sort_hints": [],
    },
    "renal": {
        "broad_conditions": set(),
        "trigger_aliases": {U(r"\u80be\u4e0d\u597d"), U(r"\u80be\u529f\u80fd\u969c\u788d"), U(r"\u80be\u865a"), U(r"\u80be\u708e"), U(r"\u80be\u7ed3\u77f3"), U(r"\u80be\u706b\u5927")},
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u7c7b\u80be\u7cfb\u95ee\u9898\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u80be\u706b\u5927"), "value": U(r"\u80be\u706b\u5927"), "keywords": [U(r"\u80be\u706b\u5927")]},
            {"label": U(r"\u80be\u7ed3\u77f3"), "value": U(r"\u80be\u7ed3\u77f3"), "keywords": [U(r"\u80be\u7ed3\u77f3")]},
            {"label": U(r"\u80be\u708e/\u80be\u529f\u80fd\u4e0d\u5168"), "value": U(r"\u80be\u529f\u80fd\u4e0d\u5168"), "keywords": [U(r"\u80be\u708e"), U(r"\u80be\u529f\u80fd\u4e0d\u5168"), U(r"\u80be\u529f\u80fd\u969c\u788d")]},
            {"label": U(r"\u504f\u80be\u865a/\u8170\u8189\u9178\u8f6f"), "value": U(r"\u80be\u865a"), "keywords": [U(r"\u80be\u865a"), U(r"\u8170\u8189\u9178\u8f6f")]},
        ],
        "sort_hints": [],
    },
    "liver": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u809d\u4e0d\u597d"), U(r"\u809d\u529f\u80fd\u969c\u788d"), U(r"\u809d\u529f\u80fd\u4e0d\u597d"), U(r"\u809d\u529f\u80fd\u5f02\u5e38"),
            U(r"\u809d\u75c5"), U(r"\u8102\u80aa\u809d"), U(r"\u809d\u635f\u4f24"), U(r"\u80c6\u7ed3\u77f3"), U(r"\u80c6\u56ca\u708e"),
            U(r"\u80c6\u4e0d\u597d"), U(r"\u80c6\u56ca\u4e0d\u597d"), U(r"\u5bb9\u6613\u4e0a\u706b"), U(r"\u4e0a\u706b"),
            U(r"\u706b\u6c14\u5927"), U(r"\u809d\u706b\u5927"), U(r"\u809d\u706b\u65fa"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u7c7b\u809d\u80c6\u76f8\u5173\u95ee\u9898\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u8102\u80aa\u809d"), "value": U(r"\u8102\u80aa\u809d"), "keywords": [U(r"\u8102\u80aa\u809d"), U(r"\u8f7b\u5ea6\u8102\u80aa\u809d"), U(r"\u4e2d\u5ea6\u8102\u80aa\u809d"), U(r"\u91cd\u5ea6\u8102\u80aa\u809d"), U(r"\u4e2d\u91cd\u5ea6\u8102\u80aa\u809d"), U(r"\u8102\u80aa\u809d\u4e25\u91cd")]},
            {"label": U(r"\u5176\u4ed6\u809d\u75c5/\u809d\u635f\u4f24"), "value": U(r"\u809d\u75c5"), "keywords": [U(r"\u809d\u75c5"), U(r"\u809d\u708e"), U(r"\u809d\u786c\u5316"), U(r"\u809d\u635f\u4f24")]},
            {"label": U(r"\u80c6\u7ed3\u77f3/\u80c6\u56ca\u708e"), "value": U(r"\u80c6\u7ed3\u77f3\u3001\u80c6\u56ca\u708e"), "keywords": [U(r"\u80c6\u7ed3\u77f3"), U(r"\u80c6\u56ca\u708e")]},
            {"label": U(r"\u5bb9\u6613\u4e0a\u706b/\u809d\u706b\u504f\u65fa"), "value": U(r"\u5bb9\u6613\u4e0a\u706b"), "keywords": [U(r"\u5bb9\u6613\u4e0a\u706b"), U(r"\u4e0a\u706b"), U(r"\u706b\u6c14\u5927"), U(r"\u809d\u706b\u5927"), U(r"\u809d\u706b\u65fa")]},
        ],
        "sort_hints": [],
    },
    "heart": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u5fc3\u4e0d\u597d"), U(r"\u5fc3\u810f\u4e0d\u597d"), U(r"\u5fc3\u529f\u80fd\u969c\u788d"), U(r"\u5fc3\u529f\u80fd\u4e0d\u597d"),
            U(r"\u5fc3\u808c\u7f3a\u8840"), U(r"\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"), U(r"\u8033\u9e23"), U(r"\u5fc3\u614c"),
            U(r"\u80f8\u95f7"), U(r"\u80f8\u53e3\u53d1\u7d27"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u7c7b\u5fc3\u7cfb\u76f8\u5173\u95ee\u9898\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u5fc3\u808c\u7f3a\u8840/\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"), "value": U(r"\u5fc3\u808c\u7f3a\u8840"), "keywords": [U(r"\u5fc3\u808c\u7f3a\u8840"), U(r"\u5fc3\u810f\u4f9b\u8840\u4e0d\u8db3"), U(r"\u5fc3\u614c"), U(r"\u80f8\u95f7"), U(r"\u80f8\u53e3\u53d1\u7d27")]},
            {"label": U(r"\u8033\u9e23"), "value": U(r"\u8033\u9e23"), "keywords": [U(r"\u8033\u9e23")]},
            {"label": U(r"\u5931\u7720/\u5165\u7761\u56f0\u96be"), "value": U(r"\u5931\u7720"), "keywords": [U(r"\u5931\u7720"), U(r"\u7761\u4e0d\u597d"), U(r"\u7761\u4e0d\u7740"), U(r"\u5165\u7761\u56f0\u96be"), U(r"\u534a\u591c\u9192")]},
            {"label": U(r"\u60c5\u7eea\u4f4e\u843d/\u6291\u90c1"), "value": U(r"\u6291\u90c1\u75c7"), "keywords": [U(r"\u6291\u90c1\u75c7"), U(r"\u6291\u90c1"), U(r"\u60c5\u7eea\u4f4e\u843d")]},
        ],
        "sort_hints": [],
    },
    "andrology": {
        "broad_conditions": set(),
        "trigger_aliases": {U(r"\u7537\u79d1"), U(r"\u9633\u75ff"), U(r"\u65e9\u6cc4"), U(r"\u8170\u9178\u817f\u8f6f"), U(r"\u80be\u865a")},
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u7537\u79d1/\u80be\u7cbe\u4e0d\u8db3\u60c5\u51b5\uff1f"),
        "options": [
            {"label": U(r"\u7537\u6027\u9633\u75ff"), "value": U(r"\u7537\u6027\u9633\u75ff"), "keywords": [U(r"\u7537\u6027\u9633\u75ff"), U(r"\u9633\u75ff")]},
            {"label": U(r"\u65e9\u6cc4"), "value": U(r"\u65e9\u6cc4"), "keywords": [U(r"\u65e9\u6cc4")]},
            {"label": U(r"\u8170\u9178\u817f\u8f6f/\u80be\u7cbe\u4e0d\u8db3"), "value": U(r"\u8170\u9178\u817f\u8f6f"), "keywords": [U(r"\u8170\u9178\u817f\u8f6f"), U(r"\u80be\u865a")]},
        ],
        "sort_hints": [],
    },
    "gynecology": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u5987\u79d1"), U(r"\u5973\u6027\u5bab\u5bd2"), U(r"\u5bab\u5bd2"), U(r"\u6708\u7ecf\u4e0d\u8c03"), U(r"\u75db\u7ecf"),
            U(r"\u8170\u9178\u817f\u8f6f"), U(r"\u9762\u5bb9\u67af\u6697"), U(r"\u5987\u79d1\u80bf\u7624"), U(r"\u5375\u5de2\u56ca\u80bf"),
            U(r"\u5b50\u5bab\u808c\u7624"), U(r"\u4e73\u817a\u7ed3\u8282"), U(r"\u7532\u72b6\u817a\u7ed3\u8282"), U(r"\u764c\u524d\u75c5\u53d8"),
            U(r"\u80a0\u5316\u751f"), U(r"\u6162\u6027\u80a0\u708e"), U(r"\u5404\u7c7b\u7ed3\u8282\u75c5"), U(r"\u529f\u8840"), U(r"\u6708\u7ecf\u8fc7\u591a"),
        },
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u4e00\u7c7b\u5987\u79d1/\u7ed3\u8282\u76f8\u5173\u60c5\u51b5\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u5973\u6027\u5bab\u5bd2"), "value": U(r"\u5973\u6027\u5bab\u5bd2"), "keywords": [U(r"\u5973\u6027\u5bab\u5bd2"), U(r"\u5bab\u5bd2")]},
            {"label": U(r"\u6708\u7ecf\u4e0d\u8c03"), "value": U(r"\u6708\u7ecf\u4e0d\u8c03"), "keywords": [U(r"\u6708\u7ecf\u4e0d\u8c03")]},
            {"label": U(r"\u75db\u7ecf"), "value": U(r"\u75db\u7ecf"), "keywords": [U(r"\u75db\u7ecf")]},
            {"label": U(r"\u8170\u9178\u817f\u8f6f/\u9762\u5bb9\u67af\u6697"), "value": U(r"\u8170\u9178\u817f\u8f6f"), "keywords": [U(r"\u8170\u9178\u817f\u8f6f"), U(r"\u9762\u5bb9\u67af\u6697")]},
            {"label": U(r"\u5987\u79d1\u80bf\u7624"), "value": U(r"\u5987\u79d1\u80bf\u7624"), "keywords": [U(r"\u5987\u79d1\u80bf\u7624")]},
            {"label": U(r"\u5375\u5de2\u56ca\u80bf/\u5b50\u5bab\u808c\u7624\u7b49\u7ed3\u8282\u75c5"), "value": U(r"\u5375\u5de2\u56ca\u80bf"), "keywords": [U(r"\u5375\u5de2\u56ca\u80bf"), U(r"\u5b50\u5bab\u808c\u7624"), U(r"\u764c\u524d\u75c5\u53d8"), U(r"\u80a0\u5316\u751f"), U(r"\u6162\u6027\u80a0\u708e"), U(r"\u5404\u7c7b\u7ed3\u8282\u75c5")]},
            {"label": U(r"\u4e73\u817a\u6216\u7532\u72b6\u817a\u7ed3\u8282"), "value": U(r"\u4e73\u817a\u7ed3\u8282"), "keywords": [U(r"\u4e73\u817a\u7ed3\u8282"), U(r"\u7532\u72b6\u817a\u7ed3\u8282")]},
            {"label": U(r"\u6708\u7ecf\u8fc7\u591a/\u529f\u8840"), "value": U(r"\u529f\u8840(\u6708\u7ecf\u8fc7\u591a)"), "keywords": [U(r"\u529f\u8840"), U(r"\u6708\u7ecf\u8fc7\u591a")]},
        ],
        "sort_hints": [],
    },
    "visual_blur": {
        "broad_conditions": set(),
        "trigger_aliases": {
            U(r"\u89c6\u529b\u6a21\u7cca"), U(r"\u770b\u4e0d\u6e05"), U(r"\u770b\u4e1c\u897f\u6a21\u7cca"), U(r"\u773c\u524d\u53d1\u82b1"),
        },
        "question": U(r"\u60f3\u518d\u786e\u8ba4\u4e00\u4e0b\uff0c\u60a8\u8fd9\u79cd\u89c6\u529b\u6a21\u7cca\u662f\u5426\u540c\u65f6\u6709\u7cd6\u5c3f\u75c5\u53f2\uff1f"),
        "force_clarify": True,
        "options": [
            {"label": U(r"\u6709\u7cd6\u5c3f\u75c5\u53f2"), "value": U(r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2"), "keywords": [U(r"\u7cd6\u5c3f\u75c5\u53f2"), U(r"\u6709\u7cd6\u5c3f\u75c5"), U(r"\u8840\u7cd6\u9ad8")]},
            {"label": U(r"\u6ca1\u6709\u7cd6\u5c3f\u75c5\u53f2"), "value": U(r"\u89c6\u529b\u6a21\u7cca"), "keywords": [U(r"\u6ca1\u6709\u7cd6\u5c3f\u75c5"), U(r"\u65e0\u7cd6\u5c3f\u75c5\u53f2")]},
        ],
        "sort_hints": [],
    },
    "ophthalmology": {
        "broad_conditions": set(),
        "trigger_aliases": {U(r"\u773c\u5e72"), U(r"\u773c\u6da9"), U(r"\u773c\u75b2\u52b3"), U(r"\u773c\u775b\u4e0d\u8212\u670d"), U(r"\u89c6\u529b\u6a21\u7cca"), U(r"\u660e\u76ee")},
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u773c\u90e8\u60c5\u51b5\uff1f"),
        "options": [
            {"label": U(r"\u89c6\u529b\u6a21\u7cca"), "value": U(r"\u89c6\u529b\u6a21\u7cca"), "keywords": [U(r"\u89c6\u529b\u6a21\u7cca"), U(r"\u770b\u4e0d\u6e05")]},
            {"label": U(r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2"), "value": U(r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2"), "keywords": [U(r"\u89c6\u529b\u6a21\u7cca\u4e14\u6709\u7cd6\u5c3f\u75c5\u53f2")]},
            {"label": U(r"\u773c\u5e72/\u773c\u6da9/\u773c\u75b2\u52b3"), "value": U(r"\u7f13\u89e3\u773c\u75b2\u52b3"), "keywords": [U(r"\u773c\u5e72"), U(r"\u773c\u775b\u5e72"), U(r"\u773c\u6da9"), U(r"\u773c\u75b2\u52b3")]},
            {"label": U(r"\u957f\u671f\u7528\u773c\u591a/\u9700\u8981\u62a4\u809d\u660e\u76ee"), "value": U(r"\u62a4\u809d\u660e\u76ee"), "keywords": [U(r"\u62a4\u809d\u660e\u76ee"), U(r"\u660e\u76ee")]},
        ],
        "sort_hints": [],
    },
    "nodules": {
        "broad_conditions": {U(r"\u4e73\u817a\u7ed3\u8282\u3001\u7532\u72b6\u817a\u7ed3\u8282")},
        "trigger_aliases": {U(r"\u4e73\u817a\u7ed3\u8282"), U(r"\u7532\u72b6\u817a\u7ed3\u8282"), U(r"\u4e73\u623f\u7ed3\u8282")},
        "question": U(r"\u60f3\u66f4\u51c6\u786e\u5224\u65ad\u4e00\u4e0b\uff0c\u60a8\u66f4\u63a5\u8fd1\u4e0b\u9762\u54ea\u79cd\u7ed3\u8282\u76f8\u5173\u60c5\u51b5\uff1f"),
        "options": [
            {"label": U(r"\u4e73\u817a\u7ed3\u8282"), "value": U(r"\u4e73\u817a\u7ed3\u8282"), "keywords": [U(r"\u4e73\u817a\u7ed3\u8282")]},
            {"label": U(r"\u7532\u72b6\u817a\u7ed3\u8282"), "value": U(r"\u7532\u72b6\u817a\u7ed3\u8282"), "keywords": [U(r"\u7532\u72b6\u817a\u7ed3\u8282")]},
            {"label": U(r"\u4e9a\u6025\u6027\u7532\u72b6\u817a\u708e"), "value": U(r"\u4e9a\u6025\u6027\u7532\u72b6\u817a\u708e"), "keywords": [U(r"\u4e9a\u6025\u6027\u7532\u72b6\u817a\u708e")]},
            {"label": U(r"\u7532\u72b6\u817a\u5f25\u6f2b\u6027\u75c5\u53d8"), "value": U(r"\u7532\u72b6\u817a\u5f25\u6f2b\u6027\u75c5\u53d8"), "keywords": [U(r"\u7532\u72b6\u817a\u5f25\u6f2b\u6027\u75c5\u53d8")]},
            {"label": U(r"\u7532\u51cf"), "value": U(r"\u7532\u51cf"), "keywords": [U(r"\u7532\u51cf")]},
        ],
        "sort_hints": [],
    },
}



