from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "calculo"


def formalize_phs(
    target: Path,
    *,
    course: str,
    topic: str,
    script_text: str,
    source_ref: str,
    approved: bool,
) -> dict[str, object]:
    relative = Path("02 - Cursos") / course / "Cálculos" / "validaciones" / f"{_slug(topic)}.phs"
    script = (
        f"// generated_by: academic-workspace\n"
        f"// course: {course}\n"
        f"// topic: {topic}\n"
        f"// source_ref: {source_ref}\n"
        f"// transformation_approved: {str(approved).lower()}\n\n"
        f"{script_text.rstrip()}\n"
    )
    payload = {
        "schema": "phs-formalization.v1",
        "status": "created" if approved else "awaiting_approval",
        "course": course,
        "topic": topic,
        "source_ref": source_ref,
        "script_path": relative.as_posix(),
        "script_sha256": sha256(script.encode("utf-8")).hexdigest(),
        "approval_required": True,
    }
    if not approved:
        payload["script_preview"] = script
        return payload
    destination = Path(target) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(script, encoding="utf-8", newline="\n")
    metadata = destination.with_suffix(".input.json")
    metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return payload
