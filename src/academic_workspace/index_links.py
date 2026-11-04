from __future__ import annotations

from pathlib import Path
import re


def _title(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)


def _child_links(index: Path, vault: Path) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for child in sorted(index.parent.iterdir(), key=lambda p: p.name.casefold()):
        if child.name == "Adjuntos":
            continue
        if child.is_file() and child.suffix.lower() == ".md" and child.name != "index.md":
            target = child
        elif child.is_dir() and (child / "index.md").is_file():
            target = child / "index.md"
        else:
            continue
        vault_path = target.relative_to(vault).with_suffix("").as_posix()
        links.append((vault_path, _title(target)))
    return links


def refresh_index(index: Path, vault: Path) -> bool:
    text = index.read_text(encoding="utf-8", errors="replace")
    links = _child_links(index, vault)
    if not links:
        return False
    section = "\n## Contenido\n" + "".join(f"- [[{path}|{title}]]\n" for path, title in links)
    if "\n## Contenido\n" in text:
        text = re.split(r"\n## Contenido\n", text, maxsplit=1)[0].rstrip() + "\n"
    updated = text.rstrip() + "\n" + section
    if updated == index.read_text(encoding="utf-8"):
        return False
    index.write_text(updated, encoding="utf-8", newline="\n")
    return True


def refresh_indexes(root: Path, *, scope: Path | None = None) -> dict[str, object]:
    root = Path(root)
    scope = Path(scope) if scope is not None else root
    indexes = sorted(scope.rglob("index.md"))
    changed = [index.relative_to(root).as_posix() for index in indexes if refresh_index(index, root)]
    return {"scanned": len(indexes), "changed": len(changed), "paths": changed}
