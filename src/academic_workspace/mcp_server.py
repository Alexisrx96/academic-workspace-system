from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import json

from .companion_contracts import EvidenceRecord
from .companion_kernel import build_context, record_evidence, start_session
from .application import AcademicWorkspaceKernel
from .memory import memory_store_for_workspace
from .study_plans import next_plan_step
from .study_routines import cancel_pomodoro, start_focus, start_pomodoro, status, stop_focus
from .search_index import rebuild_search_index, search
from .semantic_search import SentenceTransformerProvider, rebuild_semantic_index, semantic_search
from .rag import build_rag_context as build_rag_context_payload
from .task_control import audit_task, calculate_weekly_quota

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as error:  # pragma: no cover - optional runtime dependency
    FastMCP = None  # type: ignore[assignment]
    _MCP_IMPORT_ERROR = error
else:
    _MCP_IMPORT_ERROR = None


def _target() -> Path:
    value = os.environ.get("ACADEMIC_WORKSPACE")
    if not value:
        raise RuntimeError("ACADEMIC_WORKSPACE no está configurado")
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise RuntimeError(f"ACADEMIC_WORKSPACE no es un directorio: {target}")
    return target


def _kernel() -> AcademicWorkspaceKernel:
    return AcademicWorkspaceKernel(_target())


def _result(result) -> dict[str, Any]:
    return {
        "title": result.title,
        "excerpt": result.excerpt,
        "path": result.path,
        "lane": result.lane,
        "course": result.course,
        "source_url": result.source_url,
    }


