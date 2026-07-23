"""Parse blog topic cards from memory/topics/blog-topics.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def parse_topic_card(topics_path: Path, topic_id: str) -> dict[str, Any]:
    text = topics_path.read_text(encoding="utf-8")
    pattern = rf"##\s+{re.escape(topic_id)}\s+—[^\n]*\n(.*?)(?=\n---|\n##\s+[A-Z]\d+|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"topic card not found: {topic_id}")

    block = match.group(1)

    def field(name: str, default: str = "") -> str:
        table = re.search(
            rf"^\|\s*{re.escape(name)}\s*\|\s*(.+?)\s*\|\s*$",
            block,
            re.IGNORECASE | re.MULTILINE,
        )
        if table:
            return table.group(1).strip()
        bullet = re.search(rf"-\s*\*\*{re.escape(name)}:\*\*\s*(.+)", block, re.IGNORECASE)
        if bullet:
            return bullet.group(1).strip()
        return default

    slug = field("slug") or field("slug_hint")
    h1 = field("h1") or field("title_draft")
    search_intent = field("search_intent") or field("intent")
    if "how-to" in search_intent.lower() or "how_to" in search_intent.lower():
        search_intent = "how_to"
    elif "comparison" in search_intent.lower():
        search_intent = "comparison"
    elif "beginner" in search_intent.lower() or "parent" in search_intent.lower():
        search_intent = "parent_guide"
    elif search_intent and search_intent not in {"how_to", "checklist", "comparison", "troubleshooting", "workflow", "parent_guide"}:
        search_intent = "how_to"

    secondary_raw = field("secondary_queries")
    secondary = [q.strip() for q in re.split(r",|;", secondary_raw) if q.strip()]

    return {
        "topic_id": topic_id.upper(),
        "priority": field("priority"),
        "slug": slug,
        "h1": h1,
        "primary_query": field("primary_query"),
        "secondary_queries": secondary,
        "search_intent": search_intent,
        "article_mode": field("article_mode") or "B",
        "h2_outline": field("h2_outline"),
    }
