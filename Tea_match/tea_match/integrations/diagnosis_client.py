from __future__ import annotations

import hashlib
import os
import time
from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_BASE_URL = "http://aibayes.cn/api/analysis"
DEFAULT_API_VERSION = "1.0"


@dataclass(frozen=True)
class DiagnosisApiSettings:
    app_id: str = ""
    app_secret: str = ""
    base_url: str = DEFAULT_BASE_URL
    version: str = DEFAULT_API_VERSION
    timeout: float = 30.0

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.app_secret:
            data["app_secret"] = "***configured***"
        return data


class DiagnosisClient:
    def __init__(self, settings: DiagnosisApiSettings | None = None):
        self.settings = settings or get_diagnosis_api_settings()

    def analyze(self, method: str, biz_params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.is_configured():
            raise RuntimeError(
                "Diagnosis API is not configured. Set DIAGNOSIS_APP_ID and DIAGNOSIS_APP_SECRET first."
            )

        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is not installed. Run `pip install requests` first.") from exc

        payload = self.build_common_params(method)
        payload.update(self._stringify_params(biz_params))

        response = requests.post(
            self.settings.base_url,
            data=payload,
            timeout=self.settings.timeout,
        )
        response.raise_for_status()
        return response.json()

    def build_common_params(self, method: str, timestamp: str | None = None) -> dict[str, str]:
        current_timestamp = timestamp or build_timestamp()
        return {
            "method": method,
            "timestamp": current_timestamp,
            "app_id": self.settings.app_id,
            "version": self.settings.version,
            "sign": build_sign(current_timestamp, self.settings.app_secret),
        }

    @staticmethod
    def _stringify_params(params: dict[str, Any]) -> dict[str, str]:
        payload: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            payload[key] = str(value)
        return payload


def md5_upper(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest().upper()


def build_timestamp() -> str:
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def build_sign(timestamp: str, app_secret: str) -> str:
    return md5_upper(md5_upper(timestamp) + app_secret)


def diagnosis_api_is_configured() -> bool:
    return get_diagnosis_api_settings().is_configured()


def get_diagnosis_api_settings() -> DiagnosisApiSettings:
    app_id = os.getenv("DIAGNOSIS_APP_ID", "").strip()
    app_secret = os.getenv("DIAGNOSIS_APP_SECRET", "").strip()
    base_url = os.getenv("DIAGNOSIS_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    version = os.getenv("DIAGNOSIS_API_VERSION", DEFAULT_API_VERSION).strip() or DEFAULT_API_VERSION
    timeout = float(os.getenv("DIAGNOSIS_TIMEOUT", "30"))

    return DiagnosisApiSettings(
        app_id=app_id,
        app_secret=app_secret,
        base_url=base_url,
        version=version,
        timeout=timeout,
    )
