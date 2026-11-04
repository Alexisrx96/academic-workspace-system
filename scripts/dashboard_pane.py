from __future__ import annotations
import argparse,json
from pathlib import Path
from academic_workspace.dashboard_pane import write_dashboard_pane
p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);a=p.parse_args();path=write_dashboard_pane(a.target);print(json.dumps({'pane':str(path)},ensure_ascii=False));raise SystemExit(0)
