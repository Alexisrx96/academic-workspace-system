from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.providers.platzi import PlatziProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza un export local de Platzi al contrato académico neutral")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--instance", default="default")
    args = parser.parse_args()
    snapshot = PlatziProvider(args.source, instance=args.instance).collect_snapshot()
    print(json.dumps({
        "schema": "platzi-snapshot.v1",
        "provider": snapshot.provider,
        "instance": snapshot.instance,
        "courses": [{"id": item.identity.external_id, "code": item.code, "name": item.name, "metadata": dict(item.metadata)} for item in snapshot.courses],
        "items": [{"id": item.identity.external_id, "course": item.course.external_id, "kind": item.kind, "title": item.title, "metadata": dict(item.metadata)} for item in snapshot.items],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