def create_server():
    if FastMCP is None:
        raise RuntimeError("Instala el extra MCP para ejecutar el servidor") from _MCP_IMPORT_ERROR
    server = FastMCP(
        name="academic-search",
        instructions="Use source paths and lane labels. Never treat external material as official scope. For mathematics and physics, prefer PHS verification when available.",
    )

    @server.tool(name="search_academic", description="Search official and external academic sources.", structured_output=True)
    def search_academic(query: str, mode: str = "lexical", course: str | None = None, lane: str | None = None, semantic_model: str | None = None) -> dict[str, Any]:
        target = _target()
        if mode == "lexical":
            results = search(target, query, course=course, lane=lane)
        elif mode in {"semantic", "hybrid"}:
            if not semantic_model:
                raise ValueError("semantic_model es obligatorio para semantic/hybrid")
            provider = SentenceTransformerProvider(semantic_model)
            semantic = semantic_search(target, query, provider, course=course, lane=lane)
            if mode == "semantic":
                results = semantic
            else:
                lexical = search(target, query, course=course, lane=lane)
                merged = {item.path: item for item in semantic}
                merged.update({item.path: item for item in lexical})
                results = tuple(sorted(merged.values(), key=lambda item: (0 if item.lane == "official" else 1, item.path)))
        else:
            raise ValueError("mode debe ser lexical, semantic o hybrid")
        return {"mode": mode, "query": query, "results": [_result(item) for item in results]}

    @server.tool(name="build_rag_context", description="Build bounded, citable local context without invoking a model.", structured_output=True)
    def build_rag_context_tool(
        query: str,
        mode: str = "lexical",
        course: str | None = None,
        lane: str | None = None,
        semantic_model: str | None = None,
        max_chunks: int = 8,
        max_chars: int = 6000,
    ) -> dict[str, Any]:
        return build_rag_context_payload(
            _target(), query, mode=mode, course=course, lane=lane,
            semantic_model=semantic_model, max_chunks=max_chunks, max_chars=max_chars,
        )

    @server.tool(name="audit_academic_task", description="Audit an academic task against its deterministic rubric.", structured_output=True)
    def audit_academic_task(task_path: str) -> dict[str, Any]:
        target = _target()
        return audit_task(target / task_path, target)

    @server.tool(name="get_weekly_study_quota", description="Return the configured weekly study quota and progress.", structured_output=True)
    def get_weekly_study_quota() -> dict[str, Any]:
        target = _target()
        path = target / "Control Académico" / "cuota-semanal.json"
        return calculate_weekly_quota(json.loads(path.read_text(encoding="utf-8")))

    @server.tool(name="rebuild_search_index", description="Rebuild the local lexical or semantic index.", structured_output=True)
    def rebuild_search_index_tool(mode: str = "lexical", semantic_model: str | None = None) -> dict[str, Any]:
        target = _target()
        lexical_db = rebuild_search_index(target)
        result: dict[str, Any] = {"lexical_database": lexical_db.as_posix(), "mode": mode}
        if mode in {"semantic", "hybrid"}:
            if not semantic_model:
                raise ValueError("semantic_model es obligatorio para semantic/hybrid")
            result["semantic_database"] = rebuild_semantic_index(target, SentenceTransformerProvider(semantic_model)).as_posix()
        return result

    @server.tool(name="get_search_status", description="Return local index and source status.", structured_output=True)
    def get_search_status() -> dict[str, Any]:
        target = _target()
        return {
            "workspace": target.as_posix(),
            "lexical_index": (target / ".blackboard-sync" / "search.sqlite3").is_file(),
            "semantic_index": (target / ".blackboard-sync" / "semantic-search.sqlite3").is_file(),
            "external_lane": (target / "Recursos Externos").is_dir(),
        }

    @server.tool(name="check_math_physics_engine", description="Check whether PhysureScript (PHS) is installed for mathematics and physics verification.", structured_output=True)
    def check_math_physics_engine() -> dict[str, Any]:
        return _kernel().phs_status()

    @server.tool(name="recommend_phs_for_problem", description="Suggest PHS optionally when a problem involves mathematics, calculus, or physics.", structured_output=True)
    def recommend_phs_for_problem(problem_or_topic: str) -> dict[str, Any]:
        return _kernel().recommend_phs(problem_or_topic)

    @server.tool(name="run_phs_script", description="Run a workspace-local .phs script for deterministic mathematics or physics verification.", structured_output=True)
    def run_phs_script(script: str) -> dict[str, Any]:
        return _kernel().run_phs(script)

    @server.resource("academic://study-context", name="study-context", description="Current versioned StudyContext.", mime_type="application/json")
    def study_context_resource() -> str:
        return json.dumps(build_context(_target()).to_dict(), ensure_ascii=False, sort_keys=True, indent=2)

    @server.resource("academic://evidence", name="study-evidence", description="Recorded student evidence.", mime_type="application/json")
    def evidence_resource() -> str:
        events = memory_store_for_workspace(_target()).events()
        return json.dumps({"schema": "evidence-collection.v1", "events": events}, ensure_ascii=False, sort_keys=True, indent=2)

    @server.tool(name="get_study_context", description="Return the versioned StudyContext for the companion.", structured_output=True)
    def get_study_context() -> dict[str, Any]:
        return build_context(_target()).to_dict()

    @server.tool(name="start_study_session", description="Create a deterministic study-session action.", structured_output=True)
    def start_study_session(course: str | None = None, topic: str | None = None) -> dict[str, Any]:
        return start_session(_target(), course=course, topic=topic).to_dict()

    @server.tool(name="record_study_evidence", description="Record student evidence idempotently.", structured_output=True)
    def record_study_evidence(
        course: str,
        topic: str,
        explanation_score: int | None = None,
        application_score: int | None = None,
        application_evidence: str = "",
        boundary_or_doubt: str = "",
        source_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        evidence = EvidenceRecord(
            course=course,
            topic=topic,
            explanation_score=explanation_score,
            application_score=application_score,
            application_evidence=application_evidence,
            boundary_or_doubt=boundary_or_doubt,
            source_refs=tuple(source_refs or ()),
        )
        return {"event_id": record_evidence(_target(), evidence)}

    @server.tool(name="start_pomodoro", description="Start an explicit cancelable Pomodoro session.", structured_output=True)
    def start_pomodoro_tool(course: str, topic: str, minutes: int = 25) -> dict[str, Any]:
        return start_pomodoro(_target(), course=course, topic=topic, minutes=minutes)

    @server.tool(name="get_pomodoro_status", description="Return the current Pomodoro status.", structured_output=True)
    def get_pomodoro_status() -> dict[str, Any]:
        return status(_target())

    @server.tool(name="cancel_pomodoro", description="Cancel the active Pomodoro session.", structured_output=True)
    def cancel_pomodoro_tool() -> dict[str, Any]:
        return cancel_pomodoro(_target())

    @server.tool(name="start_focus_mode", description="Start a single-topic focus mode.", structured_output=True)
    def start_focus_mode(course: str, topic: str, source_refs: list[str] | None = None) -> dict[str, Any]:
        return start_focus(_target(), course=course, topic=topic, source_refs=tuple(source_refs or ()))

    @server.tool(name="stop_focus_mode", description="Stop the active focus mode.", structured_output=True)
    def stop_focus_mode() -> dict[str, Any]:
        return stop_focus(_target())

    @server.tool(name="get_next_plan_step", description="Return the next deterministic step of a study plan.", structured_output=True)
    def get_next_plan_step(plan_id: str) -> dict[str, Any]:
        return next_plan_step(_target(), plan_id)

    return server
