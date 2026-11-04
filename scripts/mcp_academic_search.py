from __future__ import annotations

import argparse
import os

from academic_workspace.mcp_server import create_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Academic Search MCP server over stdio")
    parser.add_argument("--target", required=True, help="Workspace académico")
    args = parser.parse_args()
    os.environ["ACADEMIC_WORKSPACE"] = args.target
    create_server().run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
