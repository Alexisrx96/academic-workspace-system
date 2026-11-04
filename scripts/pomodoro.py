from __future__ import annotations

import argparse
from pathlib import Path

from academic_workspace.notifications import NotificationPayload, send_notification
from academic_workspace.study_routines import cancel_pomodoro, notify_pomodoro, pomodoro_notification_text, start_pomodoro, status


def main() -> int:
    parser = argparse.ArgumentParser(description="Control determinista de Pomodoro")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--target", type=Path, required=True)
    start.add_argument("--course", required=True)
    start.add_argument("--topic", required=True)
    start.add_argument("--minutes", type=int, default=25)
    st = sub.add_parser("status")
    st.add_argument("--target", type=Path, required=True)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("--target", type=Path, required=True)
    notify = sub.add_parser("notify")
    notify.add_argument("--target", type=Path, required=True)
    notify.add_argument("--backend", choices=("auto", "windows", "console"), default="auto")
    args = parser.parse_args()
    if args.command == "start":
        result = start_pomodoro(args.target, course=args.course, topic=args.topic, minutes=args.minutes)
    elif args.command == "status":
        result = status(args.target)
    elif args.command == "cancel":
        result = cancel_pomodoro(args.target)
    else:
        event = notify_pomodoro(args.target)
        if event is None:
            return 0
        payload = NotificationPayload("UTEC · Pomodoro", pomodoro_notification_text(event), "medium")
        send_notification(payload, args.backend)
        result = event
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
