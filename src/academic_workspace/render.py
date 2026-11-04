from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Callable, Mapping, Protocol

from .document_markdown import extract_to_markdown, supports_markdown_extraction
from .attachment_signatures import detect_extension
from .models import Activity, Course, Snapshot, canonical_json


class BinaryDownloader(Protocol):
    def fetch(self, source_url: str) -> bytes: ...


def _previous_managed_files(destination: Path, source_root: str = "Blackboard") -> set[str]:
    manifest_path = destination / ".blackboard-sync" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    result = set()
    for entry in manifest.get("files", ()):
        relative = entry.get("path") if isinstance(entry, dict) else None
        path = Path(relative) if isinstance(relative, str) else None
        if path is None or path.is_absolute() or ".." in path.parts:
            continue
        normalized = path.as_posix()
        source_prefix = source_root.strip("/") + "/"
        if normalized.startswith(source_prefix) or normalized == ".blackboard-sync" or normalized.startswith(".blackboard-sync/"):
            result.add(normalized)
    return result


def _prune_empty_directories(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


@dataclass(frozen=True, slots=True)
class RenderResult:
    changed: bool
    manifest_hash: str
    written: tuple[Path, ...]


def _safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip().rstrip(".")
    value = re.sub(r"\s+", " ", value)
    return value or "sin-titulo"


def _rewrite_attachment_mentions(
    body: str,
    attachments: list[tuple[str, Mapping[str, object], bool]],
) -> str:
    """Replace extracted original filenames with working Obsidian references."""
    image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
    protected = []
    def protect(match):
        protected.append(match.group(0))
        return f"\x00ATTACH{len(protected)-1}\x00"
    body = re.sub(r"!\[\[[^\]]+\]\]", protect, body)
    replacements = []
    for generated_name, item, _has_markdown in attachments:
        original = str(item.get("name") or "").strip()
        if not original:
            continue
        suffix = Path(generated_name).suffix.lower()
        target = f"![[Adjuntos/{generated_name}]]" if suffix in image_suffixes else f"[[Adjuntos/{generated_name}]]"
        replacements.append((original, target))
    for original, target in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        body = re.sub(re.escape(original), target, body)
    body = re.sub(r"https?://utecvirtual\.blackboard\.com/bbcswebdav/[^\s<>\"']+", "", body)
    generic_images = []
    for generated_name, item, _has_markdown in attachments:
        original = str(item.get("name") or "").strip().casefold()
        mime = str(item.get("mime_type") or item.get("_detected_mime") or "").casefold()
        suffix = Path(generated_name).suffix.lower()
        if original in {"adjunto", "attachment"} and (mime.startswith("image/") or suffix in image_suffixes):
            target = f"![[Adjuntos/{generated_name}]]"
            if target not in body:
                generic_images.append(target)
    if generic_images:
        body = body.rstrip() + "\n\n" + " ".join(generic_images)
    for index, embed in enumerate(protected):
        body = body.replace(f"\x00ATTACH{index}\x00", embed)
    seen = set()
    def unique_embed(match):
        value = match.group(0)
        if value in seen:
            return ""
        seen.add(value)
        return value
    body = re.sub(r"!\[\[[^\]]+\]\]", unique_embed, body)
    return body


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    return True


def _frontmatter(values: dict[str, str]) -> str:
    return "---\n" + "".join(f'{key}: {json.dumps(value, ensure_ascii=False)}\n' for key, value in values.items()) + "---\n\n"


def _course_key(course: Course) -> str:
    return _safe_name(course.course_id or course.id)


def _course_note(course: Course, *, source_provider: str = "blackboard_ultra", source_instance: str = "default") -> str:
    fields = {
        "source_provider": source_provider,
        "source_instance": source_instance,
        "source_course_id": course.id,
        "course_code": course.course_id or "",
        "source": "Blackboard Ultra" if source_provider == "blackboard_ultra" else "Academic source",
    }
    if source_provider == "blackboard_ultra":
        fields["blackboard_course_id"] = course.id
    body = _frontmatter(fields) + f"# {course.name}\n"
    if course.description:
        body += f"\n{course.description}\n"
    return body


def _section(activity: Activity) -> str:
    return {"announcement": "Anuncios", "assignment": "Actividades", "feedback": "Retroalimentacion", "content": "Contenido"}.get(activity.kind, "Contenido")


def _activity_directory(course: Course, activity: Activity, *, source_root: str = "Blackboard") -> str:
    parts = [source_root.strip("/"), _course_key(course), _section(activity)]
    if activity.kind in {"content", "assignment"}:
        parts.extend(_safe_name(part) for part in activity.content_path)
    if activity.is_container:
        parts.append(f"{_safe_name(activity.title)}--{_safe_name(activity.id)}")
    return "/".join(parts)


def _attachment_filename(attachment: Mapping[str, object]) -> str:
    name = Path(str(attachment.get("name") or "adjunto"))
    suffix = name.suffix
    stem = name.name[:-len(suffix)] if suffix else name.name
    return f"{_safe_name(stem)}--{_safe_name(str(attachment.get('id') or 'archivo'))}{suffix.lower()}"


def _activity_note_path(course: Course, activity: Activity, *, source_root: str = "Blackboard") -> str:
    filename = "index.md" if activity.is_container else f"{_safe_name(activity.title)}--{_safe_name(activity.id)}.md"
    return f"{_activity_directory(course, activity, source_root=source_root)}/{filename}"


def _activity_note(course: Course, activity: Activity, attachments: list[tuple[str, Mapping[str, object], bool]], *, source_root: str = "Blackboard", source_provider: str = "blackboard_ultra", source_instance: str = "default", child_links: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    note_path = _activity_note_path(course, activity, source_root=source_root)
    fields = {"source_provider": source_provider, "source_instance": source_instance, "source_item_id": activity.id, "source_course_id": course.id, "kind": activity.kind, "due_at": activity.due_at or "", "updated_at": activity.updated_at or "", "source": "Blackboard Ultra" if source_provider == "blackboard_ultra" else "Academic source"}
    if source_provider == "blackboard_ultra": fields["blackboard_id"] = activity.id
    content = _frontmatter(fields) + f"# {activity.title}\n"
    if activity.body:
        content += f"\n{_rewrite_attachment_mentions(activity.body, attachments)}\n"
    if attachments:
        content += "\n## Adjuntos\n"
        for path, item, has_markdown in attachments:
            content += f"- [{item.get('name') or path}](Adjuntos/{path})\n"
            if has_markdown: content += f"  - [Texto extraído](Adjuntos/{path}.md)\n"
    if activity.is_container and child_links:
        content += "\n## Contenido\n"
        for link, title in sorted(child_links, key=lambda item: (item[1].casefold(), item[0])):
            content += f"- [[{link}|{title}]]\n"
    return note_path, content


def _child_links(snapshot: Snapshot, course: Course, activity: Activity, *, source_root: str) -> list[tuple[str, str]]:
    parent = Path(_activity_directory(course, activity, source_root=source_root)); links=[]
    for child in snapshot.activities:
        if child.id == activity.id or child.course_id != activity.course_id: continue
        child_path=Path(_activity_note_path(course,child,source_root=source_root))
        if child_path.parent == parent or (child.is_container and child_path.parent.parent == parent): links.append((child_path.with_suffix("").as_posix(),child.title))
    return links


def refresh_manifest(destination: Path, source_root: str = "Blackboard") -> Path:
    """Rehash the manifest after managed post-render imports such as Canva."""
    destination = Path(destination)
    manifest_path = destination / ".blackboard-sync" / "manifest.json"
    if not manifest_path.is_file():
        return manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = {
        entry["path"]
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    source_path = destination / source_root
    if source_path.is_dir():
        paths.update(
            item.relative_to(destination).as_posix()
            for item in source_path.rglob("*")
            if item.is_file()
        )
    files = []
    for relative in sorted(paths):
        path = destination / relative
        if path.is_file():
            files.append({"path": relative, "sha256": sha256(path.read_bytes()).hexdigest()})
    manifest["files"] = files
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def render_snapshot(snapshot: Snapshot, destination: Path, downloader: BinaryDownloader | None = None, control_files: Mapping[str, str] | None = None, *, source_root: str = "Blackboard", source_provider: str = "blackboard_ultra", source_instance: str = "default", on_progress: Callable[[str, int, int | None, str | None], None] | None = None) -> RenderResult:
    destination=Path(destination); previous_files=_previous_managed_files(destination,source_root); courses={course.id:course for course in snapshot.courses}; text_files={}; binary_files={}
    total_activities = len(snapshot.activities)
    for course in snapshot.courses: text_files[f"{source_root.strip('/')}/{_course_key(course)}/index.md"]=_course_note(course,source_provider=source_provider,source_instance=source_instance)
    for activity_index, activity in enumerate(snapshot.activities, start=1):
        if on_progress is not None:
            on_progress("render", activity_index, total_activities, activity.id)
        course=courses.get(activity.course_id)
        if course is None: continue
        downloaded=[]
        for raw_attachment in activity.attachments:
            attachment=dict(raw_attachment); source_url=attachment.get("source_url")
            if not isinstance(source_url,str) or downloader is None: raise ValueError(f"No hay descargador para el adjunto de Blackboard {activity.id}.")
            filename=_attachment_filename(attachment)
            binary=downloader.fetch(source_url)
            if not Path(filename).suffix:
                detected_extension=detect_extension(binary[:32])
                if detected_extension:
                    filename += detected_extension
            relative=f"{_activity_directory(course,activity,source_root=source_root)}/Adjuntos/{filename}"
            binary_files[relative]=binary
            binary_path=destination/relative
            binary_unchanged=binary_path.is_file() and binary_path.read_bytes()==binary
            creates_markdown=supports_markdown_extraction(Path(filename),str(attachment.get("mime_type") or "") or None)
            if not attachment.get("mime_type"):
                if binary.startswith(b"\x89PNG"):
                    attachment["_detected_mime"] = "image/png"
                elif binary.startswith(b"\xff\xd8\xff"):
                    attachment["_detected_mime"] = "image/jpeg"
            if creates_markdown:
                with TemporaryDirectory() as td:
                    tp=Path(td)/filename; tp.write_bytes(binary); extracted=extract_to_markdown(tp,str(attachment.get("mime_type") or "") or None)
                sidecar_path=destination/(relative+".md")
                if binary_unchanged and "requiere OCR" in extracted and sidecar_path.is_file():
                    existing=sidecar_path.read_text(encoding="utf-8")
                    if "requiere OCR" not in existing: extracted=existing
                text_files[relative+".md"]=extracted
            downloaded.append((filename,attachment,creates_markdown))
        relative,content=_activity_note(course,activity,downloaded,source_root=source_root,source_provider=source_provider,source_instance=source_instance,child_links=_child_links(snapshot,course,activity,source_root=source_root))
        if Path(relative).name.startswith("ultraDocumentBody--_") and not content.strip():
            continue
        text_files[relative]=content
    for path,content in sorted((control_files or {}).items()):
        if path==".blackboard-sync/manifest.json": raise ValueError("El manifiesto está reservado para el renderizador.")
        text_files[path]=content
    manifest_files=[{"path":path,"sha256":sha256(content.encode("utf-8")).hexdigest()} for path,content in sorted(text_files.items())]+[{"path":path,"sha256":sha256(content).hexdigest()} for path,content in sorted(binary_files.items())]
    manifest={"format":2,"snapshot_sha256":sha256(canonical_json(snapshot).encode("utf-8")).hexdigest(),"files":sorted(manifest_files,key=lambda item:item["path"])}; text_files[".blackboard-sync/manifest.json"]=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    written=[]
    for relative,content in sorted(binary_files.items()):
        path=destination/relative
        if _write_bytes_if_changed(path,content): written.append(path)
    for relative,content in sorted(text_files.items()):
        path=destination/relative
        if _write_if_changed(path,content): written.append(path)
    current_files=set(binary_files)|set(text_files)
    for relative in sorted(previous_files-current_files):
        path=destination/relative
        if path.is_file(): path.unlink(); written.append(path)
    _prune_empty_directories(destination/source_root)
    return RenderResult(changed=bool(written),manifest_hash=manifest["snapshot_sha256"],written=tuple(written))
