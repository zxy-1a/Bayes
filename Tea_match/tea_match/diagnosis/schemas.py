from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    name: str
    source: str
    confidence: float | None = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuleHint:
    name: str
    rule_step: str
    source: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommended_teas: list[str] = field(default_factory=list)
    evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnosticSummary:
    constitution_hints: list[RuleHint] = field(default_factory=list)
    organ_hints: list[RuleHint] = field(default_factory=list)
    symptom_hints: list[RuleHint] = field(default_factory=list)
    tongue_signs: list[EvidenceItem] = field(default_factory=list)
    sublingual_signs: list[EvidenceItem] = field(default_factory=list)
    pulse_signs: list[EvidenceItem] = field(default_factory=list)
    syndrome_signs: list[EvidenceItem] = field(default_factory=list)
    syndrome_hints: list[str] = field(default_factory=list)
    raw_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constitution_hints": [item.to_dict() for item in self.constitution_hints],
            "organ_hints": [item.to_dict() for item in self.organ_hints],
            "symptom_hints": [item.to_dict() for item in self.symptom_hints],
            "tongue_signs": [item.to_dict() for item in self.tongue_signs],
            "sublingual_signs": [item.to_dict() for item in self.sublingual_signs],
            "pulse_signs": [item.to_dict() for item in self.pulse_signs],
            "syndrome_signs": [item.to_dict() for item in self.syndrome_signs],
            "syndrome_hints": list(self.syndrome_hints),
            "raw_summary": dict(self.raw_summary),
        }
