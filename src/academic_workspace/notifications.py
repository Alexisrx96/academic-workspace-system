from __future__ import annotations

from dataclasses import dataclass
import os
import re
import subprocess

from .alerts import AlertCandidate


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    title: str
    body: str
    severity: str


def _plain_text(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[*_`#]", "", value)
    value = value.replace("- [ ]", "").replace("- [x]", "")
    return " ".join(value.split()).strip()


def format_notification(alerts: tuple[AlertCandidate, ...], *, max_items: int = 2) -> NotificationPayload:
    if not alerts:
        raise ValueError("Se requiere al menos una alerta")
    ordered = tuple(alerts)
    severity = "high" if any(alert.severity == "high" for alert in ordered) else "medium" if any(alert.severity == "medium" for alert in ordered) else "low"
    lines = [_plain_text(alert.text) for alert in ordered[:max_items]]
    remaining = len(ordered) - len(lines)
    if remaining:
        lines.append(f"+{remaining} acciones académicas")
    return NotificationPayload("UTEC · Atención académica", "\n".join(lines), severity)


def send_notification(payload: NotificationPayload, backend: str = "auto") -> None:
    selected = backend
    if selected == "auto":
        selected = "windows" if os.name == "nt" else "console"
    if selected == "console":
        print(f"{payload.title}\n{payload.body}")
        return
    if selected != "windows":
        raise ValueError(f"backend de notificación desconocido: {backend}")
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
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell], env=env, check=True, timeout=20, capture_output=True, text=True)
