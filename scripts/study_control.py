from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from academic_workspace.exam_checkpoint import build_exam_checkpoint
from academic_workspace.knowledge_bridge import refresh_knowledge_bridge
from academic_workspace.reading_refinement import build_refined_readings
from academic_workspace.study_control import refresh_control


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera control semanal, calendario local y recordatorios desde Blackboard sincronizado")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7, help="Horizonte de fechas de entrega; por defecto 7")
    parser.add_argument("--sync-status", choices=("verified", "unavailable", "unverified"), help="Estado de la última sincronización Blackboard")
    args = parser.parse_args()
    result = refresh_control(args.target, now=datetime.now(timezone.utc), days=args.days, sync_status=args.sync_status)
    bridge = refresh_knowledge_bridge(args.target)
    checkpoint = build_exam_checkpoint(args.target)
    refined_readings = build_refined_readings(args.target)
    print(json.dumps({
        "baseline_created": result.baseline_created,
        "pending_next_days": len(result.pending),
        "new_publications": len(result.new_publications),
        "report": result.report_path.as_posix(),
        "calendar": result.calendar_path.as_posix(),
        "knowledge_map": bridge.map_path.as_posix(),
        "linked_courses": bridge.course_count,
        "exam_checkpoint": checkpoint.panel_path.as_posix(),
        "checkpoint_courses": checkpoint.course_count,
        "refined_readings": refined_readings.reading_count,
        "refinement_indexes": [path.as_posix() for path in refined_readings.index_paths],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
