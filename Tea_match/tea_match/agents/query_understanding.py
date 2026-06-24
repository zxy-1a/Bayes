from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from tea_match.config import PROJECT_ROOT

MOCK_ENV_VALUES = {"1", "true", "yes", "on"}


class QueryUnderstandingAgent:
    """LLM-backed query understanding. It does not decide final tea products."""

    def __init__(self, project_root: Path = PROJECT_ROOT, use_mock: bool | None = None):
        self.project_root = project_root
        self.use_mock = use_mock

    def understand(
        self,
        query: str,
        selected_symptoms: list[str] | None = None,
        memory_summary: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        selected_symptoms = selected_symptoms or []
        if self._should_use_mock():
            data = self._run_understand_query(query, selected_symptoms, use_mock=True, fallback_to_mock=False)
        else:
            try:
                data = self._run_understand_query(query, selected_symptoms, use_mock=False, fallback_to_mock=True)
            except RuntimeError:
                data = self._run_understand_query(query, selected_symptoms, use_mock=True, fallback_to_mock=False)
        complaints = data.get("complaints", [])
        return complaints if isinstance(complaints, list) else []

    def _run_understand_query(
        self,
        query: str,
        selected_symptoms: list[str],
        use_mock: bool,
        fallback_to_mock: bool,
    ) -> dict[str, Any]:
        cmd = [sys.executable, "understand_query.py", query or "", "--pretty"]
        if selected_symptoms:
            cmd.extend(["--selected-symptoms", *selected_symptoms])
        if use_mock:
            cmd.append("--mock")
        elif fallback_to_mock:
            cmd.append("--fallback-to-mock")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "understand_query failed").strip()
            raise RuntimeError(message)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"understand_query returned invalid JSON: {exc}") from exc

    def _should_use_mock(self) -> bool:
        if self.use_mock is not None:
            return self.use_mock
        return os.getenv("USE_MOCK_UNDERSTANDING", "").lower() in MOCK_ENV_VALUES

