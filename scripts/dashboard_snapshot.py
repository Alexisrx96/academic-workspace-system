from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.dashboard_snapshot import build_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un snapshot académico estable para Hermes")
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_snapshot(args.target), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
