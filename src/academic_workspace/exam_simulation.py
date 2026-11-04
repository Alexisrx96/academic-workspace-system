from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUESTIONS={'ELE1':['Explica polarización directa e inversa de un diodo.','Resuelve un rectificador de onda completa y justifica qué diodos conducen.','Indica un límite del modelo ideal del diodo.'],'LEMA':['Explica la diferencia entre BYTE, WORD y DWORD.','Corrige un MOV con operandos incompatibles.','Indica una limitación o supuesto de tu solución.'],'SINF':['Distingue dato, información y decisión gerencial.','Aplica un SI a un caso de negocio nuevo.','Indica un riesgo o control necesario.'],'ADCC':['Explica interacción e interdependencia.','Analiza un efecto en cadena de un cambio de TI.','Indica una condición o límite del análisis.']}

def build_exam_simulation(target:Path,course:str,seed:int=1)->dict[str,Any]:
    questions=QUESTIONS.get(course,['Explica un concepto central del curso.','Aplícalo a un caso nuevo.','Indica un límite o duda.'])
    return {'schema':'exam-simulation.v1','course':course,'seed':seed,'questions':[{'id':f'{course}-Q{i+1}','prompt':q,'response':'','score':None} for i,q in enumerate(questions)],'rubric':{'explanation':0,'application':0,'boundary':0},'status':'not_attempted','determinism':{'model_used':False,'question_order':'fixed'}}

def write_exam_simulation(target:Path,course:str)->Path:
    target=Path(target); out=target/f'Proyectos de Estudio/{course} - Parcial 1/Simulaciones/Simulación de parcial.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(build_exam_simulation(target,course),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); return out
