from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_PATH = ".blackboard-sync/sources.json"


class SourceConfigError(ValueError):
    """Raised when an explicit source configuration is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class SourceConfig:
    provider: str
    instance: str
    root: str

    @property
    def root_path(self) -> Path:
        return Path(self.root)


def _default() -> tuple[SourceConfig, ...]:
    return (SourceConfig(provider="blackboard_ultra", instance="default", root="Blackboard"),)


def _validated_root(target: Path, root: str) -> str:
    normalized = root.strip().replace("\\", "/").strip("/")
    candidate = Path(normalized)
    if any(part in {".", ".."} for part in candidate.parts):
        raise SourceConfigError(f"source root fuera del workspace: segmentos no permitidos en {root}")
    workspace = Path(target).resolve()
    resolved = (workspace / candidate).resolve()
    if not normalized or candidate.is_absolute() or resolved == workspace or workspace not in resolved.parents:
        raise SourceConfigError(f"source root fuera del workspace: {root}")
    return normalized


def load_source_configs(target: Path) -> tuple[SourceConfig, ...]:
    path = Path(target) / _CONFIG_PATH
    if not path.is_file():
        return _default()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceConfigError(f"sources.json inválido: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != 1 or not isinstance(payload.get("sources"), list):
        raise SourceConfigError("sources.json tiene un schema inválido")
    configs: list[SourceConfig] = []
    for raw in payload["sources"]:
        if not isinstance(raw, dict):
            raise SourceConfigError("sources.json contiene una fuente inválida")
        provider = raw.get("provider")
        instance = raw.get("instance")
        root = raw.get("root")
        if not all(isinstance(value, str) and value.strip() for value in (provider, instance, root)):
            raise SourceConfigError("sources.json contiene campos vacíos o inválidos")
        configs.append(SourceConfig(provider=provider.strip(), instance=instance.strip(), root=_validated_root(target, root)))
    if not configs:
        raise SourceConfigError("sources.json debe declarar al menos una fuente")
    return tuple(configs)


def register_source(target: Path, provider: str, instance: str, root: str) -> SourceConfig:
    path = Path(target) / _CONFIG_PATH
    configs = [config for config in load_source_configs(target) if not (config.provider == provider and config.instance == instance)]
    new_config = SourceConfig(provider=provider.strip(), instance=instance.strip(), root=_validated_root(target, root))
    configs.append(new_config)
    payload = {"format": 1, "sources": [{"provider": item.provider, "instance": item.instance, "root": item.root} for item in configs]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (Path(target) / new_config.root).mkdir(parents=True, exist_ok=True)
    return new_config
