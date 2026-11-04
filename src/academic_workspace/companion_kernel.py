from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .companion_contracts import (
    EvidenceRecord,
    ExternalSourceRecord,
    StudyAction,
    StudyContext,
    StudySessionPolicy,
    ValidationRecord,
)
from .dashboard_snapshot import build_snapshot
from .memory import MemoryStore, memory_store_for_workspace
from .study_sessions import (
    StudyAttempt,
    StudySession,
    advance_phase,
    create_session,
    transition_session,
)
from .workspace_commands import load_workspace_config

_TERMINAL_SESSION_STATES = {"abandoned", "completed"}


def _prefer_session(candidate: StudySession, current: StudySession | None) -> bool:
    if current is None or candidate.revision > current.revision:
        return True
    if candidate.revision < current.revision:
        return False
    candidate_terminal = candidate.status in _TERMINAL_SESSION_STATES
    current_terminal = current.status in _TERMINAL_SESSION_STATES
    if candidate_terminal != current_terminal:
        return candidate_terminal
    return True


@dataclass(frozen=True, slots=True)
class CompanionPolicy:
    session_minutes: int = 25
    retrieval_before_explanation: bool = True
    require_application: bool = True
    require_boundary_or_doubt: bool = True
    interleaving_when_multiple_topics: bool = True
    adversarial_check: bool = True
    adversarial_minutes: int = 5
    max_actions_in_dashboard: int = 1
    never_invent_deadlines: bool = True
    never_submit_graded_work: bool = True
    mode: str = "guided"
    answer_policy: str = "deferred"
    source_policy: str = "course_first"
    external_lookup: str = "ask_first"
    web_purposes: tuple[str, ...] = ()

    @classmethod
    def load(cls, target: Path) -> CompanionPolicy:
        path = Path(target) / ".study-companion.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(value, dict) or value.get("policy_version") != 1:
            return cls()
        fields = {key: value[key] for key in cls.__dataclass_fields__ if key in value}
        if "web_purposes" in fields:
            fields["web_purposes"] = tuple(fields["web_purposes"] or ())
        try:
            policy = cls(**fields)
            StudySessionPolicy(
                mode=policy.mode,
                answer_policy=policy.answer_policy,
                source_policy=policy.source_policy,
                external_lookup=policy.external_lookup,
                web_purposes=policy.web_purposes,
            )
        except (TypeError, ValueError):
            return cls()
        return policy


def study_policy(target: Path) -> StudySessionPolicy:
    policy = CompanionPolicy.load(target)
    return StudySessionPolicy(
        mode=policy.mode,
        answer_policy=policy.answer_policy,
        source_policy=policy.source_policy,
        external_lookup=policy.external_lookup,
        web_purposes=policy.web_purposes,
    )


def build_context(target: Path) -> StudyContext:
    snapshot = build_snapshot(target)
    return StudyContext(
        priorities=tuple(snapshot["attention"]),
        domain=tuple(snapshot["domain"]),
        reviews=tuple(row for row in snapshot["domain"] if row.get("next_review") not in {None, "", "—"}),
        traceability={"view": "Control Académico/Reporte de trazabilidad.md"},
        source_health=snapshot["health"],
    )


