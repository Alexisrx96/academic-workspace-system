from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class StudyContext:
    priorities: tuple[Mapping[str, Any], ...]
    domain: tuple[Mapping[str, Any], ...]
    reviews: tuple[Mapping[str, Any], ...]
    traceability: Mapping[str, Any]
    source_health: Mapping[str, Any]
    available_actions: tuple[str, ...] = (
        "start_session",
        "record_attempt",
        "record_evidence",
        "schedule_review",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-context.v1",
            "source_health": dict(self.source_health),
            "priorities": [dict(item) for item in self.priorities],
            "domain": [dict(item) for item in self.domain],
            "reviews": [dict(item) for item in self.reviews],
            "traceability": dict(self.traceability),
            "available_actions": list(self.available_actions),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StudyContext":
        if value.get("schema") != "study-context.v1":
            raise ValueError("schema de StudyContext inválido")
        return cls(
            priorities=tuple(dict(item) for item in value.get("priorities", ())),
            domain=tuple(dict(item) for item in value.get("domain", ())),
            reviews=tuple(dict(item) for item in value.get("reviews", ())),
            traceability=dict(value.get("traceability") or {}),
            source_health=dict(value.get("source_health") or {}),
            available_actions=tuple(value.get("available_actions", ())),
        )


@dataclass(frozen=True, slots=True)
class StudyEvent:
    event_id: str
    event_type: str
    source_ref: str
    course: str
    occurred_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-event.v1",
            "event_id": self.event_id,
            "type": self.event_type,
            "source_ref": self.source_ref,
            "course": self.course,
            "occurred_at": self.occurred_at,
        }


_ALLOWED_ACTIONS = {"start_session", "record_attempt", "record_evidence", "schedule_review"}


@dataclass(frozen=True, slots=True)
class StudyAction:
    action: str
    course: str
    topic: str
    duration_minutes: int | None
    source_refs: tuple[str, ...]
    reason: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"acción desconocida: {self.action}")
        if not self.course or not self.topic:
            raise ValueError("course y topic son obligatorios")
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("duration_minutes debe ser positivo")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-action.v1",
            "action": self.action,
            "course": self.course,
            "topic": self.topic,
            "duration_minutes": self.duration_minutes,
            "source_refs": list(self.source_refs),
            "reason": self.reason,
            "parameters": dict(self.parameters),
        }


_STUDY_MODES = {"guided", "explicit_validation", "manual_verification", "adversarial_source"}
_ANSWER_POLICIES = {"deferred", "hints", "explicit", "full_procedure"}
_SOURCE_POLICIES = {"course_first", "course_only", "course_plus_personal_notes", "course_plus_authorized_external"}
_EXTERNAL_LOOKUP = {"disabled", "ask_first", "allowed"}
_WEB_PURPOSES = {"find_examples", "find_exercises", "clarify_background", "cross_check", "fact_check", "find_authoritative_source", "find_visual_or_alternative_explanation"}
_VALIDATION_VERDICTS = {"course_consistent", "externally_confirmed", "course_simplification", "course_ambiguous", "course_conflict", "insufficient_evidence"}


@dataclass(frozen=True, slots=True)
class StudySessionPolicy:
    mode: str = "guided"
    answer_policy: str = "deferred"
    source_policy: str = "course_first"
    external_lookup: str = "ask_first"
    web_purposes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in _STUDY_MODES:
            raise ValueError(f"modo de estudio desconocido: {self.mode}")
        if self.answer_policy not in _ANSWER_POLICIES:
            raise ValueError(f"política de respuesta desconocida: {self.answer_policy}")
        if self.source_policy not in _SOURCE_POLICIES:
            raise ValueError(f"política de fuente desconocida: {self.source_policy}")
        if self.external_lookup not in _EXTERNAL_LOOKUP:
            raise ValueError(f"política web desconocida: {self.external_lookup}")
        if any(purpose not in _WEB_PURPOSES for purpose in self.web_purposes):
            raise ValueError("propósito web desconocido")
        if self.external_lookup == "disabled" and self.web_purposes:
            raise ValueError("no se pueden declarar propósitos web con lookup deshabilitado")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "study-session-policy.v1",
            "mode": self.mode,
            "answer_policy": self.answer_policy,
            "source_policy": self.source_policy,
            "external_lookup": self.external_lookup,
            "web_purposes": list(self.web_purposes),
        }


@dataclass(frozen=True, slots=True)
class ExternalSourceRecord:
    source_id: str
    url: str
    title: str
    source_type: str
    publisher: str
    retrieved_at: str
    content_hash: str
    purpose: str
    authorized: bool
    evidence: tuple[Mapping[str, Any], ...] = ()
    snapshot_path: str = ""

    def __post_init__(self) -> None:
        if not self.source_id or not self.url or not self.title:
            raise ValueError("source_id, url y title son obligatorios")
        if self.purpose not in _WEB_PURPOSES:
            raise ValueError(f"propósito web desconocido: {self.purpose}")
        if len(self.content_hash) != 64:
            raise ValueError("content_hash debe ser SHA-256")
        for item in self.evidence:
            if not item.get("quote"):
                raise ValueError("cada evidencia debe tener quote")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "external-source.v1",
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "source_type": self.source_type,
            "publisher": self.publisher,
            "retrieved_at": self.retrieved_at,
            "content_hash": self.content_hash,
            "purpose": self.purpose,
            "authorized": self.authorized,
            "snapshot_path": self.snapshot_path,
            "evidence": [dict(item) for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    course_claim: str
    external_claim: str
    verdict: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    correction: str = ""

    def __post_init__(self) -> None:
        if self.verdict not in _VALIDATION_VERDICTS:
            raise ValueError(f"veredicto desconocido: {self.verdict}")
        if not self.course_claim or not self.external_claim:
            raise ValueError("course_claim y external_claim son obligatorios")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "validation-record.v1",
            "course_claim": self.course_claim,
            "external_claim": self.external_claim,
            "verdict": self.verdict,
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "correction": self.correction,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    course: str
    topic: str
    explanation_score: int | None
    application_score: int | None
    application_evidence: str
    boundary_or_doubt: str
    source_refs: tuple[str, ...]
    recorded_by: str = "student"

    def __post_init__(self) -> None:
        for score in (self.explanation_score, self.application_score):
            if score is not None and score not in range(4):
                raise ValueError("los puntajes deben estar entre 0 y 3")
        if self.recorded_by != "student":
            raise ValueError("la evidencia académica debe registrarse como student")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "evidence-record.v1",
            "course": self.course,
            "topic": self.topic,
            "explanation_score": self.explanation_score,
            "application_score": self.application_score,
            "application_evidence": self.application_evidence,
            "boundary_or_doubt": self.boundary_or_doubt,
            "source_refs": list(self.source_refs),
            "recorded_by": self.recorded_by,
        }
