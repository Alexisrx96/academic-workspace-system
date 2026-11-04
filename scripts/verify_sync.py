from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from academic_workspace.browser_source import BrowserApiCollector
from academic_workspace.live_browser import LiveBrowserTransport
from academic_workspace.verification import validate_local_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida el mapa y la salida determinista de Blackboard Sync")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    with LiveBrowserTransport(args.profile) as transport:
        snapshot = BrowserApiCollector(transport).collect()
    report = validate_local_output(snapshot, args.target)
    output = args.target / "Blackboard"
    sidecars = sorted(path for path in output.rglob("*.pdf.md")) + sorted(path for path in output.rglob("*.docx.md"))
    observed = [attachment for activity in snapshot.activities for attachment in activity.attachments]
    report.update({
        "courses": len(snapshot.courses),
        "elements": len(snapshot.activities),
        "observed_attachments": len(observed),
        "observed_attachment_mime_types": dict(sorted(Counter((item.get("mime_type") or "unknown") for item in observed).items())),
        "pdf_ocr_required": sum("requiere OCR" in path.read_text(encoding="utf-8", errors="replace") for path in sidecars if path.name.lower().endswith(".pdf.md")),
        "unreadable_document_markers": sum("No se pudo extraer" in path.read_text(encoding="utf-8", errors="replace") for path in sidecars),
    })
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    failed = (
        not report["source_map_matches_platform"]
        or report["source_map_contains_browser_url"]
        or report["mapped_notes_missing"]
        or report["mapped_attachments_missing"]
        or report["container_indexes_missing"]
        or report["pdf_or_docx_without_sidecar"]
        or report["document_format_errors"]
        or report["attachments_without_content_note"]
        or report["manifest_hash_mismatches"]
        or report["observed_attachments"] != report["disk_attachments"]
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
