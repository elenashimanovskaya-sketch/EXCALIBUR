#!/usr/bin/env python3
"""Excalibur BLOG — step 0: today date context + fresh web search for a topic.

Outputs research-context.json and research-serp.json for the agent to write research-notes.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from excalibur_repo_paths import repo_relative
from excalibur_blog_topics import parse_topic_card

USER_AGENT = "ExcaliburBlogResearch/1.0 (+research-start)"
DDG_HTML = "https://html.duckduckgo.com/html/"
DEFAULT_TZ = "Europe/Moscow"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_context(tz_name: str) -> dict[str, Any]:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"

    now = datetime.now(tz)
    month_names = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апril",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }
    # fix typo april
    month_names[4] = "апрель"

    freshness_start = (now - timedelta(days=90)).date().isoformat()
    return {
        "timezone": tz_name,
        "today_iso": now.date().isoformat(),
        "today_ru": now.strftime("%d.%m.%Y"),
        "year": now.year,
        "month": now.month,
        "month_name_ru": month_names.get(now.month, str(now.month)),
        "weekday_ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][
            now.weekday()
        ],
        "freshness_window": {
            "prefer_sources_after": freshness_start,
            "note": "Предпочитай источники не старше ~90 дней; версии продуктов — актуальные на today_iso.",
        },
        "research_disclaimer": (
            f"Все даты, версии и статистика в статье должны быть проверены на {now.date().isoformat()} "
            f"({now.year} год)."
        ),
    }


def build_search_queries(topic: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, str]]:
    year = str(ctx["year"])
    month = ctx["month_name_ru"]
    primary = topic.get("primary_query") or topic.get("h1") or topic["topic_id"]

    queries: list[dict[str, str]] = [
        {"id": "primary_fresh", "query": f"{primary} {year}", "purpose": "актуальный SERP по главному запросу"},
        {"id": "primary_recent", "query": f"{primary} {month} {year}", "purpose": "свежее за текущий месяц"},
        {"id": "news_angle", "query": f"{primary} новости {year}", "purpose": "новости и обновления"},
    ]

    for idx, sec in enumerate(topic.get("secondary_queries") or [], start=1):
        queries.append(
            {
                "id": f"secondary_{idx}",
                "query": f"{sec} {year}",
                "purpose": f"вторичный запрос: {sec}",
            }
        )

    if topic.get("h1") and topic["h1"] != primary:
        queries.append(
            {
                "id": "h1_fresh",
                "query": f"{topic['h1']} {year}",
                "purpose": "SERP по H1",
            }
        )

    return queries


class DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result_link = False
        self._in_snippet = False
        self._current_href = ""
        self._current_title = ""
        self._current_snippet = ""
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = attr.get("class") or ""
        if tag == "a" and "result__a" in classes:
            self._in_result_link = True
            self._current_href = attr.get("href") or ""
            self._capture_title = True
            self._current_title = ""
        elif tag == "a" and "result__snippet" in classes:
            self._in_snippet = True
            self._capture_snippet = True
            self._current_snippet = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result_link:
            self._in_result_link = False
            self._capture_title = False
            if self._current_href and self._current_title:
                self.results.append(
                    {
                        "title": self._current_title.strip(),
                        "url": self._unwrap_ddg_url(self._current_href),
                        "snippet": self._current_snippet.strip(),
                    }
                )
            self._current_href = ""
            self._current_title = ""
            self._current_snippet = ""
        if tag == "a" and self._in_snippet:
            self._in_snippet = False
            self._capture_snippet = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._current_title += data
        if self._capture_snippet:
            self._current_snippet += data

    @staticmethod
    def _unwrap_ddg_url(href: str) -> str:
        if href.startswith("//"):
            href = "https:" + href
        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                return urllib.parse.unquote(qs["uddg"][0])
        return href


def search_web(query: str, *, max_results: int = 8, retries: int = 3) -> list[dict[str, str]]:
    body = urllib.parse.urlencode({"q": query, "kl": "ru-ru"}).encode("utf-8")
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(DDG_HTML, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as response:
                html = response.read().decode("utf-8", errors="replace")
            parser = DuckDuckGoResultParser()
            parser.feed(html)
            deduped: list[dict[str, str]] = []
            seen: set[str] = set()
            for item in parser.results:
                url = item.get("url") or ""
                if not url.startswith("http") or url in seen:
                    continue
                seen.add(url)
                deduped.append(item)
                if len(deduped) >= max_results:
                    break
            return deduped
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(min(2.0, 0.4 * attempt))

    raise RuntimeError(f"search failed for {query!r}: {last_error}")


def article_dir(root: Path, topic: dict[str, Any]) -> Path:
    slug = topic.get("slug") or topic["topic_id"].lower()
    return root / "memory" / "blog" / "articles" / f"{topic['topic_id']}-{slug}"


def run_research_start(
    *,
    topic_id: str,
    topics_path: Path,
    output_dir: Path | None,
    tz_name: str,
    max_results: int,
    dry_run: bool,
    wordstat: bool = False,
    wordstat_region: str = "225",
) -> dict[str, Any]:
    ctx = now_context(tz_name)
    topic = parse_topic_card(topics_path, topic_id)

    # Utility-only topic gate (before SERP spend)
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from excalibur_blog_utility_gate import gate_topic, load_json as load_policy_json

    policy_path = project_root() / "memory" / "brief" / "editorial-policy.json"
    policy = load_policy_json(policy_path)
    utility_report = gate_topic(topic, policy)
    if utility_report["status"] != "PASS":
        raise ValueError(
            "UTILITY TOPIC BLOCKER: "
            + "; ".join(utility_report.get("errors") or ["topic failed utility gate"])
        )

    queries = build_search_queries(topic, ctx)
    out_dir = output_dir or article_dir(project_root(), topic)
    out_dir.mkdir(parents=True, exist_ok=True)

    serp_runs: list[dict[str, Any]] = []
    errors: list[str] = []

    if not dry_run:
        for item in queries:
            try:
                results = search_web(item["query"], max_results=max_results)
                serp_runs.append(
                    {
                        "query_id": item["id"],
                        "query": item["query"],
                        "purpose": item["purpose"],
                        "result_count": len(results),
                        "results": results,
                        "searched_at": ctx["today_iso"],
                    }
                )
                time.sleep(0.8)
            except RuntimeError as exc:
                errors.append(str(exc))
                serp_runs.append(
                    {
                        "query_id": item["id"],
                        "query": item["query"],
                        "purpose": item["purpose"],
                        "result_count": 0,
                        "results": [],
                        "error": str(exc),
                        "searched_at": ctx["today_iso"],
                    }
                )

    payload_context = {
        "agent": "excalibur-blog",
        "step": "research_start",
        "date_context": ctx,
        "topic": topic,
        "utility_gate": utility_report,
        "search_queries": queries,
        "output_dir": repo_relative(out_dir, project_root()),
        "next_step": "Прочитай research-serp.json, дополни web research, напиши research-notes.md",
    }

    payload_serp = {
        "agent": "excalibur-blog",
        "date_context": ctx,
        "topic": topic,
        "searches": serp_runs,
        "errors": errors,
        "unique_urls": _unique_urls(serp_runs),
    }

    context_path = out_dir / "research-context.json"
    serp_path = out_dir / "research-serp.json"

    if not dry_run:
        context_path.write_text(json.dumps(payload_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        serp_path.write_text(json.dumps(payload_serp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_utility = out_dir / "utility-gate-topic.json"
        save_utility.write_text(json.dumps(utility_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    wordstat_path: Path | None = None
    wordstat_payload: dict[str, Any] | None = None
    wordstat_error: str | None = None

    if wordstat and not dry_run:
        wordstat_path, wordstat_payload, wordstat_error = fetch_wordstat_for_topic(
            topic, out_dir, region=wordstat_region
        )

    return {
        "context_path": str(context_path),
        "serp_path": str(serp_path),
        "wordstat_path": str(wordstat_path) if wordstat_path else None,
        "wordstat_error": wordstat_error,
        "context": payload_context,
        "serp": payload_serp,
        "wordstat": wordstat_payload,
        "dry_run": dry_run,
        "out_dir": out_dir,
        "topic": topic,
    }


def fetch_wordstat_for_topic(
    topic: dict[str, str],
    out_dir: Path,
    *,
    region: str = "225",
    num_phrases: int = 20,
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    """Wordstat Search API v2 — локальный обход MCP-KV SSL на api.wordstat.yandex.net."""
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from excalibur_wordstat import load_credentials, top_requests

    api_key, folder_id = load_credentials(project_root())
    if not api_key or not folder_id:
        return None, None, (
            "YANDEX_CLOUD_API_KEY / YANDEX_CLOUD_FOLDER_ID не заданы "
            "(memory/site.env.local или teya-memory/teya.env.local)"
        )

    phrases: list[str] = []
    for key in ("primary_query",):
        val = (topic.get(key) or "").strip()
        if val and val not in phrases:
            phrases.append(val)
    secondary = topic.get("secondary_queries") or ""
    if isinstance(secondary, str):
        for part in re.split(r"[;,]", secondary):
            val = part.strip()
            if val and val not in phrases:
                phrases.append(val)

    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    for phrase in phrases[:3]:
        try:
            data = top_requests(
                phrase,
                api_key=api_key,
                folder_id=folder_id,
                num_phrases=num_phrases,
                regions=[region],
            )
            runs.append({"phrase": phrase, "ok": True, "response": data})
        except RuntimeError as exc:
            errors.append(f"{phrase}: {exc}")
            runs.append({"phrase": phrase, "ok": False, "error": str(exc)})

    payload = {
        "source": "excalibur_wordstat.py",
        "endpoint": "searchapi.api.cloud.yandex.net/v2/wordstat/topRequests",
        "region": region,
        "phrases": phrases,
        "runs": runs,
        "errors": errors,
    }
    path = out_dir / "research-wordstat.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if runs and not any(r.get("ok") for r in runs):
        return path, payload, "; ".join(errors) or "all wordstat calls failed"
    return path, payload, None


def _unique_urls(serp_runs: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for run in serp_runs:
        for row in run.get("results") or []:
            url = row.get("url") or ""
            if url and url not in seen:
                seen.add(url)
                out.append({"url": url, "title": row.get("title") or "", "from_query": run.get("query") or ""})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Excalibur BLOG: date context + fresh web search (step 0)")
    ap.add_argument("--topic-id", required=True, help="e.g. B01")
    ap.add_argument(
        "--topics-file",
        type=Path,
        default=None,
        help="Path to blog-topics.md (default: memory/topics/blog-topics.md)",
    )
    ap.add_argument("--output-dir", type=Path, default=None, help="Override article output directory")
    ap.add_argument("--timezone", default=DEFAULT_TZ, help=f"IANA timezone (default: {DEFAULT_TZ})")
    ap.add_argument("--max-results", type=int, default=6, help="Max SERP results per query")
    ap.add_argument("--dry-run", action="store_true", help="Only print date context and queries, no HTTP")
    ap.add_argument(
        "--wordstat",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch Wordstat via Search API v2 → research-wordstat.json (default: on)",
    )
    ap.add_argument("--wordstat-region", default="225", help="Wordstat region id (default 225 Russia)")
    args = ap.parse_args()

    root = project_root()
    topics_path = args.topics_file or root / "memory" / "topics" / "blog-topics.md"

    try:
        result = run_research_start(
            topic_id=args.topic_id.upper(),
            topics_path=topics_path if topics_path.is_absolute() else root / topics_path,
            output_dir=args.output_dir,
            tz_name=args.timezone,
            max_results=args.max_results,
            dry_run=args.dry_run,
            wordstat=args.wordstat,
            wordstat_region=args.wordstat_region,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"BLOCKER: {exc}", file=sys.stderr)
        return 1

    ctx = result["context"]["date_context"]
    print(f"OK date={ctx['today_ru']} year={ctx['year']} tz={ctx['timezone']}")
    print(f"topic={result['context']['topic']['topic_id']} slug={result['context']['topic'].get('slug')}")
    print(f"queries={len(result['context']['search_queries'])}")
    if args.dry_run:
        print(json.dumps(result["context"], ensure_ascii=False, indent=2))
        return 0

    unique = len(result["serp"].get("unique_urls") or [])
    print(f"serp_unique_urls={unique}")
    print(f"context={result['context_path']}")
    print(f"serp={result['serp_path']}")
    if args.wordstat:
        if result.get("wordstat_path"):
            print(f"wordstat={result['wordstat_path']}")
        if result.get("wordstat_error"):
            print(f"WARN wordstat: {result['wordstat_error']}", file=sys.stderr)
            return 2
    if result["serp"].get("errors"):
        print("WARN: some queries failed; see research-serp.json", file=sys.stderr)
        return 2 if unique == 0 else 0
    if unique == 0:
        print("BLOCKER: no search results; check network or queries", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
