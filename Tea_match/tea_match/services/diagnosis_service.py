from __future__ import annotations

from typing import Any

from tea_match.integrations.diagnosis_client import DiagnosisClient


DEFAULT_TONGUE_METHOD = "TongueFaceAnalysis"
DEFAULT_PULSE_METHOD = "PulseAnalysis"
DEFAULT_TONGUE_BASE_METHOD = "TongueBaseAnalysis"


class DiagnosisService:
    def __init__(self, client: DiagnosisClient | None = None):
        self.client = client or DiagnosisClient()

    def analyze_tongue(
        self,
        tongue_img_path: str,
        face_img_path: str | None = None,
        age: int | str | None = None,
        gender: str | None = None,
        extra_params: dict[str, Any] | None = None,
        method: str = DEFAULT_TONGUE_METHOD,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "TongueImgpath": tongue_img_path,
            "FaceImgpath": face_img_path,
            "age": age,
            "gender": gender,
        }
        if extra_params:
            payload.update(extra_params)
        return self.client.analyze(method, payload)

    def analyze_pulse(
        self,
        pulse_params: dict[str, Any] | None = None,
        method: str = DEFAULT_PULSE_METHOD,
    ) -> dict[str, Any]:
        return self.client.analyze(method, pulse_params or {})

    def analyze_tongue_base(
        self,
        tongue_base_img_path: str,
        extra_params: dict[str, Any] | None = None,
        method: str = DEFAULT_TONGUE_BASE_METHOD,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "TongueBaseImgpath": tongue_base_img_path,
        }
        if extra_params:
            payload.update(extra_params)
        return self.client.analyze(method, payload)
