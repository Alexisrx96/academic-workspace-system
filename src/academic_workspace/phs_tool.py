from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class PHSStatus:
    installed: bool
    executable: str | None
    version: str | None
    suggestion: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": "phs",
            "name": "PhysureScript",
            "installed": self.installed,
            "executable": self.executable,
            "version": self.version,
            "preferred_for": ["mathematics", "physics"],
            "suggestion": self.suggestion,
        }


_DOMAIN_TERMS = {
    "matemática", "matematicas", "matemáticas", "math", "calculo", "cálculo", "algebra", "álgebra",
    "derivada", "integral", "ecuacion", "ecuación", "vector", "matriz", "probabilidad", "estadística",
    "física", "fisica", "physics", "electricidad", "electrónica", "electronica", "circuito", "circuitos",
    "voltaje", "corriente", "resistencia", "ohm", "cinemática", "cinematica", "dinámica", "dinamica",
    "mecánica", "mecanica", "fuerza", "movimiento", "fluido", "fluidos", "presión", "presion", "sólido",
    "solido", "termodinámica", "termodinamica", "calor", "óptica", "optica", "onda", "ondas", "frecuencia",
    "electromagnetismo", "campo eléctrico", "campo electrico", "energía", "energia", "momento", "trabajo",
}
_ACTION_TERMS = {"calcular", "calcula", "calcule", "resolver", "resuelve", "determin", "hallar", "halla", "obtener", "simular", "simula", "modelar", "derivar", "integra", "integrar", "comprobar", "verificar"}
_QUANTITATIVE_TERMS = {"problema", "ejercicio", "valor", "resultado", "fórmula", "formula", "ecuación", "ecuacion", "medir", "medición", "medicion"}
_NON_PHYSICAL_CONTEXTS = {"programación dinámica", "programacion dinamica", "algoritmo", "algoritmos", "software", "código", "codigo", "computacional", "complejidad", "recursión", "recursion"}


def phs_recommendation(text: str) -> dict[str, Any]:
    normalized = text.casefold()
    matches = tuple(sorted(term for term in _DOMAIN_TERMS if term in normalized))
    actions = tuple(sorted(term for term in _ACTION_TERMS if term in normalized))
    quantitative = tuple(sorted(term for term in _QUANTITATIVE_TERMS if term in normalized))
    exclusions = tuple(sorted(term for term in _NON_PHYSICAL_CONTEXTS if term in normalized))
    probability = 0.05
    probability += min(0.5, 0.16 * len(matches))
    probability += min(0.25, 0.12 * len(actions))
    probability += min(0.15, 0.08 * len(quantitative))
    probability -= min(0.55, 0.28 * len(exclusions))
    if matches and not actions and not quantitative:
        probability -= 0.12
    probability = round(max(0.0, min(0.99, probability)), 2)
    suggested = probability >= 0.55
    return {
        "schema": "phs-recommendation.v1",
        "suggested": suggested,
        "optional": True,
        "probability": probability,
        "engine": "phs",
        "matched_terms": matches,
        "action_terms": actions,
        "quantitative_terms": quantitative,
        "excluded_contexts": exclusions,
        "reason": "Hay alta probabilidad de cálculo matemático/físico verificable." if suggested else "La evidencia contextual no alcanza el umbral para sugerir PHS.",
        "instruction": "Sugiere PHS de forma opcional y úsalo si existe una formulación verificable; separa resultado, explicación y supuestos." if suggested else "No sugieras PHS automáticamente; continúa con la explicación y úsalo solo si el usuario lo pide.",
    }


def _executable() -> str | None:
    return shutil.which("phs") or shutil.which("phs.exe")


def check_phs() -> PHSStatus:
    executable = _executable()
    if not executable:
        return PHSStatus(False, None, None, "Instala PhysureScript (PHS) y asegúrate de que el comando `phs` esté disponible en PATH.")
    try:
        completed = subprocess.run([executable, "--help"], capture_output=True, text=True, timeout=10, check=False)
        output = completed.stdout + "\n" + completed.stderr
    except (OSError, subprocess.SubprocessError):
        return PHSStatus(True, executable, None, "PHS está en PATH, pero no pudo responder a `phs --help`.")
    match = re.search(r"PhysureScript[^\n]*v([0-9][^\s]*)", output)
    return PHSStatus(True, executable, match.group(1) if match else None, None)


def _safe_script(target: Path, script: str | Path) -> Path:
    target = Path(target).resolve()
    path = (target / script).resolve() if not Path(script).is_absolute() else Path(script).resolve()
    if path != target and target not in path.parents:
        raise ValueError("el script PHS debe estar dentro del workspace")
    if not path.is_file() or path.suffix.lower() != ".phs":
        raise ValueError("se requiere un archivo .phs existente")
    return path


def run_phs(target: Path, script: str | Path, *, args: Sequence[str] = (), timeout: int = 120) -> dict[str, Any]:
    status = check_phs()
    if not status.installed or not status.executable:
        raise RuntimeError(status.suggestion or "PHS no está instalado")
    path = _safe_script(target, script)
    completed = subprocess.run([status.executable, str(path), *args], capture_output=True, text=True, timeout=timeout, check=False)
    return {"schema": "phs-execution.v1", "script": path.relative_to(Path(target).resolve()).as_posix(), "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "verified": completed.returncode == 0}


def transpile_phs(target: Path, script: str | Path, *, language: str = "python", output: str | Path | None = None, timeout: int = 120) -> dict[str, Any]:
    status = check_phs()
    if not status.installed or not status.executable:
        raise RuntimeError(status.suggestion or "PHS no está instalado")
    path = _safe_script(target, script)
    command = [status.executable, "transpile", str(path), "--target", language]
    if output:
        output_path = (Path(target) / output).resolve() if not Path(output).is_absolute() else Path(output).resolve()
        if Path(target).resolve() not in output_path.parents:
            raise ValueError("el archivo de salida debe estar dentro del workspace")
        command.extend(["--output", str(output_path)])
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    return {"schema": "phs-transpile.v1", "script": path.relative_to(Path(target).resolve()).as_posix(), "target": language, "output": str(output) if output else None, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "verified": completed.returncode == 0}
