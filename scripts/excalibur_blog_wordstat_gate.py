#!/usr/bin/env python3
"""Wordstat editorial gate — частотность primary_query и title/h1 перед writer/publish."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from excalibur_blog_topics import parse_topic_card


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm_phrase(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def phrase_shows(data: dict[str, Any]) -> int | None:
    """totalCount или сумма top results из ответа Search API v2."""
    if not data:
        return None
    total = data.get("totalCount")
    if isinstance(total, int):
        return total
    results = data.get("results") or []
    if results:
        counts = [int(r.get("count") or r.get("value") or 0) for r in results]
        if counts:
            return max(counts)
    return None


def collect_phrase_table(wordstat_doc: dict[str, Any]) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for run in wordstat_doc.get("runs") or []:
        resp = run.get("response") or {}
        for row in resp.get("results") or []:
            p = norm_phrase(str(row.get("phrase") or row.get("text") or ""))
            c = int(row.get("count") or row.get("value") or 0)
            if p and c:
                rows.append((p, c))
        for row in resp.get("associations") or []:
            p = norm_phrase(str(row.get("phrase") or row.get("text") or ""))
            c = int(row.get("count") or row.get("value") or 0)
            if p and c:
                rows.append((p, c))
        q = norm_phrase(str(run.get("phrase") or ""))
        tc = phrase_shows(resp)
        if q and tc:
            rows.append((q, tc))
    # dedupe keep max count
    best: dict[str, int] = {}
    for p, c in rows:
        best[p] = max(best.get(p, 0), c)
    return sorted(best.items(), key=lambda x: -x[1])


def lookup_shows(wordstat_doc: dict[str, Any], phrase: str) -> int | None:
    phrase = norm_phrase(phrase)
    if not phrase:
        return None
    for run in wordstat_doc.get("runs") or []:
        if norm_phrase(str(run.get("phrase") or "")) == phrase:
            val = phrase_shows(run.get("response") or {})
            if val is not None:
                return val
    for p, c in collect_phrase_table(wordstat_doc):
        if p == phrase:
            return c
    return None


def title_hook(h1: str) -> str:
    """Часть до двоеточия — то, что видит Дзен в ленте."""
    h1 = (h1 or "").strip()
    if ":" in h1:
        return h1.split(":", 1)[0].strip()
    if "?" in h1:
        return h1.split("?", 1)[0].strip() + "?"
    return h1


def fetch_wordstat_for_topic(topic: dict[str, str], out_dir: Path, region: str = "225") -> Path:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from excalibur_blog_research_start import fetch_wordstat_for_topic as _fetch

    path, _, err = _fetch(topic, out_dir, region=region)
    if err and not path:
        raise RuntimeError(err)
    if err:
        print(f"WARN wordstat fetch: {err}", file=sys.stderr)
    if not path or not path.is_file():
        raise RuntimeError("wordstat fetch failed")
    return path


def append_wordstat_phrase(article_dir: Path, phrase: str, region: str = "225") -> None:
    """Добавить в research-wordstat.json проверку title hook (если ещё нет)."""
    phrase = norm_phrase(phrase)
    if not phrase:
        return
    ws_path = article_dir / "research-wordstat.json"
    doc: dict[str, Any] = load_json(ws_path) if ws_path.is_file() else {"runs": [], "errors": []}
    for run in doc.get("runs") or []:
        if norm_phrase(str(run.get("phrase") or "")) == phrase:
            return

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from excalibur_wordstat import load_credentials, top_requests

    api_key, folder_id = load_credentials(project_root())
    if not api_key or not folder_id:
        return
    try:
        data = top_requests(
            phrase,
            api_key=api_key,
            folder_id=folder_id,
            num_phrases=20,
            regions=[region],
        )
        doc.setdefault("runs", []).append({"phrase": phrase, "ok": True, "response": data})
    except RuntimeError as exc:
        doc.setdefault("runs", []).append({"phrase": phrase, "ok": False, "error": str(exc)})
        doc.setdefault("errors", []).append(f"{phrase}: {exc}")
    ws_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gate_article(
    article_dir: Path,
    policy: dict[str, Any],
    *,
    fetch_missing: bool = False,
) -> dict[str, Any]:
    root = project_root()
    meta_path = article_dir / "article.meta.json"
    ws_path = article_dir / "research-wordstat.json"
    errors: list[str] = []
    warnings: list[str] = []

    rules = policy.get("wordstat_gate") or {}
    min_primary_block = int(rules.get("min_primary_shows_block") or 200)
    min_primary_warn = int(rules.get("min_primary_shows_warn") or 500)
    min_title_block = int(rules.get("min_title_hook_shows_block") or 200)
    require_json = bool(rules.get("require_research_wordstat_json", True))

    meta = load_json(meta_path) if meta_path.is_file() else {}
    primary = norm_phrase(meta.get("primary_query") or meta.get("focus_keyword") or "")
    h1 = meta.get("h1") or meta.get("title") or ""
    hook = title_hook(h1)

    topic_id = meta.get("topic_id") or article_dir.name.split("-")[0]
    topics_path = root / "memory/topics/blog-topics.md"
    try:
        topic = parse_topic_card(topics_path, topic_id)
    except ValueError:
        topic = {"topic_id": topic_id, "primary_query": primary}

    if not ws_path.is_file():
        if fetch_missing:
            try:
                fetch_wordstat_for_topic(topic, article_dir)
            except RuntimeError as exc:
                errors.append(f"нет research-wordstat.json и fetch failed: {exc}")
        elif require_json:
            errors.append(
                "нет research-wordstat.json — запусти: "
                f"python scripts/excalibur_blog_research_start.py --topic-id {topic_id}"
            )

    if fetch_missing and hook and ws_path.is_file():
        append_wordstat_phrase(article_dir, hook)

    wordstat_doc: dict[str, Any] = {}
    if ws_path.is_file():
        wordstat_doc = load_json(ws_path)

    table = collect_phrase_table(wordstat_doc)
    approved_title = table[0][0] if table else ""
    approved_shows = table[0][1] if table else 0

    primary_shows = lookup_shows(wordstat_doc, primary) if primary else None
    hook_shows = lookup_shows(wordstat_doc, hook) if hook else None

    if primary_shows is None and primary:
        warnings.append(f"primary_query «{primary}» не найден в wordstat runs — добавь в research-wordstat")
    elif primary_shows is not None:
        if primary_shows < min_primary_block:
            errors.append(
                f"primary_query «{primary}» = {primary_shows}/мес < {min_primary_block} (BLOCK)"
            )
        elif primary_shows < min_primary_warn:
            warnings.append(
                f"primary_query «{primary}» = {primary_shows}/мес — ниже целевых {min_primary_warn}+ для Дзена"
            )

    if hook and hook.lower() != primary:
        if hook_shows is None:
            warnings.append(f"title hook «{hook}» — нет данных Wordstat; проверь вручную")
        elif hook_shows < min_title_block:
            errors.append(
                f"title hook «{hook}» = {hook_shows}/мес < {min_title_block}. "
                f"Дзен-title с низким спросом (пример B20). "
                f"Лучше: «{approved_title}» ({approved_shows}/мес)"
            )

    if approved_title and approved_shows >= min_primary_warn:
        if approved_title not in norm_phrase(h1) and approved_title not in norm_phrase(primary):
            warnings.append(
                f"title/h1 не содержит топ-фразу Wordstat «{approved_title}» ({approved_shows}/мес)"
            )

    status = "PASS" if not errors else "BLOCK"
    report = {
        "gate": "wordstat",
        "topic_id": topic_id,
        "article_dir": str(article_dir),
        "status": status,
        "primary_query": primary,
        "primary_shows": primary_shows,
        "title_hook": hook,
        "title_hook_shows": hook_shows,
        "approved_title_phrase": approved_title,
        "approved_title_shows": approved_shows,
        "top_phrases": [{"phrase": p, "shows": c} for p, c in table[:10]],
        "errors": errors,
        "warnings": warnings,
    }
    out = article_dir / "wordstat-gate.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Wordstat gate for Excalibur BLOG")
    ap.add_argument("--article-dir", type=Path, required=True)
    ap.add_argument("--policy", default="memory/brief/editorial-policy.json")
    ap.add_argument("--fetch", action="store_true", help="Скачать Wordstat если json нет")
    args = ap.parse_args()

    root = project_root()
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    policy = load_json(policy_path)

    report = gate_article(article_dir, policy, fetch_missing=args.fetch)
    print(f"wordstat {report.get('topic_id')}: {report['status']}")
    print(f"  primary={report.get('primary_query')!r} shows={report.get('primary_shows')}")
    print(f"  hook={report.get('title_hook')!r} shows={report.get('title_hook_shows')}")
    if report.get("approved_title_phrase"):
        print(
            f"  approved_top={report['approved_title_phrase']!r} "
            f"shows={report.get('approved_title_shows')}"
        )
    for err in report.get("errors") or []:
        print(f"  ERROR: {err}")
    for warn in report.get("warnings") or []:
        print(f"  WARN: {warn}")

    if report["status"] != "PASS":
        print("❌ WORDSTAT GATE BLOCKER", file=sys.stderr)
        return 1
    print("OK WORDSTAT GATE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
