#!/usr/bin/env python3
"""Cover panel scheme rotation: 5 alternating compositions by topic number."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def topic_number(topic_id: str) -> int:
    match = re.match(r"B(\d+)", (topic_id or "").strip(), flags=re.IGNORECASE)
    return int(match.group(1)) if match else 1


def load_cover_schemes(root: Path) -> dict[str, Any]:
    path = root / "memory/cover/cover-schemes.json"
    if not path.is_file():
        return {"schemes": [], "forbidden_global": []}
    return json.loads(path.read_text(encoding="utf-8"))


def pick_cover_scheme(topic_id: str, schemes_data: dict[str, Any]) -> dict[str, Any]:
    schemes = schemes_data.get("schemes") or []
    if not schemes:
        return {}
    idx = (topic_number(topic_id) - 1) % len(schemes)
    return schemes[idx]


def resolve_cover_scheme(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    schemes_data = load_cover_schemes(root)
    scheme_id = (manifest.get("cover_scheme_id") or "").strip()
    if scheme_id:
        for scheme in schemes_data.get("schemes") or []:
            if scheme.get("scheme_id") == scheme_id:
                return {**scheme, "forbidden_global": schemes_data.get("forbidden_global") or []}
    topic_id = manifest.get("topic_id") or "B01"
    scheme = pick_cover_scheme(topic_id, schemes_data)
    if scheme:
        scheme = {**scheme, "forbidden_global": schemes_data.get("forbidden_global") or []}
    return scheme


def cover_scheme_prompt_block(scheme: dict[str, Any]) -> str:
    if not scheme:
        return ""
    forbidden = list(scheme.get("forbidden_global") or []) + list(scheme.get("forbidden_poses") or [])
    forbidden_txt = "; ".join(forbidden) if forbidden else "симметричные руки у висков"
    return (
        f"COVER SCHEME {scheme.get('scheme_id', '')} — {scheme.get('label_ru', '')}: "
        f"{scheme.get('pose_rule', '').strip()} "
        f"Composition: {scheme.get('composition', '').strip()}. "
        f"MANDATORY: pose/composition from scheme; scene_hint = topic/props only, never override scheme pose. "
        f"FORBIDDEN on cover: {forbidden_txt}."
    )


def _is_face_yoga_topic(manifest: dict[str, Any], cover_slot: dict[str, Any]) -> bool:
    hay = " ".join(
        [
            str(manifest.get("cover_problem") or ""),
            str(manifest.get("cover_hook") or ""),
            str(cover_slot.get("scene_hint") or ""),
            str(manifest.get("topic_id") or ""),
        ]
    ).lower()
    keys = (
        "фейс",
        "face yoga",
        "face-yoga",
        "йога для лица",
        "упражнен",
        "массаж лица",
        "асahi",
        "асахи",
        "ревитоника",
        "угol молодости",
        "угол молодости",
    )
    return any(k in hay for k in keys)


def cover_problem_hero_prompt_block(manifest: dict[str, Any], cover_slot: dict[str, Any], scheme: dict[str, Any]) -> str:
    """Top-left cover panel: problem-focused editorial, no on-image text (S7)."""
    variants = scheme.get("variants") or [
        "closeup_problem_gesture",
        "split_subtle_before_after",
        "ghost_correct_overlay",
    ]
    if _is_face_yoga_topic(manifest, cover_slot):
        variant = "split_subtle_before_after"
        variant_note = (
            "Face-yoga / exercise topic: mandatory subtle before-after in ONE frame "
            "(left problem visible, right same woman same angle softer). "
        )
    else:
        variant = variants[(topic_number(manifest.get("topic_id", "B01")) - 1) % len(variants)]
        variant_note = ""
    scene = (cover_slot.get("scene_hint") or "").strip()
    problem = (manifest.get("cover_problem") or manifest.get("cover_hook") or "").strip()
    host_rule = (cover_slot.get("host_rule") or "generic_woman_45_55").strip()
    if host_rule == "use_elena_reference":
        host_line = (
            "Use blog host Elena likeness from reference ONLY if scene_hint requests host; "
            "otherwise generic relatable Russian woman 45-55, natural skin, not stock plastic."
        )
    else:
        host_line = (
            "Do NOT copy Elena from reference on this cover panel. "
            "Generic relatable Russian woman 45-55, natural aging visible, premium wellness editorial photo."
        )

    return "\n".join(
        [
            f"Top-left COVER ONLY — S7 problem hero, variant {variant}.",
            variant_note,
            host_line,
            f"Article problem zone (visual focus): {problem}.",
            scene,
            "Full-bleed inside top-left quadrant, 16:9, clean studio background (beige #d4c4b0 or soft grey).",
            "COVER PANEL: photo only — NO Cyrillic, NO Latin headlines, NO logos, NO sticky notes, NO torn paper, NO YouTube typography.",
            "All Cyrillic text / UI / checklists / diagrams belong ONLY to the other 3 quad panels (top-right, bottom-left, bottom-right).",
            "Thin yellow directional arrows/lines OK if they show massage direction — without any letters.",
            "Problem must be VISUALLY READABLE at thumbnail size: wrinkles/lines/folds clearly visible, not airbrushed away.",
            "Prefer split before/after in one frame when topic is lines/wrinkles: left = problem more visible, right = same woman same angle softer — NOT plastic surgery ad.",
            "Soft natural light, shallow depth of field on problem zone, human editorial NOT sterile corporate stock.",
            f"FORBIDDEN on cover panel: {scheme.get('forbidden_poses', [])}; Drake; syringe; clinic; English UI.",
        ]
    )


def rotate_reference_urls(urls: list[str], topic_id: str) -> list[str]:
    clean = [u.strip() for u in urls if str(u).strip()]
    if len(clean) <= 1:
        return clean
    start = (topic_number(topic_id) - 1) % len(clean)
    return clean[start:] + clean[:start]


def filter_portrait_reference_urls(urls: list[str]) -> list[str]:
    """Только портреты Елены для i2i — без дизайн-PNG и прочего."""
    out: list[str] = []
    for url in urls:
        low = url.lower()
        if low.endswith(".png") and "mkatrin" not in low and "img_" not in low:
            continue
        if any(x in low for x in ("mkatrin-", "/img_0", "img_04", "img_05")):
            out.append(url)
    return out or [u.strip() for u in urls if str(u).strip()]


def yoga_master_outfit_prompt(topic_id: str) -> str:
    """Йога-костюм мастера фейс-йоги — новый цвет/фасон, не копировать reference."""
    palette = ("fuchsia", "cobalt", "terracotta", "emerald", "plum", "coral")
    color = palette[(topic_number(topic_id) - 1) % len(palette)]
    return (
        f"Professional face-yoga master outfit: matching yoga set (high-waist leggings + fitted sports top/bra), "
        f"{color} accent this article, modern wellness studio look. "
        "Preserve EXACT face likeness from reference ONLY — do NOT copy clothing, hairstyle props or background from reference photo."
    )
