from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.companion_contracts import EvidenceRecord
from academic_workspace.companion_kernel import build_context, record_evidence, start_session
from academic_workspace.source_config import register_source
from academic_workspace.study_plans import complete_plan_step, create_plan, next_plan_step
from academic_workspace.learning_tracks import list_tracks, register_track
from academic_workspace.study_routines import cancel_pomodoro, start_focus, start_pomodoro, status, stop_focus


def main() -> int:
    parser = argparse.ArgumentParser(description="Study Companion Kernel CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    context = sub.add_parser("context")
    context.add_argument("--target", type=Path, required=True)
    session = sub.add_parser("start-session")
    session.add_argument("--target", type=Path, required=True)
    session.add_argument("--course")
    session.add_argument("--topic")
    evidence = sub.add_parser("record-evidence")
    evidence.add_argument("--target", type=Path, required=True)
    evidence.add_argument("--json-file", type=Path, required=True)
    pomodoro_start = sub.add_parser("pomodoro-start")
    pomodoro_start.add_argument("--target", type=Path, required=True)
    pomodoro_start.add_argument("--course", required=True)
    pomodoro_start.add_argument("--topic", required=True)
    pomodoro_start.add_argument("--minutes", type=int, default=25)
    pomodoro_status = sub.add_parser("pomodoro-status")
    pomodoro_status.add_argument("--target", type=Path, required=True)
    pomodoro_cancel = sub.add_parser("pomodoro-cancel")
    pomodoro_cancel.add_argument("--target", type=Path, required=True)
    focus_start = sub.add_parser("focus-start")
    focus_start.add_argument("--target", type=Path, required=True)
    focus_start.add_argument("--course", required=True)
    focus_start.add_argument("--topic", required=True)
    focus_stop = sub.add_parser("focus-stop")
    focus_stop.add_argument("--target", type=Path, required=True)
    plan_create = sub.add_parser("plan-create")
    plan_create.add_argument("--target", type=Path, required=True)
    plan_create.add_argument("--plan-id", required=True)
    plan_create.add_argument("--title", required=True)
    plan_create.add_argument("--course", required=True)
    plan_create.add_argument("--steps-json", type=Path, required=True)
    plan_next = sub.add_parser("plan-next")
    plan_next.add_argument("--target", type=Path, required=True)
    plan_next.add_argument("--plan-id", required=True)
    plan_complete = sub.add_parser("plan-complete")
    plan_complete.add_argument("--target", type=Path, required=True)
    plan_complete.add_argument("--plan-id", required=True)
    plan_complete.add_argument("--step-id", required=True)
    source_register = sub.add_parser("register-source")
    source_register.add_argument("--target", type=Path, required=True)
    source_register.add_argument("--provider", required=True)
    source_register.add_argument("--instance", required=True)
    source_register.add_argument("--root", required=True)
    track_create = sub.add_parser("track-create")
    track_create.add_argument("--target", type=Path, required=True)
    track_create.add_argument("--track-id", required=True)
    track_create.add_argument("--title", required=True)
    track_create.add_argument("--kind", required=True)
    track_create.add_argument("--objectives-json", type=Path, required=True)
    track_create.add_argument("--source-refs-json", type=Path)
    track_list = sub.add_parser("track-list")
    track_list.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "context":
        print(json.dumps(build_context(args.target).to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    elif args.command == "start-session":
        print(json.dumps(start_session(args.target, course=args.course, topic=args.topic).to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    elif args.command == "record-evidence":
        value = json.loads(args.json_file.read_text(encoding="utf-8"))
        evidence = EvidenceRecord(
            course=value["course"],
            topic=value["topic"],
            explanation_score=value.get("explanation_score"),
            application_score=value.get("application_score"),
            application_evidence=value.get("application_evidence", ""),
            boundary_or_doubt=value.get("boundary_or_doubt", ""),
            source_refs=tuple(value.get("source_refs", ())),
        )
        output = {"event_id": record_evidence(args.target, evidence)}
    elif args.command == "pomodoro-start":
        output = start_pomodoro(args.target, course=args.course, topic=args.topic, minutes=args.minutes)
    elif args.command == "pomodoro-status":
        output = status(args.target)
    elif args.command == "pomodoro-cancel":
        output = cancel_pomodoro(args.target)
    elif args.command == "focus-start":
        output = start_focus(args.target, course=args.course, topic=args.topic)
    elif args.command == "focus-stop":
        output = stop_focus(args.target)
    elif args.command == "plan-create":
        output = create_plan(args.target, args.plan_id, args.title, args.course, json.loads(args.steps_json.read_text(encoding="utf-8")))
    elif args.command == "plan-next":
        output = next_plan_step(args.target, args.plan_id)
    elif args.command == "register-source":
        source = register_source(args.target, args.provider, args.instance, args.root)
        output = {"provider": source.provider, "instance": source.instance, "root": source.root}
    elif args.command == "track-create":
        objectives = json.loads(args.objectives_json.read_text(encoding="utf-8"))
        refs = json.loads(args.source_refs_json.read_text(encoding="utf-8")) if args.source_refs_json else []
        output = register_track(args.target, args.track_id, args.title, args.kind, objectives, refs)
    elif args.command == "track-list":
        output = list_tracks(args.target)
    else:
        output = complete_plan_step(args.target, args.plan_id, args.step_id)
    if args.command not in {"context", "start-session"}:
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
