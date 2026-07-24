#!/usr/bin/env python3
"""Write article.html via Google Gemini API (Excalibur BLOG writer step)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from excalibur_blog_topics import parse_topic_card  # noqa: E402


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def load_env(root: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for name in ("memory/site.env.local", "memory/site.env.local.example"):
        p = root / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def plain_char_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", "", html)
    return len(text)


def build_system_prompt(root: Path, article_dir: Path | None = None) -> str:
    contract = (root / "shared/excalibur-article-writing-contract.md").read_text(encoding="utf-8")
    slop = (root / ".cursor/skills/excalibur/references/ai-slop-blocklist.md")
    slop_txt = slop.read_text(encoding="utf-8") if slop.is_file() else ""
    voice = (root / "memory/brief/elena-voice-rules.md")
    voice_txt = voice.read_text(encoding="utf-8") if voice.is_file() else ""
    dzen = (root / "memory/brief/elena-dzen-writer-prompt.md")
    dzen_txt = dzen.read_text(encoding="utf-8") if dzen.is_file() else ""
    author_txt = ""
    if article_dir:
        author_ref = article_dir / "elena-author-draft.md"
        if author_ref.is_file():
            author_txt = author_ref.read_text(encoding="utf-8")[:8000]
    return f"""Ты — автор блога Natural Lift, голос Елены Шимановской.
Пиши как подружке: мягко, разговорно, для женщин 40-65. Без нейрослога, канцелярита и тяжёлого техязыка.

ГОЛОС ЕЛЕНЫ (обязательно):
{voice_txt[:4000]}

DZEN WRITER PROMPT (обязательно):
{dzen_txt[:14000]}

АВТОРСКИЙ ЭТАЛОН (если есть elena-author-draft.md):
{author_txt}

КОНТРАКТ (соблюдай строго):
{contract[:12000]}

АНТИ-SLOP:
{slop_txt[:4000]}

ФОРМАТ ОТВЕТА:
1) Сначала строка === ARTICLE_HTML ===
2) Полный article.html (только разрешённые теги, без h1, без figure, без inline-картинок)
3) Строка === META_JSON ===
4) JSON с полями meta_ab (title_seo, title_ctr, title_aeo, description_seo, description_ctr, description_aeo), description, focus_keyword
5) Строка === END ===

РУССКИЙ ЯЗЫК (критично):
- Живой разговорный русский. Как объясняешь подруге за кухонным столом.
- Запрещено: отклик/откликается → результат, изменения в лучшую сторону, что вам отзывается.
- Эффекты только в плюс: уйдут отёки, снимем зажимы (не «от отёка, от зажимов»).
- В лиде: сравним две техники, попробуйте обе; я чаще за фейс-йогу, но элементы фейсбилдинга тоже использую.
- Не используй англицизмы: комьюнити, фокус, workflow, insight, utility, performance, пампинг.
- Вместо "протокол" чаще пиши "план", "пошаговый план", "ритуал" - слово "протокол" не чаще 2 раз на всю статью.
- Вместо "чеклист" можно "список для самопроверки" (допустимо "чеклист" 1 раз в заголовке h2).
- Проверь орфографию. Без опечаток и лишних букв.
- Не упоминай Ревитонику, конкретных авторов или бренды конкурентов.
- Сравнивай фейсбилдинг (упражнения на тонус) и фейс-йогу (расслабление и привычки) нейтрально.

