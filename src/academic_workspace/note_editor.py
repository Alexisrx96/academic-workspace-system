from __future__ import annotations

from pathlib import Path


def save_user_note(target: Path, relative_path: str, content: str) -> Path:
    target = Path(target).resolve()
    path = (target / relative_path).resolve()
    allowed_root = (target / "02 - Cursos").resolve()
    if allowed_root not in path.parents or path.suffix.lower() != ".md":
        raise PermissionError("solo se pueden editar notas Markdown dentro de 02 - Cursos")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return path