def start_session(target: Path, *, course: str | None = None, topic: str | None = None) -> StudyAction:
    context = build_context(target)
    selected: dict[str, Any] | None = None
    if course and topic:
        selected = {"course": course, "topic": topic}
    else:
        selected = next(iter(context.priorities), None)
        if selected is not None and not selected.get("topic"):
            link = re.search(r"\[([^\]]+)\]", str(selected.get("text", "")))
            selected = {**selected, "topic": link.group(1) if link else selected.get("text", "")}
        if selected is None:
            row = next(iter(context.domain), None)
            if row:
                selected = {"course": row.get("course", ""), "topic": row.get("block", "")}
    if not selected or not selected.get("course") or not selected.get("topic"):
        raise ValueError("no hay una prioridad o tema disponible para iniciar sesión")
    source = selected.get("source", "")
    policy = CompanionPolicy.load(target)
    has_interleaving = policy.interleaving_when_multiple_topics and len(context.domain) >= 2
    adversarial_minutes = policy.adversarial_minutes if policy.adversarial_check else 0
    application_minutes = 5 if policy.require_application else 0
    retrieval_minutes = 3 if policy.retrieval_before_explanation else 0
    fixed = retrieval_minutes + application_minutes + adversarial_minutes
    focused_minutes = max(1, policy.session_minutes - fixed - (4 if has_interleaving else 0))
    plan = []
    if retrieval_minutes:
        plan.append({"phase": "retrieval", "minutes": retrieval_minutes, "instruction": "Explica lo que recuerdas sin consultar la fuente."})
    plan.append({"phase": "focused", "minutes": focused_minutes, "instruction": "Consulta la fuente y corrige solo los vacíos relevantes."})
    if has_interleaving:
        secondary = next((row for row in context.domain if row.get("block") and row.get("block") != selected.get("topic")), None)
        plan.append({"phase": "interleaving", "minutes": 4, "instruction": f"Compara el tema principal con {secondary.get('block') if secondary else 'un segundo tema'} y discrimina cuándo usar cada estrategia."})
    if application_minutes:
        plan.append({"phase": "application", "minutes": application_minutes, "instruction": "Resuelve un caso nuevo y registra la evidencia producida."})
    if adversarial_minutes:
        plan.append({"phase": "adversarial", "minutes": adversarial_minutes, "instruction": "Identifica un supuesto, contrasta la fuente y formula una refutación o límite."})
    return StudyAction(
        action="start_session",
        course=str(selected["course"]),
        topic=str(selected["topic"]),
        duration_minutes=CompanionPolicy.load(target).session_minutes,
        source_refs=(source,) if source else (),
        reason="dashboard_priority",
        parameters={
            "plan": plan,
            "require_application": policy.require_application,
            "require_boundary_or_doubt": policy.require_boundary_or_doubt,
        },
    )


def record_study_session(target: Path, session: StudySession, *, store: MemoryStore | None = None) -> str:
    payload = session.to_dict()
    payload["event_type"] = "study.session.state"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    memory = store or memory_store_for_workspace(Path(target))
    atomic_append = getattr(memory, "append_session_state", None)
    if callable(atomic_append):
        atomic_append(event_id, payload)
        return event_id
    current: StudySession | None = None
    for event in memory.events():
        if event.get("schema") != "study-session.v1" or event.get("session_id") != session.session_id:
            continue
        value = dict(event)
        value.pop("event_id", None)
        value.pop("event_type", None)
        candidate = StudySession.from_dict(value)
        if _prefer_session(candidate, current):
            current = candidate
    if current is not None and session.to_dict() != current.to_dict() and session.revision <= current.revision:
        raise ValueError("transición de sesión obsoleta o conflictiva")
    memory.append_once(event_id, payload)
    return event_id


def study_session(target: Path, session_id: str) -> StudySession:
    found: StudySession | None = None
    for event in memory_store_for_workspace(Path(target)).events():
        if event.get("schema") != "study-session.v1" or event.get("session_id") != session_id:
            continue
        payload = dict(event)
        payload.pop("event_id", None)
        payload.pop("event_type", None)
        candidate = StudySession.from_dict(payload)
        if _prefer_session(candidate, found):
            found = candidate
    if found is None:
        raise ValueError(f"sesión no encontrada: {session_id}")
    return found


def study_sessions(target: Path, *, status: str | None = None) -> tuple[StudySession, ...]:
    """Project the latest state of every persisted session occurrence."""
    projected: dict[str, StudySession] = {}
    for event in memory_store_for_workspace(Path(target)).events():
        if event.get("schema") != "study-session.v1" or not event.get("session_id"):
            continue
        payload = dict(event)
        payload.pop("event_id", None)
        payload.pop("event_type", None)
        session = StudySession.from_dict(payload)
        current = projected.get(session.session_id)
        if _prefer_session(session, current):
            projected[session.session_id] = session
    values = tuple(projected.values())
    if status is not None:
        values = tuple(item for item in values if item.status == status)
    return values


