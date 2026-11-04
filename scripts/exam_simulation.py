from __future__ import annotations
import argparse,json
from pathlib import Path
from academic_workspace.exam_simulation import write_exam_simulation
p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);p.add_argument('--course',required=True);a=p.parse_args();path=write_exam_simulation(a.target,a.course);print(json.dumps({'simulation':str(path)},ensure_ascii=False));raise SystemExit(0)
