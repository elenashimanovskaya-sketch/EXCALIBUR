#!/usr/bin/env python3
"""Normalize Excalibur article.html spacing and semantic blocks before preview/publish."""
from __future__ import annotations

import re


SPACER = "<p>&nbsp;</p>"

# Убираем латиницу и ярлыки «инсайт» из выжимки / миниплана при publish/preview.
_TLDR_LABEL_IN_BLOCKQUOTE = re.compile(
    r"(<blockquote>\s*)<b>\s*(?:TL;DR\s*/\s*)?(?:Быстрый\s+)?инсайт\s*:?\s*</b>\s*",
    flags=re.IGNORECASE,
)
_TLDR_LABEL_PLAIN = re.compile(
    r"(<blockquote>\s*)(?:TL;DR\s*/\s*)?(?:Быстрый\s+)?инсайт\s*:\s*",
    flags=re.IGNORECASE,
)
_MINI_WORKFLOW = re.compile(r"Мини-workflow", flags=re.IGNORECASE)


def _has_spacer_before(html: str, pos: int) -> bool:
    before = html[max(0, pos - 80) : pos].strip()
    return before.endswith(SPACER) or before.endswith("</figure>")


def _insert_spacer(html: str, pos: int) -> str:
    if _has_spacer_before(html, pos):
        return html
    return html[:pos] + f"\n{SPACER}\n" + html[pos:]


def _insert_before_matches(html: str, pattern: str) -> str:
    """Вставка spacer перед совпадениями — с конца, чтобы не сбивать позиции."""
    matches = list(re.finditer(pattern, html, flags=re.I))
    for m in reversed(matches):
        html = _insert_spacer(html, m.start())
    return html


def split_checklist_header(html: str) -> str:
    """Чеклист: заголовок отдельным абзацем, тело — следующим."""
    pattern = re.compile(
        r"<p><b>Чеклист перед стартом:</b>\s+(.+?)</p>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        body = m.group(1).strip()
        return f"<p><b>Чеклист перед стартом:</b></p>\n{SPACER}\n<p>{body}</p>"

    return pattern.sub(repl, html)


def spacer_around_lists(html: str) -> str:
    """Воздух вокруг нумерованных протоколов: intro <p> отдельно от <ol>."""
    out = html
    out = re.sub(
        r"(</p>)\s*(<ol\b)",
        lambda m: m.group(1) + (f"\n{SPACER}\n" if SPACER not in m.group(0) else "\n") + m.group(2),
        out,
        flags=re.I,
    )
    out = re.sub(
        r"(</ol>)\s*(<p>(?!&nbsp;))",
        lambda m: m.group(1) + f"\n{SPACER}\n" + m.group(2),
        out,
        flags=re.I,
    )
    return out


def ensure_spacers(html: str) -> str:
    out = html
    for pattern in (
        r"<h2\b",
        r"<h3\b",
        r"<table\b",
        r"<figure\b",
        r"<blockquote>\s*<b>Достоверность:",
    ):
        out = _insert_before_matches(out, pattern)

    # После таблицы
    for m in reversed(list(re.finditer(r"</table>", out, flags=re.I))):
        end = m.end()
        after = out[end : end + 24].strip()
        if not after.startswith("<p>&nbsp;"):
            out = out[:end] + f"\n{SPACER}\n" + out[end:]

    # После blockquote «Достоверность» перед FAQ
    for m in reversed(list(re.finditer(r"</blockquote>", out, flags=re.I))):
        after = out[m.end() : m.end() + 120]
        if re.search(r"<h2[^>]*>\s*Частые вопросы", after, flags=re.I):
            out = _insert_spacer(out, m.end())

    # После figure
    for m in reversed(list(re.finditer(r"</figure>", out, flags=re.I))):
        end = m.end()
        after = out[end : end + 24].strip()
        if not after.startswith("<p>&nbsp;"):
            out = out[:end] + f"\n{SPACER}\n" + out[end:]

    out = re.sub(
        rf"(?:\s*{re.escape(SPACER)}\s*){{2,}}",
        f"\n{SPACER}\n",
        out,
        flags=re.I,
    )
    return out.strip() + "\n"


def strip_latin_editorial_labels(html: str) -> str:
    """Выжимка в blockquote — только текст; «Мини-workflow» → «Миниплан»."""
    out = _TLDR_LABEL_IN_BLOCKQUOTE.sub(r"\1", html)
    out = _TLDR_LABEL_PLAIN.sub(r"\1", out)
    out = _MINI_WORKFLOW.sub("Миниплан", out)
    return out


def format_article_html(html: str) -> str:
    html = strip_latin_editorial_labels(html)
    html = split_checklist_header(html)
    html = spacer_around_lists(html)
    html = ensure_spacers(html)
    return html


def main() -> int:
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Format article.html spacing for WP/Dzen")
    ap.add_argument("article_html", type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    src = args.article_html.read_text(encoding="utf-8")
    out = format_article_html(src)
    if args.write:
        args.article_html.write_text(out, encoding="utf-8")
        print(f"OK formatted={args.article_html}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
