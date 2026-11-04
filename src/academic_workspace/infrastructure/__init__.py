"""Infrastructure adapters exposed for composition, not domain use."""

from academic_workspace.memory import MemoryStore, memory_store_for_workspace
from academic_workspace.source_config import SourceConfig, load_source_configs

__all__ = ["MemoryStore", "SourceConfig", "load_source_configs", "memory_store_for_workspace"]
