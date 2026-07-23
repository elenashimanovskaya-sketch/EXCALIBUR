#!/usr/bin/env python3
"""Yandex Wordstat via Search API v2 (searchapi.api.cloud.yandex.net).

MCP-KV иногда бьёт в устаревший api.wordstat.yandex.net (SSL fail) — этот клиент
использует актуальный endpoint. Креды те же, что в dashboard MCP-KV → Wordstat API.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_ROOT = "https://searchapi.api.cloud.yandex.net/v2/wordstat"


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def load_credentials(root: Path) -> tuple[str, str]:
    key = os.environ.get("YANDEX_CLOUD_API_KEY", "").strip()
    folder = os.environ.get("YANDEX_CLOUD_FOLDER_ID", "").strip()
    if key and folder:
        return key, folder

    candidates = [
        root / "memory/site.env.local",
        root.parent / "naturallift-site/teya-memory/teya.env.local",
    ]
    for path in candidates:
        env = parse_env_file(path)
        key = key or env.get("YANDEX_CLOUD_API_KEY", "").strip()
        folder = folder or env.get("YANDEX_CLOUD_FOLDER_ID", "").strip()
        if key and folder:
            return key, folder

    return key, folder


def api_post(path: str, body: dict[str, Any], api_key: str) -> dict[str, Any]:
    url = f"{API_ROOT}/{path.lstrip('/')}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Wordstat HTTP {exc.code}: {detail}") from exc


def normalize_devices(devices: list[str] | None) -> list[str]:
    if not devices:
        return ["DEVICE_ALL"]
    mapping = {
        "all": "DEVICE_ALL",
        "desktop": "DEVICE_DESKTOP",
        "mobile": "DEVICE_PHONE",
        "phone": "DEVICE_PHONE",
        "tablet": "DEVICE_TABLET",
    }
    out: list[str] = []
    for d in devices:
        raw = str(d).strip()
        if not raw:
            continue
        up = raw.upper()
        if up.startswith("DEVICE_"):
            out.append(up)
        else:
            out.append(mapping.get(raw.lower(), "DEVICE_ALL"))
    return out or ["DEVICE_ALL"]


def top_requests(
    phrase: str,
    *,
    api_key: str,
    folder_id: str,
    num_phrases: int = 20,
    regions: list[str] | None = None,
    devices: list[str] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "phrase": phrase,
        "numPhrases": num_phrases,
        "folderId": folder_id,
        "devices": normalize_devices(devices),
    }
    if regions:
        body["regions"] = [str(r) for r in regions]
    return api_post("topRequests", body, api_key)


def format_top_table(data: dict[str, Any]) -> str:
    lines = ["| Фраза | Показы/мес |", "|-------|------------|"]
    for row in data.get("results") or []:
        phrase = (row.get("phrase") or row.get("text") or "").strip()
        count = row.get("count") or row.get("value") or "—"
        if phrase:
            lines.append(f"| {phrase} | {count} |")
    assoc = data.get("associations") or []
    if assoc:
        lines.append("")
        lines.append("### Ассоциации")
        lines.append("| Фраза | Показы/мес |")
        lines.append("|-------|------------|")
        for row in assoc:
            phrase = (row.get("phrase") or row.get("text") or "").strip()
            count = row.get("count") or row.get("value") or "—"
            if phrase:
                lines.append(f"| {phrase} | {count} |")
    total = data.get("totalCount")
    if total is not None:
        lines.insert(0, f"**totalCount:** {total}\n")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Wordstat Search API v2 (обход MCP SSL)")
    ap.add_argument("--phrase", required=True)
    ap.add_argument("--num-phrases", type=int, default=20)
    ap.add_argument("--regions", default="225", help="ID через запятую, напр. 225 или 213")
    ap.add_argument("--devices", default="DEVICE_ALL")
    ap.add_argument("--out", type=Path, help="JSON output path")
    ap.add_argument("--markdown", action="store_true", help="Markdown table to stdout")
    args = ap.parse_args()

    root = project_root()
    api_key, folder_id = load_credentials(root)
    if not api_key or not folder_id:
        print(
            "❌ WORDSTAT BLOCKER: задайте YANDEX_CLOUD_API_KEY и YANDEX_CLOUD_FOLDER_ID\n"
            "   (те же значения, что в dashboard MCP-KV → Wordstat API настройки)\n"
            "   в memory/site.env.local или naturallift-site/teya-memory/teya.env.local",
            file=sys.stderr,
        )
        return 1

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    devices = [d.strip() for d in args.devices.split(",") if d.strip()]

    try:
        data = top_requests(
            args.phrase,
            api_key=api_key,
            folder_id=folder_id,
            num_phrases=args.num_phrases,
            regions=regions,
            devices=devices,
        )
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    payload = {
        "source": "yandex_search_api_v2",
        "endpoint": f"{API_ROOT}/topRequests",
        "phrase": args.phrase,
        "regions": regions,
        "devices": normalize_devices(devices),
        "response": data,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK wordstat={args.out}")

    if args.markdown or not args.out:
        print(format_top_table(data))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
