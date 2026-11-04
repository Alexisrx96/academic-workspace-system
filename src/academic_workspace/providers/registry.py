from __future__ import annotations

from collections.abc import Callable
from typing import Any


ProviderFactory = Callable[..., Any]
_FACTORIES: dict[str, ProviderFactory] = {}


def register_provider(provider_id: str, factory: ProviderFactory) -> None:
    if not provider_id or not provider_id.strip():
        raise ValueError("provider_id no puede estar vacío")
    _FACTORIES[provider_id] = factory


def get_provider(provider_id: str) -> ProviderFactory:
    try:
        return _FACTORIES[provider_id]
    except KeyError as error:
        available = ", ".join(sorted(_FACTORIES)) or "ninguno"
        raise KeyError(f"Proveedor desconocido: {provider_id}. Disponibles: {available}") from error


def available_providers() -> tuple[str, ...]:
    return tuple(sorted(_FACTORIES))
