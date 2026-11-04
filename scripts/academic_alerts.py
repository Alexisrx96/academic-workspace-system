from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from academic_workspace.academic_alerts import build_candidates
from academic_workspace.alerts import collect_new_alerts
from academic_workspace.notifications import NotificationPayload, format_notification


def _notify_windows(payload: NotificationPayload) -> None:
    if os.name != "nt":
        raise RuntimeError("Las notificaciones Windows solo están disponibles en Windows")
    env = os.environ.copy()
    env["UTEC_ALERT_TITLE"] = payload.title
    env["UTEC_ALERT_TEXT"] = payload.body[:1800]
    powershell = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$icon = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon = [System.Drawing.SystemIcons]::Information
$icon.BalloonTipTitle = $env:UTEC_ALERT_TITLE
$icon.BalloonTipText = $env:UTEC_ALERT_TEXT
$icon.Visible = $true
$icon.ShowBalloonTip(8000)
Start-Sleep -Seconds 9
$icon.Dispose()
'''
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell],
        env=env,
        check=True,
        timeout=20,
        capture_output=True,
        text=True,
    )


def _notify_console(payload: NotificationPayload) -> None:
    print(f"{payload.title}\n{payload.body}")


def _notify(alerts, backend: str) -> None:
    payload = format_notification(tuple(alerts))
    selected = backend
    if selected == "auto":
        selected = "windows" if os.name == "nt" else "console"
    if selected == "windows":
        _notify_windows(payload)
    elif selected == "console":
        _notify_console(payload)
    else:
        raise RuntimeError(f"Backend de notificación desconocido: {backend}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emite alertas académicas nuevas sin repetirlas")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--notify", action="store_true", help="Muestra una notificación")
    parser.add_argument("--notify-backend", choices=("auto", "windows", "console"), default="auto")
    parser.add_argument("--json", action="store_true", help="Imprime JSON incluso cuando no hay alertas")
    parser.add_argument("--stale-after-hours", type=int, default=48)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    candidates = build_candidates(args.target, now=now, stale_after_hours=args.stale_after_hours)
    fresh = collect_new_alerts(args.target, candidates, now=now)
    if args.notify and fresh:
        try:
            _notify(fresh, args.notify_backend)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"No se pudo mostrar la notificación: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps({
            "alerts": [
                {"key": alert.key, "text": alert.text, "severity": alert.severity}
                for alert in fresh
            ],
        }, ensure_ascii=False, sort_keys=True))
    elif fresh:
        for alert in fresh:
            print(f"[{alert.severity.upper()}] {alert.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
