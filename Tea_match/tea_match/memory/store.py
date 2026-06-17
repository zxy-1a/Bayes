from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from tea_match.config import MEMORY_DIR


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonMemoryStore:
    """Small local memory store. Replace this with DB access when integrating user profiles."""

    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.memory_dir / "profiles.json"
        self.recommendation_path = self.memory_dir / "recommendation_events.jsonl"
        self.feedback_path = self.memory_dir / "feedback_events.jsonl"

    def get_profile(self, user_id: str) -> dict[str, Any]:
        profiles = self._read_profiles()
        return profiles.get(user_id, {"user_id": user_id, "created_at": utc_now(), "updated_at": utc_now()})

    def upsert_profile(self, user_id: str, updates: dict[str, Any] | None = None) -> dict[str, Any]:
        profiles = self._read_profiles()
        profile = profiles.get(user_id, {"user_id": user_id, "created_at": utc_now()})
        profile.update(updates or {})
        profile["updated_at"] = utc_now()
        profiles[user_id] = profile
        self._write_profiles(profiles)
        return profile

    def add_recommendation_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_id": f"rec_{uuid4().hex}",
            "user_id": user_id,
            "event_type": "recommendation",
            "created_at": utc_now(),
            **payload,
        }
        self._append_jsonl(self.recommendation_path, event)
        self.upsert_profile(user_id)
        return event

    def add_feedback_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_id": f"fb_{uuid4().hex}",
            "user_id": user_id,
            "event_type": "feedback",
            "created_at": utc_now(),
            **payload,
        }
        self._append_jsonl(self.feedback_path, event)
        self.upsert_profile(user_id)
        return event

    def list_recommendations(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._tail_user_events(self.recommendation_path, user_id, limit)

    def list_feedback(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._tail_user_events(self.feedback_path, user_id, limit)

    def _read_profiles(self) -> dict[str, Any]:
        if not self.profile_path.exists():
            return {}
        return json.loads(self.profile_path.read_text(encoding="utf-8-sig") or "{}")

    def _write_profiles(self, profiles: dict[str, Any]) -> None:
        self.profile_path.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, event: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _tail_user_events(self, path: Path, user_id: str, limit: int) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("user_id") == user_id:
                    events.append(event)
        return events[-limit:]

