from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR determinista de un PDF escaneado a Markdown")
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()

    import easyocr
    import numpy
    import pypdfium2

    reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    pdf = pypdfium2.PdfDocument(args.pdf)
    pages: list[str] = []
    for page_number in range(len(pdf)):
        image = pdf[page_number].render(scale=2.0).to_pil()
        lines = reader.readtext(numpy.array(image), detail=0, paragraph=True)
        text = "\n\n".join(" ".join(line.split()) for line in lines if line.strip())
        pages.append(f"## Página {page_number + 1}\n\n{text or '> No se detectó texto.'}")
    print("# Archivo: " + args.pdf.name + "\n\n" + "\n\n".join(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
