from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class QdrantSettings:
    url: str = "http://localhost:6333"
    api_key: str | None = None
    prefer_grpc: bool = False
    timeout: float = 10.0
    https: bool | None = None
    collection_prefix: str = "tea_match"

    def client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "url": self.url,
            "prefer_grpc": self.prefer_grpc,
            "timeout": self.timeout,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.https is not None:
            kwargs["https"] = self.https
        return kwargs

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.api_key:
            data["api_key"] = "***configured***"
        return data

    def collection_name(self, base_name: str) -> str:
        prefix = self.collection_prefix.strip()
        return f"{prefix}_{base_name}" if prefix else base_name



def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def qdrant_is_configured() -> bool:
    url = os.getenv("QDRANT_URL", "").strip()
    host = os.getenv("QDRANT_HOST", "").strip()
    return bool(url or host)



def get_qdrant_settings() -> QdrantSettings:
    url = os.getenv("QDRANT_URL", "").strip()
    host = os.getenv("QDRANT_HOST", "").strip()
    port = os.getenv("QDRANT_PORT", "6333").strip() or "6333"
    api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
    prefer_grpc = _parse_bool(os.getenv("QDRANT_PREFER_GRPC"), False)
    timeout = float(os.getenv("QDRANT_TIMEOUT", "10"))
    https_env = os.getenv("QDRANT_HTTPS")
    https = _parse_bool(https_env, False) if https_env is not None else None
    collection_prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "tea_match").strip()

    if not url:
        if host:
            scheme = "https" if https else "http"
            url = f"{scheme}://{host}:{port}"
        else:
            url = "http://localhost:6333"

    return QdrantSettings(
        url=url,
        api_key=api_key,
        prefer_grpc=prefer_grpc,
        timeout=timeout,
        https=https,
        collection_prefix=collection_prefix,
    )


@lru_cache(maxsize=1)
def get_qdrant_client():
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise RuntimeError(
            "qdrant-client is not installed. Run `pip install qdrant-client` in your project environment first."
        ) from exc

    settings = get_qdrant_settings()
    return QdrantClient(**settings.client_kwargs())
