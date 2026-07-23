#!/usr/bin/env python3
"""Preflight для Cursor Cloud: окружение, папки, env vars (без вывода секретов)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from excalibur_env import assert_naturallift_publish_target, load_env

REQUIRED_DIRS = (
    "agents",
    ".cursor/agents",
    "scripts",
    "shared",
    "memory",
    "memory/topics",
)

REQUIRED_FILES = (
    "AGENTS.md",
    "CLOUD-AUTOMATION.md",
    "shared/published-articles.md",
    "memory/topics/blog-topics.md",
)

OPTIONAL_ENV = (
    "PUBLIC_SITE_URL",
    "WP_SITE_URL",
    "EXCALIBUR_BLOG_ALLOW_PUBLISH",
    "EXCALIBUR_TOPIC_ID",
    "FTP_HOST",
    "FTP_USER",
    "FTP_PASSWORD",
    "YANDEX_CLOUD_FOLDER_ID",
    "YANDEX_CLOUD_OAUTH_TOKEN",
)


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = project_root()
    errors = 0
    warnings = 0

    print(f"OK python {sys.version.split()[0]}")
    print(f"OK project_root={root}")

    for rel in REQUIRED_DIRS:
        path = root / rel
        if path.is_dir():
            print(f"OK dir {rel}")
        else:
            print(f"ERR missing dir {rel}", file=sys.stderr)
            errors += 1

    for rel in REQUIRED_FILES:
        path = root / rel
        if path.is_file():
            print(f"OK file {rel}")
        else:
            print(f"ERR missing file {rel}", file=sys.stderr)
            errors += 1

    env = load_env(root)
    for key in OPTIONAL_ENV:
        val = env.get(key, "").strip()
        if val:
            print(f"OK env {key}=configured")
        else:
            print(f"WARN env {key} not set")
            warnings += 1

    allow = env.get("EXCALIBUR_BLOG_ALLOW_PUBLISH", "").strip().lower()
    if allow == "yes":
        print("OK publish_mode=production")
    elif allow == "no":
        print("WARN publish_mode=dry-run (EXCALIBUR_BLOG_ALLOW_PUBLISH=no)")
        warnings += 1
    else:
        print("WARN publish_mode=unset (set EXCALIBUR_BLOG_ALLOW_PUBLISH=yes for live)")
        warnings += 1

    public = env.get("PUBLIC_SITE_URL") or env.get("WP_SITE_URL") or ""
    if public:
        try:
            assert_naturallift_publish_target(public)
            print("OK publish_target=naturallift.store")
        except RuntimeError as exc:
            print(f"ERR {exc}", file=sys.stderr)
            errors += 1
    else:
        print("ERR PUBLIC_SITE_URL not set (нужен https://naturallift.store)", file=sys.stderr)
        errors += 1

    print(f"SUMMARY errors={errors} warnings={warnings}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