Объём article.html: минимум 12000 символов без HTML-тегов.
Запрещены длинные тире (—) и кавычки-ёлочки. Используй дефис (-) и прямые кавычки (").
Каждый сложный термин объясни простыми словами сразу после упоминания.
Не вставляй оглавление со ссылками на якоря.
Не вставляй figure и cover/inline — это делает cover-агент позже.

ТОЧКИ ВНИМАНИЯ (обязательно, см. DZEN WRITER PROMPT § «ТОЧКИ ВНИМАНИЯ»):
- После GEO-абзаца: blockquote-выжимка + один абзац <p><b>…целиком жирный…</b></p>.
- Минимум 6 h2, 2 blockquote, 2 ul, 4 абзаца с <b>Метка.</b> или <b>Метка:</b>, блок «Миниплан», 3-8 эмодзи.
- Не больше 4 коротких <p> подряд без h2/ul/blockquote/жирной метки.
- В конце article.html (после FAQ): блок Telegram — 🔥 <a>Мой Telegram-канал «…»</a> + <blockquote><i>❓ вопросы по теме … ⤵️</i></blockquote>.

ТАБЛИЦЫ (критично — иначе QA/linter FAIL):
- Протокол «время / что делать / зачем» — ТОЛЬКО <table><thead><tbody><tr><th><td>.
- Сравнение (тейпы vs расслабление, ошибки) — тоже <table>.
- ЗАПРЕЩЕНО склеивать «Время 2 минуты — что делать Зачем Утро…» в один <p>.
- Эталон: memory/blog/articles/B29-dinocharya-posle-45-rasporyadok-dnya-bez-fanatizma/article.html строки 95–130.
- Чеклист на 7 дней — <ol><li><b>День N.</b> …</li></ol>.
"""


def tg_cta_from_env(env: dict[str, str]) -> tuple[str, str]:
    url = (
        os.environ.get("NATURALLIFT_TELEGRAM_URL", "").strip()
        or env.get("NATURALLIFT_TELEGRAM_URL", "").strip()
        or "https://t.me/silver_cream"
    )
    title = (
        os.environ.get("NATURALLIFT_TELEGRAM_CHANNEL_TITLE", "").strip()
        or env.get("NATURALLIFT_TELEGRAM_CHANNEL_TITLE", "").strip()
        or "Елена Шим/Фейс йога и Омоложение лица"
    )
    return url, title


def build_user_prompt(article_dir: Path, root: Path, env: dict[str, str] | None = None) -> str:
    meta_path = article_dir / "article.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    research = (article_dir / "research-notes.md").read_text(encoding="utf-8")
    topic_id = meta.get("topic_id") or article_dir.name.split("-")[0]
    topics_path = root / "memory/topics/blog-topics.md"
    try:
        card = parse_topic_card(topics_path, topic_id)
    except ValueError:
        card = {}

    h2_plan = card.get("h2_outline") or ""
    links_block = ""
    m = re.search(r"## Internal links\n(.*?)(?=\n##|\Z)", research, re.S)
    if m:
        links_block = m.group(1).strip()

    env = env or {}
    tg_url, tg_title = tg_cta_from_env(env)

    wordstat_block = ""
    ws_path = article_dir / "research-wordstat.json"
    if ws_path.is_file():
        try:
            ws_doc = json.loads(ws_path.read_text(encoding="utf-8"))
            from excalibur_blog_wordstat_gate import collect_phrase_table

            table = collect_phrase_table(ws_doc)
            if table:
                top_phrase, top_shows = table[0]
                lines = [f"- approved_title (Wordstat top): «{top_phrase}» — {top_shows}/мес"]
                for p, c in table[1:6]:
                    lines.append(f"- LSI: «{p}» — {c}/мес")
                wordstat_block = (
                    "\nWORDSTAT (обязательно для title/h1/cover hook — не выдумывай нулевые ключи):\n"
                    + "\n".join(lines)
                    + "\n- title_ctr и cover hook: паттерн «[топ-фраза]: как [результат] без [страшилка]»\n"
                    + "- Название техники (Ковш и т.п.) — не в title, max 1 раз в тексте\n"
                )
        except Exception:
            wordstat_block = ""

    return f"""Напиши статью заново (полный rewrite).

topic_id: {topic_id}
h1: {meta.get('h1') or card.get('h1', '')}
slug: {meta.get('slug', '')}
primary_query: {meta.get('primary_query') or card.get('primary_query', '')}
secondary_queries: {', '.join(meta.get('secondary_queries') or [])}

H2-план (глаголы действия, используй как заголовки h2):
{h2_plan if h2_plan else '- см. research-notes Article outline'}

Internal links (вставь естественно, не больше лимитов conversion-map):
{links_block if links_block else '- B15 kisetnye, diagnostika-kozhi, main-silver-cream, kak-rasslabit-liczo'}

{wordstat_block}
RESEARCH:
{research}

article_mode: B (utility guide). FAQ 5-7 пар. Таблица ошибок. Минимум один ol с 5+ шагами.

ОФОРМЛЕНИЕ (точки внимания, обязательно):
- GEO <p> → <blockquote> выжимка → <p><b>жирный тезис-лид</b></p>
- 6+ h2; 2+ blockquote; 2+ ul; 4+ абзаца <b>Метка.</b>/<b>Метка:</b>; блок «Миниплан»; 3-8 эмодзи (✅❌💡)
- Списки ✅/❌; blockquote с 💡; вердикт в <blockquote><i>…</i></blockquote>

ФИНАЛ — Telegram (обязательно, последним блоком после FAQ):
<p>&nbsp;</p>
<p>🔥 <a href="{tg_url}">Мой Telegram-канал «{tg_title}»</a></p>
<blockquote><i>❓ [2-4 вопроса по теме статьи] Напишите в комментариях ⤵️</i></blockquote>
"""


def call_gemini(api_key: str, model: str, system: str, user: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai not installed. Run: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=api_key)
    gm = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
        generation_config={
            "temperature": 0.75,
            "max_output_tokens": 16384,
        },
    )
    response = gm.generate_content(user)
    return (response.text or "").strip()


def parse_response(raw: str) -> tuple[str, dict]:
    html = ""
    meta_patch: dict = {}
    if "=== ARTICLE_HTML ===" in raw:
        _, rest = raw.split("=== ARTICLE_HTML ===", 1)
        if "=== META_JSON ===" in rest:
            html_part, meta_part = rest.split("=== META_JSON ===", 1)
            html = html_part.strip()
            meta_raw = meta_part.split("=== END ===", 1)[0].strip()
            if meta_raw.startswith("```"):
                meta_raw = re.sub(r"^```(?:json)?\s*", "", meta_raw)
                meta_raw = re.sub(r"\s*```$", "", meta_raw)
            meta_patch = json.loads(meta_raw)
        else:
            html = rest.strip()
    else:
        m = re.search(r"(<p>.*</p>)\s*$", raw, flags=re.S)
        html = m.group(1) if m else raw
    html = html.strip()
    if not html.startswith("<"):
        raise RuntimeError("Gemini response missing valid article HTML")
    return html, meta_patch


def main() -> int:
    ap = argparse.ArgumentParser(description="Rewrite article.html via Gemini API")
    ap.add_argument("--article-dir", required=True)
    ap.add_argument("--model", default="", help="Override EXCALIBUR_GEMINI_MODEL")
    ap.add_argument(
        "--output",
        default="",
        help="Write HTML here instead of article.html (e.g. article.gemini-draft.html)",
    )
    ap.add_argument(
        "--draft-only",
        action="store_true",
        help="Set post_status=draft in meta; do not overwrite live article.html unless --output empty",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print prompt size only")
    args = ap.parse_args()

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir

    if not (article_dir / "research-notes.md").is_file():
        print("BLOCKER: research-notes.md required", file=sys.stderr)
        return 1

    env = load_env(root)
    api_key = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
        or env.get("GEMINI_API_KEY", "").strip()
        or env.get("GOOGLE_API_KEY", "").strip()
    )
    model = (
        args.model.strip()
        or os.environ.get("EXCALIBUR_GEMINI_MODEL", "").strip()
        or env.get("EXCALIBUR_GEMINI_MODEL", "").strip()
        or "gemini-2.0-flash"
    )

    system = build_system_prompt(root, article_dir)
    user = build_user_prompt(article_dir, root, env)

    if args.dry_run:
        print(json.dumps({"model": model, "system_chars": len(system), "user_chars": len(user)}, ensure_ascii=False))
        return 0

    if not api_key:
        print(
            "BLOCKER: set GEMINI_API_KEY in memory/site.env.local or env var",
            file=sys.stderr,
        )
        return 1

    print(f"Calling Gemini model={model} ...", flush=True)
    raw = call_gemini(api_key, model, system, user)
    html, meta_patch = parse_response(raw)

    chars = plain_char_count(html)
    if chars < 11500:
        print(f"WARN: char_count={chars} below 12000 target", file=sys.stderr)

    html_path = Path(args.output) if args.output else article_dir / "article.html"
    if not html_path.is_absolute():
        html_path = article_dir / html_path
    html_path.write_text(html + "\n", encoding="utf-8")
    print(f"OK {html_path.name} chars={chars}")

    meta_path = article_dir / "article.meta.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {}
    gemini_meta = {
        "char_count": chars,
        "writer_model": model,
        "writer_engine": "gemini",
        "post_status": "draft",
        "html_file": html_path.name,
    }
    if meta_patch.get("description"):
        gemini_meta["description"] = meta_patch["description"]
    if meta_patch.get("focus_keyword"):
        gemini_meta["focus_keyword"] = meta_patch["focus_keyword"]
    if meta_patch.get("meta_ab"):
        gemini_meta["meta_ab"] = meta_patch["meta_ab"]

    if args.output or args.draft_only:
        sidecar = article_dir / "article.gemini-draft.meta.json"
        sidecar.write_text(json.dumps(gemini_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK {sidecar.name} post_status=draft (live article.html не тронут)")
    else:
        meta["char_count"] = chars
        meta["writer_model"] = model
        meta["writer_engine"] = "gemini"
        if not meta.get("post_status") or meta.get("post_status") == "draft":
            meta["post_status"] = "publish"
        if meta_patch.get("description"):
            meta["description"] = meta_patch["description"]
        if meta_patch.get("focus_keyword"):
            meta["focus_keyword"] = meta_patch["focus_keyword"]
        if meta_patch.get("meta_ab"):
            meta["meta_ab"] = {**(meta.get("meta_ab") or {}), **meta_patch["meta_ab"]}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK meta updated writer_engine=gemini model={model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
