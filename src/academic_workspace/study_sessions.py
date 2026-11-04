from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .companion_contracts import StudySessionPolicy

_PHASES = ("preflight", "diagnostic", "retrieval", "source_review", "practice", "validation", "evidence", "review_scheduling")
_STATUSES = {"planned", "active", "paused", "blocked", "completed", "abandoned"}
_ALLOWED_TRANSITIONS = {
    "planned": {"active", "abandoned"},
    "active": {"paused", "completed", "blocked", "abandoned"},
    "paused": {"active", "abandoned"},
    "blocked": {"active", "abandoned"},
    "completed": set(),
    "abandoned": set(),
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class StudySession:
    session_id: str
    course: str
    topic: str
    objective: str
    mode: str
    answer_policy: str
    source_policy: str
    external_lookup: str
    source_refs: tuple[str, ...]
    planned_minutes: int
    phases: tuple[str, ...] = _PHASES
    current_phase: str = "preflight"
    status: str = "planned"
    created_at: str = ""
    updated_at: str = ""
    ended_at: str | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        if not self.course or not self.topic or not self.objective:
            raise ValueError("course, topic y objective son obligatorios")
        if self.planned_minutes <= 0:
            raise ValueError("planned_minutes debe ser positivo")
        StudySessionPolicy(self.mode, self.answer_policy, self.source_policy, self.external_lookup)
        if self.status not in _STATUSES:
            raise ValueError(f"estado de sesión desconocido: {self.status}")
        if self.current_phase not in self.phases:
            raise ValueError("fase actual no pertenece a la sesión")
        if self.revision < 0:
            raise ValueError("revision no puede ser negativa")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-session.v1",
            "session_id": self.session_id,
            "course": self.course,
            "topic": self.topic,
            "objective": self.objective,
            "mode": self.mode,
            "answer_policy": self.answer_policy,
            "source_policy": self.source_policy,
            "external_lookup": self.external_lookup,
            "source_refs": list(self.source_refs),
            "planned_minutes": self.planned_minutes,
            "phases": list(self.phases),
            "current_phase": self.current_phase,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ended_at": self.ended_at,
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StudySession:
        if value.get("schema") != "study-session.v1":
            raise ValueError("schema de StudySession inválido")
        payload = dict(value)
        payload.pop("schema", None)
        payload["source_refs"] = tuple(payload.get("source_refs", ()))
        payload["phases"] = tuple(payload.get("phases", _PHASES))
        return cls(**payload)


def create_session(course: str, topic: str, objective: str, mode: str, source_refs: tuple[str, ...], planned_minutes: int) -> StudySession:
    policy = StudySessionPolicy(mode=mode, answer_policy="explicit" if mode in {"explicit_validation", "manual_verification"} else "deferred", source_policy="course_first", external_lookup="ask_first")
    timestamp = _now()
    return StudySession(
        session_id="session:" + uuid4().hex,
        course=course,
        topic=topic,
        objective=objective,
        mode=policy.mode,
        answer_policy=policy.answer_policy,
        source_policy=policy.source_policy,
        external_lookup=policy.external_lookup,
        source_refs=tuple(source_refs),
        planned_minutes=planned_minutes,
        created_at=timestamp,
        updated_at=timestamp,
    )



@dataclass(frozen=True, slots=True)
class StudyAttempt:
    attempt_id: str
    session_id: str
    phase: str
    response: str
    feedback: str
    result: str
    error_tags: tuple[str, ...] = ()
    confidence: int | None = None
    help_level: int = 0
    occurred_at: str = ""

    @property
    def calibration(self) -> str:
        if self.confidence is None:
            return "insufficient_data"
        correct = self.result in {"verified", "externally_confirmed"}
        if correct and self.confidence >= 2 or not correct and self.confidence <= 1:
            return "well_calibrated"
        if correct:
            return "underconfident"
        return "overconfident"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-attempt.v1",
            "attempt_id": self.attempt_id,
            "session_id": self.session_id,
            "phase": self.phase,
            "response": self.response,
            "feedback": self.feedback,
            "result": self.result,
            "error_tags": list(self.error_tags),
            "confidence": self.confidence,
            "help_level": self.help_level,
            "calibration": self.calibration,
            "occurred_at": self.occurred_at,
        }


def advance_phase(session: StudySession) -> StudySession:
    if session.status != "active":
        raise ValueError("la sesión debe estar activa para avanzar de fase")
    index = session.phases.index(session.current_phase)
    if index >= len(session.phases) - 1:
        return session
    return replace(
        session,
        current_phase=session.phases[index + 1],
        updated_at=_now(),
        revision=session.revision + 1,
    )


def create_attempt(session: StudySession, phase: str, response: str, feedback: str, result: str, error_tags: tuple[str, ...] = (), *, confidence: int | None = None, help_level: int = 0) -> StudyAttempt:
    if session.status != "active":
        raise ValueError("la sesión debe estar activa para registrar un intento")
    if phase not in session.phases:
        raise ValueError("la fase del intento no pertenece a la sesión")
    if phase != session.current_phase:
        raise ValueError("la fase del intento debe coincidir con la fase actual")
    if confidence is not None and confidence not in range(4):
        raise ValueError("confidence debe estar entre 0 y 3")
    if help_level not in range(6):
        raise ValueError("help_level debe estar entre 0 y 5")
    return StudyAttempt(
        attempt_id="attempt:" + uuid4().hex,
        session_id=session.session_id,
        phase=phase,
        response=response,
        feedback=feedback,
        result=result,
        error_tags=tuple(error_tags),
        confidence=confidence,
        help_level=help_level,
        occurred_at=_now(),
    )


def transition_session(session: StudySession, status: str) -> StudySession:
    if status not in _STATUSES:
        raise ValueError(f"estado de sesión desconocido: {status}")
    if status not in _ALLOWED_TRANSITIONS[session.status]:
        raise ValueError(f"transición inválida: {session.status} → {status}")
    phase = session.current_phase
    if status == "completed":
        phase = session.phases[-1]
    timestamp = _now()
    return replace(
        session,
        status=status,
        current_phase=phase,
        updated_at=timestamp,
        ended_at=timestamp if status in {"completed", "abandoned"} else None,
        revision=session.revision + 1,
    )
