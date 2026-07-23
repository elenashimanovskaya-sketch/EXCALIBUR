#!/usr/bin/env python3
"""Загрузка env: memory/site.env.local + Cursor Cloud Secrets (os.environ)."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# Production gate: только naturallift.store (не mayai.ru / чужие WP).
ALLOWED_PUBLISH_HOSTS = ("naturallift.store",)

ENV_KEYS = (
    "PUBLIC_SITE_URL",
    "WP_SITE_URL",
    "WP_ADMIN_URL",
    "WP_HOME",
    "EXCALIBUR_BLOG_ALLOW_PUBLISH",
    "EXCALIBUR_PROJECT_ROOT",
    "FTP_HOST",
    "FTP_PORT",
    "FTP_USER",
    "FTP_PASS",
    "FTP_PASSWORD",
    "FTP_ROOT",
    "FTP_PATH",
    "NATURALLIFT_TELEGRAM_URL",
    "NATURALLIFT_TELEGRAM_CHANNEL_TITLE",
    "YANDEX_CLOUD_API_KEY",
    "YANDEX_CLOUD_FOLDER_ID",
    "GEMINI_API_KEY",
    "EXCALIBUR_GEMINI_MODEL",
)


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def load_env(root: Path) -> dict[str, str]:
    """Файл site.env.local, затем переопределение из os.environ (Cloud Secrets)."""
    env: dict[str, str] = {}
    for name in ("memory/site.env.local", "memory/site.env.local.example"):
        env.update(parse_env_file(root / name))

    for key in ENV_KEYS:
        val = os.environ.get(key, "").strip()
        if val:
            env[key] = val

    # Алиас: doctor/доки иногда пишут FTP_PASSWORD, publish ждёт FTP_PASS
    if not env.get("FTP_PASS") and env.get("FTP_PASSWORD"):
        env["FTP_PASS"] = env["FTP_PASSWORD"]

    return env


def assert_naturallift_publish_target(public_url: str) -> None:
    host = (urlparse(public_url).netloc or "").lower().removeprefix("www.")
    if not host or not any(host == h or host.endswith("." + h) for h in ALLOWED_PUBLISH_HOSTS):
        raise RuntimeError(
            f"BLOCKER: publish target host={host!r} — разрешён только naturallift.store. "
            "Проверь PUBLIC_SITE_URL / FTP_* в Cloud Secrets (не mayai.ru)."
        )
