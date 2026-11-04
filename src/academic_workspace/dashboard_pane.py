from __future__ import annotations

import json
from pathlib import Path
from .dashboard_snapshot import build_snapshot
from .evidence_queue import build_evidence_queue


def write_dashboard_pane(target: Path) -> Path:
    target = Path(target)
    payload = json.dumps({'snapshot': build_snapshot(target), 'queue': build_evidence_queue(target)}, ensure_ascii=False).replace('</', '<\\/')
    page = '''<!doctype html><meta charset="utf-8"><title>Dashboard académico</title><style>
:root{--fg:var(--foreground,#e5e7eb);--muted:var(--muted-foreground,#9ca3af);--accent:var(--accent,#22c55e);--border:var(--border,#374151);--card:var(--card,#111827)}body{font:14px system-ui;color:var(--fg);margin:0;padding:12px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.card{border:1px solid var(--border);background:var(--card);padding:10px;border-radius:8px}h1,h2{margin:0 0 8px}small,.muted{color:var(--muted)}ul{padding-left:18px}li{margin:6px 0}.pill{color:var(--accent)}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<h1>Dashboard académico</h1><div id="app"></div><script>const d=__DATA__;const q=d.queue.items;const s=d.snapshot;document.getElementById('app').innerHTML=`<div class="grid"><div class="card"><small>Salud</small><h2 class="pill">${s.health.sync_status}</h2><span class="muted">Última sincronización: ${s.health.last_blackboard_sync||'no registrada'}</span></div><div class="card"><small>Atención</small><h2>${s.attention.length}</h2><span class="muted">acciones pendientes</span></div><div class="card"><small>Evidencia</small><h2>${d.queue.total_candidates}</h2><span class="muted">bloques con evidencia incompleta</span></div></div><div class="card" style="margin-top:8px"><h2>Siguiente cola de estudio</h2><ul>${q.slice(0,8).map(x=>`<li><b>${x.course}</b> — ${x.block}<br><span class="muted">Falta: ${x.missing.join(', ')||'repaso'}</span></li>`).join('')}</ul></div>`</script>'''.replace('__DATA__', payload)
    out = target / 'Control Académico/Dashboard académico.html'
    out.write_text(page, encoding='utf-8', newline='\n')
    return out
