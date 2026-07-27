#!/usr/bin/env python3
"""Emit MCP wordpress_content_blob_append arguments as JSON (stdout)."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: mcp_blob_upload_from_json.py <chunk_index> [blob_id]", file=sys.stderr)
        return 2
    i = int(sys.argv[1])
    path = Path(f"/tmp/mcp-blob-{i}.json")
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if len(sys.argv) >= 3:
        data["blob_id"] = sys.argv[2]
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
