from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def schema(value: Any, depth: int = 0) -> Any:
    """Return a deterministic, value-free shape for an observed JSON response."""
    if depth > 5:
        return type(value).__name__
    if isinstance(value, Mapping):
        return {key: schema(value[key], depth + 1) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [] if not value else [schema(value[0], depth + 1)]
    return type(value).__name__
