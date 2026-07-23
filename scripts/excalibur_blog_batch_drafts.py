#!/usr/bin/env python3
"""Generate quad images + upload WP drafts for B09-B12 (or --article-dir list)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_DIRS = [
    "memory/blog/articles/B09-massazh-asahi-zogan-sekret-vechnoy-molodosti-yaponskih-zhenschin",
    "memory/blog/articles/B10-ugol-molodosti-kak-vernut-chetkiy-kontur-litsa-za-2-nedeli",
    "memory/blog/articles/B11-teypy-na-noch-kak-prosnutsya-bez-morschin-na-lbu-bez-kosmetologa",
    "memory/blog/articles/B12-meshki-pod-glazami-limfodrenazh-visochnoy-zony-kak-spasenie",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> int:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", action="append", default=[])
    ap.add_argument("--image-url", action="append", default=[], help="canvas URL per article-dir order")
    ap.add_argument("--skip-publish", action="store_true", help="Не публиковать на WP")
    ap.add_argument("--draft", action="store_true", help="WP post_status=draft (иначе live publish)")
    args = ap.parse_args()
    root = project_root()
    dirs = args.article_dir or DEFAULT_DIRS
    urls = args.image_url

    if urls and len(urls) != len(dirs):
        print("ERR: --image-url count must match article dirs", file=sys.stderr)
        return 1

    rc = 0
    for i, rel in enumerate(dirs):
        adir = Path(rel)
        if not adir.is_absolute():
            adir = root / adir
        url = urls[i] if i < len(urls) else ""
        if url:
            if run(
                [
                    sys.executable,
                    str(root / "scripts/excalibur_blog_quad_apply.py"),
                    "--article-dir",
                    str(adir.relative_to(root)),
                    "--url",
                    url,
                    "--inject-html",
                ],
                root,
            ):
                rc = 1
                continue
        if not args.skip_publish:
            pub = [
                sys.executable,
                str(root / "scripts/excalibur_blog_wp_publish.py"),
                "--article-dir",
                str(adir.relative_to(root)),
            ]
            if args.draft:
                pub.append("--draft")
            if run(pub, root):
                rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
