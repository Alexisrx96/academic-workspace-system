"""Provider contracts and built-in source adapters."""

from .contracts import (
    AcademicSourceProvider,
    SourceCapabilities,
    SourceCourse,
    SourceHealth,
    SourceIdentity,
    SourceItem,
    SourceSnapshot,
)
from .blackboard_ultra import BlackboardUltraProvider
from .fixture import FixtureProvider
from .self_directed import SelfDirectedProvider
from .platzi import PlatziProvider
from .registry import available_providers, get_provider, register_provider

register_provider("fixture", FixtureProvider)
register_provider("blackboard_ultra", BlackboardUltraProvider)
register_provider("self_directed", SelfDirectedProvider)
register_provider("platzi", PlatziProvider)

__all__ = [
    "AcademicSourceProvider",
    "BlackboardUltraProvider",
    "FixtureProvider",
    "SelfDirectedProvider",
    "PlatziProvider",
    "SourceCapabilities",
    "SourceCourse",
    "SourceHealth",
    "SourceIdentity",
    "SourceItem",
    "SourceSnapshot",
    "available_providers",
    "get_provider",
    "register_provider",
]
