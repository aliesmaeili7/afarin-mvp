"""Strip secrets from eval metadata."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEY = re.compile(
    r"(api[_-]?key|authorization|secret|password|token|bearer)",
    re.I,
)
_SECRET_VALUE = re.compile(r"sk-[a-zA-Z0-9_-]{8,}")
_DATA_URL = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+")


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _SECRET_KEY.search(str(key)):
                out[str(key)] = "[redacted]"
                continue
            out[str(key)] = sanitize(item)
        return out
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        cleaned = _SECRET_VALUE.sub("[redacted]", value)
        return _DATA_URL.sub("[image-omitted]", cleaned)
    return value
