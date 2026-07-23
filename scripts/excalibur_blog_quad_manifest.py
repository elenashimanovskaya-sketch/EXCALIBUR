#!/usr/bin/env python3
"""Fill quad-manifest.json: cover hook + inline visual_type per H2 (one quad canvas)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from excalibur_blog_cover_schemes import pick_cover_scheme, topic_number

# Reuse type picker from visual manifest module inline
TYPE_PRIORITY = [
    "comparison_table_ui",
    "workflow_diagram",
    "checklist_board",
    "schema_faq_ui",
    "tool_screenshot",
    "infographic_card",
]
EXERCISE_VISUAL_TYPE = "exercise_steps_host"
EXERCISE_ARTICLE_KEYWORDS = (
    "упражнен",
    "пошагово",
    "техника",
    "ковш",
    "рамка",
    "расслаблен",
    "проработ",
    "how_to",
)
EXERCISE_H2_KEYWORDS = (
    "пошагово",
    "техника",
    "упражнен",
    "как делать",
    "шаг",
)
DEFAULT_SLOT_MAP = {
    "cover": "top_left",
    "inline_1": "top_right",
    "inline_2": "bottom_left",
    "inline_3": "bottom_right",
}


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_h2_titles(article_html: Path) -> list[str]:
    if not article_html.is_file():
        return []
    text = article_html.read_text(encoding="utf-8")
    titles: list[str] = []
    for match in re.finditer(r"<h2[^>]*>(.*?)</h2>", text, flags=re.I | re.S):
        title = re.sub(r"<[^>]+>", "", match.group(1))
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue
        if title.lower() in {"частые вопросы", "faq"}:
            break
        titles.append(title)

    anchor_titles = [
        re.sub(r"\s+", " ", a).strip()
        for a in re.findall(r'data-h2-anchor="([^"]+)"', text, flags=re.I)
        if re.sub(r"\s+", " ", a).strip()
    ]

    if len(anchor_titles) >= 3:
        return anchor_titles[:3]
    if len(titles) >= 3:
        return titles[:3]

    merged: list[str] = []
    for t in anchor_titles + titles:
        if t.lower() in {"частые вопросы", "faq"}:
            break
        if t not in merged:
            merged.append(t)
    return merged


def score_type(h2: str, type_def: dict) -> int:
    hay = h2.lower()
    score = 0
    for kw in type_def.get("keywords") or []:
        if kw.strip().lower() in hay:
            score += 2
    return score


def pick_visual_type(h2: str, types_catalog: dict, used: set[str]) -> str:
    types = types_catalog.get("types") or {}
    scored: list[tuple[int, str]] = []
    for type_id, type_def in types.items():
        scored.append((score_type(h2, type_def), type_id))
    scored.sort(key=lambda item: (-item[0], TYPE_PRIORITY.index(item[1]) if item[1] in TYPE_PRIORITY else 99))
    for score, type_id in scored:
        if score > 0 and type_id not in used:
            return type_id
    for type_id in TYPE_PRIORITY:
        if type_id not in used:
            return type_id
    return TYPE_PRIORITY[0]


def is_exercise_h2(h2: str) -> bool:
    hay = h2.lower()
    return any(kw in hay for kw in EXERCISE_H2_KEYWORDS)


def is_exercise_article(meta: dict[str, Any], article_html: Path, h2s: list[str]) -> bool:
    if meta.get("has_exercise") is True:
        return True
    if (meta.get("search_intent") or "").strip().lower() == "how_to" and any(
        kw in (meta.get("primary_query") or meta.get("h1") or "").lower() for kw in ("упражнен", "техника", "ковш", "рамка")
    ):
        return True
    blob = " ".join(
        [
            meta.get("h1") or "",
            meta.get("primary_query") or "",
            meta.get("slug") or "",
            " ".join(h2s[:4]),
        ]
    ).lower()
    if any(kw in blob for kw in EXERCISE_ARTICLE_KEYWORDS):
        return True
    if article_html.is_file():
        plain = re.sub(r"<[^>]+>", " ", article_html.read_text(encoding="utf-8"))
        if re.search(r"<ol\b", article_html.read_text(encoding="utf-8"), flags=re.I) and "шаг" in plain.lower():
            return True
    return False


def exercise_h2_slot_index(h2s: list[str]) -> int | None:
    for i, h2 in enumerate(h2s[:3]):
        if "пошагово" in h2.lower():
            return i
    for i, h2 in enumerate(h2s[:3]):
        if is_exercise_h2(h2):
            return i
    return None


def scene_hint_for_type(type_id: str, h2: str) -> str:
    hints = {
        "comparison_table_ui": f"Таблица «ошибка / что происходит / как исправить» по теме секции — «{h2}»",
        "workflow_diagram": f"Пошаговая схема с стрелками и номерами по теме секции — «{h2}»",
        "exercise_steps_host": (
            f"Елена пошагово показывает упражнение из секции «{h2}»: 4-5 numbered steps, "
            f"на каждом шаге она сама делает движение (как снимает домашний урок), "
            f"короткие подписи на русском, розовые стрелки направления, sticky note «3-5 минут ежедневно»"
        ),
        "checklist_board": f"Чеклист на клипборде по теме секции (без чужих инструментов) — «{h2}»",
        "schema_faq_ui": f"FAQ-блок по теме секции — «{h2}»",
        "tool_screenshot": f"Иллюстрация инструмента/техники по теме секции — «{h2}»",
        "infographic_card": f"Трёхколоночная инфографика ошибка → процесс → результат — «{h2}»",
    }
    return hints.get(type_id, f"Полезная иллюстрация по теме секции — «{h2}»")


def alt_for_type(type_id: str, h2: str, types_catalog: dict) -> str:
    label = ((types_catalog.get("types") or {}).get(type_id) or {}).get("label_ru") or type_id
    return f"{label}: {h2}"


def problem_scene_hint(topic_id: str, meta: dict[str, Any]) -> str:
    """Visual focus for S7 cover — problem zone, no on-image text."""
    mapping = {
        "B15": (
            "Крупный план зоны над верхней губой: вертикальные кисетные морщинки, "
            "подушечка пальца у красной каймы губы, спокойное лицо 45-55. "
            "Variant split_subtle_before_after: слева линии чуть глубже, справа мягче, одна женщина."
        ),
        "B16": (
            "Профиль generic woman 45-55 (НЕ Елена): горизонтальные «кольца Венеры» на передней/боковой шее видны чётко. "
            "Variant split_subtle_before_after: слева линии глубже, справа та же женщина/ракурс — мягче. "
            "Ладонь на боковой шее, тонкие жёлтые стрелки без букв, studio beige фон."
        ),
        "B14": (
            "Крупный план межбровья: вертикальные складки между бровями, "
            "пальцы мягко расходят брови к вискам, без агрессии."
        ),
    }
    if topic_id in mapping:
        return mapping[topic_id]
    primary = (meta.get("primary_query") or meta.get("h1") or "").strip()
    return f"Крупный план зоны проблемы статьи: {primary}. Жест показывает зону, чистый studio фон."


def build_manifest(article_dir: Path, root: Path, preserve: dict | None) -> dict[str, Any]:
    meta_path = article_dir / "article.meta.json"
    meta = load_json(meta_path) if meta_path.is_file() else {}
    types_catalog = load_json(root / "memory/cover/inline-visual-types.json")
    h2s = extract_h2_titles(article_dir / "article.html")
    topic_id = meta.get("topic_id") or article_dir.name.split("-")[0]
    article_topic = meta.get("h1") or article_dir.name
    exercise_article = is_exercise_article(meta, article_dir / "article.html", h2s)
    exercise_slot_idx = exercise_h2_slot_index(h2s) if exercise_article else None

    old_cover = ((preserve or {}).get("slots") or {}).get("cover") or {}
    topic_num = topic_number(topic_id)
    meta_scheme = (meta.get("cover_scheme_id") or "").strip()
    preserve_scheme = ((preserve or {}).get("cover_scheme_id") or "").strip()
    cover_scheme_id = preserve_scheme or meta_scheme
    # S7 по умолчанию для всех статей: обложка без текста, нейроперсонаж + проблема.
    # Явный override только через meta.cover_scheme_id (legacy S1-S6).
    use_s7 = cover_scheme_id.startswith("S7") if cover_scheme_id else True
    if not cover_scheme_id:
        cover_scheme_id = "S7_problem_hero"
    if use_s7:
        cover = {
            "quadrant": "top_left",
            "role": "cover_problem_hero",
            "alt": old_cover.get("alt") or f"Обложка: {article_topic}",
            "host_rule": old_cover.get("host_rule") or "generic_woman_45_55",
            "scene_hint": old_cover.get("scene_hint") or problem_scene_hint(topic_id, meta),
        }
    else:
        if not cover_scheme_id:
            cover_scheme_id = preserve_scheme or meta_scheme
        cover = {
            "quadrant": "top_left",
            "role": "cover_meme_hero",
            "alt": old_cover.get("alt") or f"Обложка: {article_topic}",
            "scene_hint": old_cover.get("scene_hint")
            or meta.get("cover_scene_hint")
            or "Елена в йога-костюме (не свитер), тема статьи в руках/на фоне, rose-gold интерьер, без SEO-текстов",
            "meme_caption_ru": old_cover.get("meme_caption_ru")
            or meta.get("cover_meme_caption_ru")
            or "7 минут дома",
        }

    used: set[str] = set()
    slots: dict[str, Any] = {"cover": cover}
    for idx, slot_key in enumerate(("inline_1", "inline_2", "inline_3"), start=1):
        h2 = h2s[idx - 1] if idx - 1 < len(h2s) else f"Секция {idx}"
        if exercise_slot_idx is not None and (idx - 1) == exercise_slot_idx:
            visual_type = EXERCISE_VISUAL_TYPE
        else:
            visual_type = pick_visual_type(h2, types_catalog, used | {EXERCISE_VISUAL_TYPE})
        used.add(visual_type)
        old = ((preserve or {}).get("slots") or {}).get(slot_key) or {}
        slots[slot_key] = {
            "quadrant": DEFAULT_SLOT_MAP[slot_key],
            "h2_anchor": old.get("h2_anchor") or h2,
            "visual_type": visual_type,
            "scene_hint": scene_hint_for_type(visual_type, old.get("h2_anchor") or h2),
            "alt": alt_for_type(visual_type, old.get("h2_anchor") or h2, types_catalog),
        }

    cover_hook = (
        (preserve or {}).get("cover_hook")
        or meta.get("primary_query")
        or meta.get("h1")
        or article_topic
    )
    schemes_data = load_json(root / "memory/cover/cover-schemes.json") if (root / "memory/cover/cover-schemes.json").is_file() else {}
    if not cover_scheme_id:
        scheme = pick_cover_scheme(topic_id, schemes_data)
        cover_scheme_id = scheme.get("scheme_id") or ""

    cover_problem = (preserve or {}).get("cover_problem") or meta.get("primary_query") or cover_hook

    return {
        "topic_id": topic_id,
        "canvas_file": "cover/canvas-quad.png",
        "layout": "2x2",
        "pipeline": "quad_canvas_1x_mcp",
        "style_preset": meta.get("quad_style_preset") or "digital_meme_collage_ru",
        "style_file": meta.get("quad_style_file") or "memory/cover/quad-style-digital-meme-collage-ru.json",
        "blog_hero": "memory/cover/blog-hero.json",
        "inline_types_catalog": "memory/cover/inline-visual-types.json",
        "cover_hook": cover_hook,
        "cover_problem": cover_problem,
        "cover_scheme_id": cover_scheme_id,
        "mcp_note": "ONE gpt-image-2 call with input_urls=[reference_url_hosted], then split",
        "exercise_article": exercise_article,
        "exercise_inline_slot": (f"inline_{exercise_slot_idx + 1}" if exercise_slot_idx is not None else None),
        "slots": slots,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", required=True)
    ap.add_argument("--out", default="cover/quad-manifest.json")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = article_dir / out_path

    preserve = load_json(out_path) if args.merge and out_path.is_file() else None
    manifest = build_manifest(article_dir, root, preserve)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(out_path, manifest)
    print(f"OK manifest={out_path}")
    for key in ("inline_1", "inline_2", "inline_3"):
        s = manifest["slots"][key]
        print(f"  {key}: {s['visual_type']} -> {s['h2_anchor']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
