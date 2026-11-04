from __future__ import annotations

import re
from pathlib import Path
from typing import Any

def _val(value:str)->str:
    return '' if value in {'—','-',''} else value

def build_evidence_queue(target: Path, limit:int=12)->dict[str,Any]:
    target=Path(target); rows=[]
    path=target/'Control Académico/Matriz de dominio.md'
    if path.exists():
        for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
            if not line.startswith('|') or 'Curso |' in line or set(line.replace('|','').replace('-','').replace(':','').strip())==set(): continue
            cells=[x.strip() for x in line.strip('|').split('|')]
            if len(cells)<8: continue
            course,block,explanation,application,doubt,next_action,review,source=cells[:8]
            missing=[]
            if _val(explanation)=='': missing.append('explicación sin apuntes')
            if _val(application)=='': missing.append('aplicación a caso nuevo')
            if _val(doubt)=='': missing.append('límite o duda')
            score=sum(_val(x)!='' for x in (explanation,application,doubt))
            priority=3-score
            rows.append({'course':course,'block':block,'evidence_score':score,'missing':missing,'next_action':next_action if _val(next_action) else ('Registrar '+missing[0] if missing else 'Programar repaso'),'source':source,'priority':priority})
    rows.sort(key=lambda r:(-r['priority'],r['course'],r['block']))
    return {'schema':'evidence-study-queue.v1','items':rows[:limit],'total_candidates':len(rows),'determinism':{'model_used':False,'ordering':'missing_evidence_count_then_course_then_block'}}

def write_evidence_queue(target:Path)->Path:
    target=Path(target); data=build_evidence_queue(target); out=target/'Control Académico/Cola de estudio basada en evidencia.json'; out.write_text(__import__('json').dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); return out
