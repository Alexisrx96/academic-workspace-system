from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.external_resources import import_external_resource


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa un recurso externo con procedencia explícita")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True, help="JSON con resource_kind, autor, URL, licencia y curación")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    result = import_external_resource(args.source, args.target, metadata)
    print(json.dumps({"note": result.note.as_posix(), "original": result.original.as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
