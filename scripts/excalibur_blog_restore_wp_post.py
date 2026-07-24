#!/usr/bin/env python3
"""Restore article.html + minimal meta from existing WP post via FTP bootstrap."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from excalibur_blog_wp_publish import publish_via_ftp  # noqa: E402
from excalibur_env import load_env  # noqa: E402


def project_root() -> Path:
    env_root = load_env(Path(__file__).resolve().parents[1]).get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def fetch_post_html_via_ftp(env: dict[str, str], post_id: int, public_base: str) -> str:
    php = f"""<?php
require_once __DIR__ . '/wp-load.php';
$post = get_post({post_id});
if (!$post) {{ echo 'ERR no post'; exit(1); }}
echo base64_encode($post->post_content);
"""
    out = publish_via_ftp(env, php, public_base)
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("ERR"):
            raise RuntimeError(line)
        if line and not line.startswith("OK") and not line.startswith("permalink="):
            try:
                return base64.b64decode(line).decode("utf-8")
            except Exception:
                continue
    raise RuntimeError(f"Could not parse FTP bootstrap output: {out[:500]!r}")


def clean_html(html: str, site: str) -> str:
    html = html.replace("[REDACTED]", site.rstrip("/"))
    html = re.sub(
        r'\n?<figure class="inline-quad"[^>]*>.*?</figure>\n?',
        "\n",
        html,
        flags=re.I | re.S,
    )
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-id", type=int, required=True)
    ap.add_argument("--article-dir", type=Path, required=True)
    ap.add_argument("--topic-id", default="")
    ap.add_argument("--slug", default="")
    args = ap.parse_args()

    root = project_root()
    env = load_env(root)
    public = env.get("PUBLIC_SITE_URL") or env.get("WP_SITE_URL") or "https://naturallift.store"
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "cover").mkdir(parents=True, exist_ok=True)

    raw = fetch_post_html_via_ftp(env, args.post_id, public)
    if not raw.strip():
        print("ERR: empty post content", file=sys.stderr)
        return 1

    html = clean_html(raw, public)
    (article_dir / "article.html").write_text(html, encoding="utf-8")

    meta_path = article_dir / "article.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    slug = args.slug or meta.get("slug") or article_dir.name.split("-", 1)[-1]
    topic_id = args.topic_id or meta.get("topic_id") or article_dir.name.split("-")[0]
    meta.update(
        {
            "topic_id": topic_id,
            "slug": slug,
            "wp_post_id": args.post_id,
            "post_status": meta.get("post_status") or "draft",
            "cover_scheme_id": meta.get("cover_scheme_id") or "S7_problem_hero",
        }
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK article_dir={article_dir.relative_to(root)} chars={len(html)} post_id={args.post_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