def transition_study_session(target: Path, session_id: str, status: str) -> StudySession:
    current = study_session(target, session_id)
    if status == "completed":
        has_attempt = any(
            event.get("schema") == "study-attempt.v1" and event.get("session_id") == session_id
            for event in memory_store_for_workspace(Path(target)).events()
        )
        if not has_attempt:
            raise ValueError("la sesión requiere al menos un intento del estudiante antes de completarse")
    updated = transition_session(current, status)
    record_study_session(target, updated)
    return updated


def start_study_session(target: Path, course: str, topic: str, objective: str, mode: str, source_refs: tuple[str, ...], planned_minutes: int) -> StudySession:
    session = create_session(course, topic, objective, mode, source_refs, planned_minutes)
    active = transition_session(session, "active")
    record_study_session(target, active)
    return active


def advance_study_session(target: Path, session_id: str) -> StudySession:
    current = study_session(target, session_id)
    updated = advance_phase(current)
    record_study_session(target, updated)
    return updated


def record_study_review(target: Path, review: dict[str, Any], *, store: MemoryStore | None = None) -> str:
    if review.get("schema") != "study-review.v1":
        raise ValueError("schema de study review inválido")
    payload = dict(review)
    payload["event_type"] = "study.review.scheduled"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    (store or memory_store_for_workspace(Path(target))).append_once(event_id, payload)
    return event_id


def record_study_attempt(target: Path, attempt: StudyAttempt, *, store: MemoryStore | None = None) -> str:
    payload = attempt.to_dict()
    payload["event_type"] = "study.attempt.recorded"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    (store or memory_store_for_workspace(Path(target))).append_once(event_id, payload)
    return event_id


def record_evidence(target: Path, evidence: EvidenceRecord, *, store: MemoryStore | None = None) -> str:
    target = Path(target)
    payload = evidence.to_dict()
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    memory = store or memory_store_for_workspace(target)
    memory.append_once(event_id, payload)
    return event_id


def record_external_source(target: Path, source: ExternalSourceRecord, *, store: MemoryStore | None = None) -> str:
    from .source_validation import validate_external_source

    if not load_workspace_config(Path(target)).privacy.allow_external_sources:
        raise PermissionError("la política del workspace no permite fuentes externas")
    validate_external_source(source)
    payload = source.to_dict()
    payload["event_type"] = "external_source.registered"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    (store or memory_store_for_workspace(Path(target))).append_once(event_id, payload)
    return event_id


def external_source(target: Path, source_id: str) -> ExternalSourceRecord:
    for event in memory_store_for_workspace(Path(target)).events():
        if event.get("schema") != "external-source.v1" or event.get("source_id") != source_id:
            continue
        payload = dict(event)
        payload.pop("event_id", None)
        payload.pop("event_type", None)
        payload.pop("schema", None)
        payload["evidence"] = tuple(dict(item) for item in payload.get("evidence", ()))
        return ExternalSourceRecord(**payload)
    raise ValueError(f"fuente externa no encontrada: {source_id}")


def record_claim_evidence(target: Path, record: dict[str, Any], *, store: MemoryStore | None = None) -> str:
    if record.get("schema") != "claim-evidence.v1":
        raise ValueError("schema de claim evidence inválido")
    payload = dict(record)
    payload["event_type"] = "claim.evidence.recorded"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    (store or memory_store_for_workspace(Path(target))).append_once(event_id, payload)
    return event_id


def record_validation(target: Path, validation: ValidationRecord, *, store: MemoryStore | None = None) -> str:
    payload = validation.to_dict()
    payload["event_type"] = "validation.recorded"
    event_id = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    (store or memory_store_for_workspace(Path(target))).append_once(event_id, payload)
    return event_id
