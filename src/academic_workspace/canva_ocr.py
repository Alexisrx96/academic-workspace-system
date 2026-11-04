from __future__ import annotations

from pathlib import Path
import re
from functools import lru_cache
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def _ocr_engine() -> Any:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise RuntimeError("Instala el extra ocr para extraer texto de diapositivas.") from error
    return RapidOCR()


def extract_slide_text(path: Path, *, confidence_threshold: float = 0.45) -> tuple[str, ...]:
    """Extract OCR lines deterministically with RapidOCR/ONNX Runtime."""
    result, _ = _ocr_engine()(str(path))
    if not result:
        return ()
    entries: list[tuple[float, float, str]] = []
    for item in result:
        if len(item) < 3:
            continue
        box, text, confidence = item[0], str(item[1]), float(item[2])
        if confidence < confidence_threshold or not _clean(text):
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        entries.append((min(ys), min(xs), _clean(text)))
    return tuple(text for _y, _x, text in sorted(entries, key=lambda item: (round(item[0] / 8), item[1], item[2].casefold())))


def write_slide_sidecar(image: Path, *, number: int, lines: tuple[str, ...], relative_image: str) -> Path:
    sidecar = image.with_suffix(".md")
    body = "\n".join(lines) if lines else "> No se detectó texto con el umbral OCR configurado."
    content = (
        "---\n"
        'resource_kind: "presentation-slide"\n'
        'ocr_backend: "rapidocr-onnxruntime"\n'
        f"slide_number: {number}\n"
        f"source_image: {relative_image!r}\n"
        "---\n\n"
        f"# Diapositiva {number}\n\n"
        f"![[{relative_image}]]\n\n"
        "## Texto OCR\n\n"
        f"{body}\n"
    )
    sidecar.write_text(content, encoding="utf-8", newline="\n")
    return sidecar
