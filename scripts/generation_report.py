from __future__ import annotations
import argparse,json
from pathlib import Path
from academic_workspace.generation_report import write_generation_report
p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);a=p.parse_args(); path=write_generation_report(a.target); print(json.dumps({'report':str(path)},ensure_ascii=False)); raise SystemExit(0)
