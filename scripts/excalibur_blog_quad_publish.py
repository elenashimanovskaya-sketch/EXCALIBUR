#!/usr/bin/env python3
"""Quad manifest + apply + WordPress publish (production default: publish live).

После готовности article.html + article.meta.json и URL canvas от MCP gpt-image-2:
  python scripts/excalibur_blog_quad_publish.py \\
    --article-dir memory/blog/articles/B25-... \\
    --canvas-url https://...

Без --canvas-url читает cover/quad-mcp-result.json.

Политика (2026-07-21): публикуем сразу, без ожидания команды пользователя.
Skip только с --no-publish или --draft.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> int:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def rel(root: Path, adir: Path) -> str:
    try:
        return str(adir.relative_to(root))
    except ValueError:
        return str(adir)


def ensure_meta_publish(article_dir: Path) -> None:
    meta_path = article_dir / "article.meta.json"
    if not meta_path.is_file():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("post_status") == "draft":
        meta["post_status"] = "publish"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK {meta_path.name} post_status=publish (auto)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Quad apply + WP publish (default: live publish)")
    ap.add_argument("--article-dir", required=True)
    ap.add_argument(
        "--canvas-url",
        default="",
        help="MCP gpt-image-2 result URL; иначе cover/quad-mcp-result.json",
    )
    ap.add_argument("--skip-manifest", action="store_true", help="Не пересоздавать quad-manifest/batch")
    ap.add_argument("--no-publish", action="store_true", help="Только quad apply, без WP")
    ap.add_argument("--draft", action="store_true", help="WP post_status=draft")
    ap.add_argument("--dry-run", action="store_true", help="Только manifest/batch + dry-run publish")
    args = ap.parse_args()

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir
    if not article_dir.is_dir():
        print(f"ERR: missing {article_dir}", file=sys.stderr)
        return 1

    adir_rel = rel(root, article_dir)
    rc = 0

    if not args.skip_manifest:
        for script in ("excalibur_blog_quad_manifest.py", "excalibur_blog_cover_quad_prompt.py"):
            if run(
                [sys.executable, str(root / "scripts" / script), "--article-dir", adir_rel, *(
                    ["--write-batch"] if script.endswith("cover_quad_prompt.py") else []
                )],
                root,
            ):
                return 1

    canvas_url = args.canvas_url.strip()
    if not canvas_url:
        result_path = article_dir / "cover" / "quad-mcp-result.json"
        if result_path.is_file():
            canvas_url = (json.loads(result_path.read_text(encoding="utf-8")).get("url") or "").strip()
    if not canvas_url:
        batch_path = article_dir / "cover" / "quad-mcp-batch.json"
        print(
            "BLOCKER: нужен --canvas-url или cover/quad-mcp-result.json "
            "(сначала ONE MCP gpt-image-2 по quad-mcp-batch.json)",
            file=sys.stderr,
        )
        if batch_path.is_file():
            print(f"  batch: {batch_path}", file=sys.stderr)
        return 2

    apply_cmd = [
        sys.executable,
        str(root / "scripts/excalibur_blog_quad_apply.py"),
        "--article-dir",
        adir_rel,
        "--url",
        canvas_url,
        "--inject-html",
    ]
    if run(apply_cmd, root):
        return 1

    if args.no_publish:
        print("OK quad apply (publish skipped: --no-publish)")
        return 0

    if not args.draft:
        ensure_meta_publish(article_dir)

    pub_cmd = [
        sys.executable,
        str(root / "scripts/excalibur_blog_wp_publish.py"),
        "--article-dir",
        adir_rel,
    ]
    if args.draft:
        pub_cmd.append("--draft")
    if args.dry_run:
        pub_cmd.append("--dry-run")

    if run(pub_cmd, root):
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
