#!/usr/bin/env python3
"""Upload B33 HTML to WP post 706 via MCP blob flow using stdin/stdout JSON lines.

Agent usage:
  python3 scripts/b33_mcp_full_blob_publish.py step0 > /tmp/blob-step0-result.txt

Each step prints JSON with next_action for the agent to CallMcpTool.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ARTICLE = Path("/workspace/memory/blog/articles/B33-sahar-noe-starenie-kozhi-5-neochevidnyh-posledstviy")
HTML = (ARTICLE / "mcp-publish-content-relative.html").read_text(encoding="utf-8")
SCHEMA = (ARTICLE / "schema.jsonld").read_text(encoding="utf-8")
FULL = HTML + f'\n<script type="application/ld+json">\n{SCHEMA}\n</script>\n'
META = json.loads((ARTICLE / "article.meta.json").read_text(encoding="utf-8"))
CHUNK = 5000
PARTS = [FULL[i : i + CHUNK] for i in range(0, len(FULL), CHUNK)]


def main() -> int:
    step = sys.argv[1] if len(sys.argv) > 1 else "plan"
    state_path = Path("/tmp/b33-blob-state.json")
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    if step == "plan":
        print(json.dumps({
            "parts": len(PARTS),
            "total_chars": len(FULL),
            "post_id": 706,
            "featured_media": 703,
            "steps": [f"append_{i}" for i in range(len(PARTS))] + ["update_from_blob"],
        }, ensure_ascii=False, indent=2))
        return 0

    if step.startswith("append_"):
        i = int(step.split("_")[1])
        payload = {"chunk": PARTS[i], "finalize": i == len(PARTS) - 1}
        if i == 0:
            payload["reset"] = True
        else:
            payload["blob_id"] = state.get("blob_id")
        print(json.dumps({
            "mcp_tool": "wordpress_content_blob_append",
            "arguments": payload,
        }, ensure_ascii=False))
        return 0

    if step == "save_blob":
        blob_id = sys.argv[2]
        state["blob_id"] = blob_id
        state_path.write_text(json.dumps(state), encoding="utf-8")
        print(json.dumps({"saved": blob_id}))
        return 0

    if step == "update":
        print(json.dumps({
            "mcp_tool": "wordpress_update_post_from_blob",
            "arguments": {
                "post_id": 706,
                "blob_id": state.get("blob_id"),
                "title": META["title"],
                "status": "draft",
                "excerpt": META["description"],
                "featured_media": 703,
            },
        }, ensure_ascii=False))
        return 0

    print("unknown step", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
