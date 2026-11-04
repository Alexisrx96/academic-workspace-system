from __future__ import annotations
import argparse,json
from pathlib import Path
from academic_workspace.evidence_queue import write_evidence_queue
p=argparse.ArgumentParser();p.add_argument('--target',type=Path,required=True);a=p.parse_args();path=write_evidence_queue(a.target);print(json.dumps({'queue':str(path)},ensure_ascii=False));raise SystemExit(0)
