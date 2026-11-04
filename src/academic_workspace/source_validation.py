from __future__ import annotations

from hashlib import sha256
import json
from typing import Any
from urllib.parse import urldefrag, urlsplit, urlunsplit

from .companion_contracts import ExternalSourceRecord

_RELATIONSHIPS = {"consistent", "simplification", "ambiguous", "conflict"}
_VERDICTS = {
    "consistent": "externally_confirmed",
    "simplification": "course_simplification",
    "ambiguous": "course_ambiguous",
    "conflict": "course_conflict",
}


def _canonical_url(url: str) -> str:
    parts = urlsplit(urldefrag(url)[0])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def stable_source_id(url: str, content_hash: str) -> str:
    value = f"{_canonical_url(url)}\n{content_hash}"
    return "external-source:" + sha256(value.encode("utf-8")).hexdigest()


def validate_external_source(source: ExternalSourceRecord) -> None:
    if not source.authorized:
        raise ValueError("la fuente externa no está autorizada para esta sesión")
    for evidence in source.evidence:
        quote = str(evidence.get("quote") or "")
        text = str(evidence.get("text") or "")
        if not quote or not text or quote not in text:
            raise ValueError("la cita externa no aparece literalmente en el texto suministrado")


def build_claim_evidence(
    claim: str,
    source: ExternalSourceRecord,
    quote: str,
    verdict: str,
    session_id: str = "",
) -> dict[str, Any]:
    if not claim or not source.snapshot_path:
        raise ValueError("claim y snapshot_path son obligatorios para la cadena de evidencia")
    validate_external_source(source)
    matching = next((item for item in source.evidence if item.get("quote") == quote), None)
    if matching is None:
        raise ValueError("la cita no está registrada en la fuente externa")
    payload = {
        "claim": claim,
        "source_id": source.source_id,
        "source_url": source.url,
        "snapshot_path": source.snapshot_path,
        "quote": quote,
        "verdict": verdict,
        "session_id": session_id,
    }
    claim_id = "claim:" + sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {"schema": "claim-evidence.v1", "claim_id": claim_id, **payload}


def classify_validation(
    course_claim: str,
    external_claim: str,
    *,
    relationship: str | None = None,
    external_evidence: bool = False,
) -> dict[str, Any]:
    if not external_evidence:
        verdict = "insufficient_evidence"
    elif relationship is not None:
        if relationship not in _RELATIONSHIPS:
            raise ValueError(f"relación desconocida: {relationship}")
        verdict = _VERDICTS[relationship]
    elif " ".join(course_claim.casefold().split()) == " ".join(external_claim.casefold().split()):
        verdict = "externally_confirmed"
    else:
        verdict = "insufficient_evidence"
    return {
        "schema": "validation-assessment.v1",
        "course_claim": course_claim,
        "external_claim": external_claim,
        "verdict": verdict,
        "course_claim_preserved": True,
    }
