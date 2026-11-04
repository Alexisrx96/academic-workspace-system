from __future__ import annotations

from pathlib import Path
from typing import Any

from ..academic_results import build_results_report, result_attention_lines
from ..ai_study_context import build_ai_study_context
from ..companion_contracts import EvidenceRecord, ExternalSourceRecord, ValidationRecord
from ..companion_kernel import (
    advance_study_session,
    build_context,
    external_source,
    record_claim_evidence,
    record_evidence,
    record_external_source,
    record_study_attempt,
    record_study_review,
    record_study_session,
    record_validation,
    start_study_session,
    study_policy,
    study_session,
    study_sessions,
    transition_study_session,
)
from ..execution_summary import build_execution_summary
from ..knowledge_graph import build_knowledge_graph
from ..memory import memory_store_for_workspace
from ..phs_tool import check_phs, phs_recommendation, run_phs, transpile_phs
from ..rag import build_rag_context
from ..search_index import SearchResult, search
from ..semantic_search import SentenceTransformerProvider, semantic_search
from ..workspace_commands import (
    load_workspace_config,
    validate_workspace,
    workspace_doctor,
    workspace_status,
)


class AcademicWorkspaceKernel:
    """Stable application facade for local academic-workspace capabilities.

    Interfaces should depend on this facade rather than importing Blackboard,
    SQLite, Obsidian, or a particular memory backend directly. Methods return
    versioned dictionaries or domain contracts and do not invoke an LLM.
    """

    def __init__(self, target: Path):
        self.target = Path(target).expanduser().resolve()

    def config(self) -> dict[str, Any]:
        return load_workspace_config(self.target).to_dict()

    def validate_config(self) -> dict[str, Any]:
        return validate_workspace(self.target)

    def status(self) -> dict[str, Any]:
        return workspace_status(self.target)

    def execution_summary(self) -> dict[str, Any]:
        return build_execution_summary(self.target)

    def doctor(self) -> dict[str, Any]:
        return workspace_doctor(self.target)

    def study_context(self):
        return build_context(self.target)

    def study_policy(self) -> dict[str, Any]:
        return study_policy(self.target).to_dict()

    def ai_study_context(self, session: dict[str, Any]) -> dict[str, Any]:
        return build_ai_study_context(self.target, session)

    def start_study_session(self, course: str, topic: str, objective: str, mode: str = "guided", source_refs: tuple[str, ...] = (), planned_minutes: int = 25):
        return start_study_session(self.target, course, topic, objective, mode, source_refs, planned_minutes)

    def study_session(self, session_id: str):
        return study_session(self.target, session_id)

    def study_sessions(self, *, status: str | None = None):
        return study_sessions(self.target, status=status)

    def transition_study_session(self, session_id: str, status: str):
        return transition_study_session(self.target, session_id, status)

    def advance_study_session(self, session_id: str):
        return advance_study_session(self.target, session_id)

    def record_study_session(self, session) -> str:
        return record_study_session(self.target, session)

    def record_study_attempt(self, attempt) -> str:
        return record_study_attempt(self.target, attempt)

    def record_study_review(self, review: dict[str, Any]) -> str:
        return record_study_review(self.target, review)

    def record_evidence(self, evidence: EvidenceRecord) -> str:
        return record_evidence(self.target, evidence)

    def record_external_source(self, source: ExternalSourceRecord) -> str:
        return record_external_source(self.target, source)

    def external_source(self, source_id: str) -> ExternalSourceRecord:
        return external_source(self.target, source_id)

    def record_claim_evidence(self, record: dict[str, Any]) -> str:
        return record_claim_evidence(self.target, record)

    def record_validation(self, validation: ValidationRecord) -> str:
        return record_validation(self.target, validation)

    def memory_events(self) -> list[dict[str, Any]]:
        return memory_store_for_workspace(self.target).events()

    def search(
        self,
        query: str,
        *,
        mode: str = "lexical",
        course: str | None = None,
        lane: str | None = None,
        semantic_model: str | None = None,
        limit: int = 10,
    ) -> tuple[SearchResult, ...]:
        if mode == "lexical":
            return search(self.target, query, course=course, lane=lane, limit=limit)
        if mode == "semantic":
            if not semantic_model:
                raise ValueError("semantic_model es obligatorio para semantic")
            return semantic_search(self.target, query, SentenceTransformerProvider(semantic_model), course=course, lane=lane, limit=limit)
        if mode == "hybrid":
            if not semantic_model:
                raise ValueError("semantic_model es obligatorio para hybrid")
            semantic = semantic_search(self.target, query, SentenceTransformerProvider(semantic_model), course=course, lane=lane, limit=limit)
            lexical = search(self.target, query, course=course, lane=lane, limit=limit)
            merged = {item.path: item for item in semantic}
            merged.update({item.path: item for item in lexical})
            return tuple(sorted(merged.values(), key=lambda item: (0 if item.lane == "official" else 1, -(item.score or 0), item.path)))[:limit]
        raise ValueError("mode debe ser lexical, semantic o hybrid")

    def rag_context(self, query: str, **kwargs: Any) -> dict[str, Any]:
        return build_rag_context(self.target, query, **kwargs)

    def graph_database(self) -> Path:
        return build_knowledge_graph(self.target)

    def results_report(self) -> str:
        return build_results_report(self.target)

    def result_actionables(self) -> tuple[str, ...]:
        return result_attention_lines(self.target)

    def phs_status(self) -> dict[str, Any]:
        return check_phs().to_dict()

    def recommend_phs(self, problem_or_topic: str) -> dict[str, Any]:
        return phs_recommendation(problem_or_topic)

    def run_phs(self, script: str | Path, *, args: tuple[str, ...] = (), timeout: int = 120) -> dict[str, Any]:
        return run_phs(self.target, script, args=args, timeout=timeout)

    def transpile_phs(self, script: str | Path, *, language: str = "python", output: str | Path | None = None, timeout: int = 120) -> dict[str, Any]:
        return transpile_phs(self.target, script, language=language, output=output, timeout=timeout)
