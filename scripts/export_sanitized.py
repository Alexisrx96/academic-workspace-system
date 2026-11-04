from __future__ import annotations

import argparse
from pathlib import Path

from academic_workspace.sanitized_export import export_template


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta una plantilla académica sin datos privados")
    parser.add_argument("--source", type=Path, required=True, help="Workspace personal de origen")
    parser.add_argument("--output", type=Path, required=True, help="Directorio de salida limpio")
    args = parser.parse_args()
    result = export_template(args.source, args.output)
    print(f"OK: {result.file_count} archivos exportados a {result.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
