#!/usr/bin/env python3
"""Build MCP prompt + batch for ONE quad canvas (4 panels) with hero i2i reference."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from excalibur_blog_cover_schemes import (
    cover_problem_hero_prompt_block,
    cover_scheme_prompt_block,
    filter_portrait_reference_urls,
    resolve_cover_scheme,
    rotate_reference_urls,
    yoga_master_outfit_prompt,
)


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_prompt_fragment(text: str) -> str:
    """Убрать вложенные «» из H2 — ломают gpt-image-2."""
    t = str(text or "").strip()
    t = t.replace("«", "").replace("»", "")
    return t


def inline_panel_prompt(
    slot: dict, types_catalog: dict, design_code: dict, hero: dict | None = None, topic_id: str = "B01"
) -> str:
    type_id = slot.get("visual_type") or "infographic_card"
    type_def = (types_catalog.get("types") or {}).get(type_id) or {}
    h2_clean = sanitize_prompt_fragment(slot.get("h2_anchor", ""))
    host_rule = ""
    if type_def.get("allow_host_face"):
        host_rule = (
            "REQUIRED: blog host Elena demonstrates exercise — preserve EXACT face likeness from reference; "
            "she performs each step on camera like a home lesson, NOT a faceless diagram. "
            + yoga_master_outfit_prompt(topic_id)
            + " "
            + (hero.get("prompt_fragment", "").strip() if hero else "")
        ).strip()
    else:
        host_rule = "NO blog host face."
    parts = [
        f"[{type_def.get('label_ru', type_id)}]",
        type_def.get("prompt_prefix", "").strip(),
        f"H2: {h2_clean}.",
        sanitize_prompt_fragment(slot.get("scene_hint", "")),
        type_def.get("prompt_suffix", "").strip(),
        "MANDATORY: ALL visible text labels, table headers, sticky notes, UI captions MUST be Russian Cyrillic ONLY. ZERO English words, ZERO Latin UI.",
        host_rule,
        (design_code.get("inline_human_touch") or "").strip(),
        f"Negative: {type_def.get('negative', '')}",
    ]
    return " ".join(p for p in parts if p)


def build_prompt(manifest: dict, style: dict, hero: dict, types_catalog: dict, design_code: dict, root: Path) -> str:
    slots = manifest.get("slots") or {}
    scheme = resolve_cover_scheme(manifest, root)
    topic_id = manifest.get("topic_id") or "B01"

    def slot(key: str) -> dict:
        return slots.get(key) or {}

    cover = slot("cover")
    i1, i2, i3 = slot("inline_1"), slot("inline_2"), slot("inline_3")

    scheme_id = (scheme.get("scheme_id") or "").strip()
    use_problem_hero = scheme_id.startswith("S7")

    lines = [
        style.get("global_prompt_prefix", "").strip(),
        "Single canvas 2048x1152 pixels, exact 2x2 grid, four equal 16:9 panels (1024x576 each). "
        "Optional thin white gutters ONLY on the exact center lines (x=1024 and y=576); "
        "keep all panel content strictly inside its quadrant — no bleed across seams.",
        "",
    ]

    if use_problem_hero:
        lines.extend(
            [
                cover_problem_hero_prompt_block(manifest, cover, scheme),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "REFERENCE FACE (top-left cover ONLY): preserve EXACT likeness from input reference photo —",
                hero.get("prompt_fragment", "").strip(),
                (hero.get("outfit_rule") or "Outfit is agent choice for the hook — not locked to reference photo.").strip(),
                "",
                cover_scheme_prompt_block(scheme),
                "",
                f'Top-left COVER — hook "{manifest.get("cover_hook", "")}":',
                (design_code.get("cover_panel_prompt_block") or "").strip(),
                cover.get("scene_hint", ""),
                f'Cyrillic hook caption: "{cover.get("meme_caption_ru", "")}".',
                "Wellness sticky notes and mirror cues only. NO SEO, NO Wordstat, NO laptop dashboards on cover.",
                "",
            ]
        )

    lines.extend(
        [
            f"Top-right — {inline_panel_prompt(i1, types_catalog, design_code, hero, topic_id)}",
            "",
            f"Bottom-left — {inline_panel_prompt(i2, types_catalog, design_code, hero, topic_id)}",
            "",
            f"Bottom-right — {inline_panel_prompt(i3, types_catalog, design_code, hero, topic_id)}",
            "",
        ]
    )
    if use_problem_hero:
        lines.append(
            "single canvas 2048x1152 pixels, exact 2x2 grid, four equal 16:9 panels (1024x576 each), "
            "thin white gutters, high detail. Top-left cover: editorial photo ONLY — NO Cyrillic hook, NO meme text."
        )
    else:
        lines.append(style.get("global_prompt_suffix", "").strip())
    exercise_slot = (manifest.get("exercise_inline_slot") or "").strip()
    has_exercise_host = exercise_slot in {"inline_1", "inline_2", "inline_3"} or any(
        (slots.get(k) or {}).get("visual_type") == "exercise_steps_host" for k in ("inline_1", "inline_2", "inline_3")
    )
    if has_exercise_host:
        lines.append(
            f"Inline panel {exercise_slot or 'with exercise_steps_host'}: Elena ON CAMERA step-by-step — host face REQUIRED on that panel only. "
            "Other two inline panels: editorial UI/diagram only — NO host face."
        )
        lines.append(yoga_master_outfit_prompt(topic_id))
        lines.append(
            f"Negative: {style.get('global_negative_prompt', '')}, {design_code.get('global_negative', '')}, "
            "faceless exercise infographic, generic stock woman instead of Elena on exercise panel"
        )
    else:
        lines.append("Inline panels (top-right, bottom-left, bottom-right): editorial UI/diagram only — NO host face on those three panels.")
        lines.append(
            "MANDATORY LANGUAGE: every inline panel — ALL visible text in Russian Cyrillic ONLY. "
            "No English words, no Latin UI labels (Remove/Replace/Allow, Day 1, Checklist, etc.)."
        )
        lines.append(
            f"Negative: {style.get('global_negative_prompt', '')}, {design_code.get('global_negative', '')}, extra faces on inline panels, English text, Latin UI"
        )
    return "\n".join(line for line in lines if line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", required=True)
    ap.add_argument("--manifest", default="cover/quad-manifest.json")
    ap.add_argument("--write-batch", action="store_true", help="Write cover/quad-mcp-batch.json")
    args = ap.parse_args()

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = article_dir / manifest_path
    if not manifest_path.is_file():
        print(f"❌ PROMPT BLOCKER: {manifest_path} not found", file=sys.stderr)
        return 1

    manifest = load_json(manifest_path)
    hero = load_json(root / manifest.get("blog_hero", "memory/cover/blog-hero.json"))
    style = load_json(root / manifest.get("style_file", "memory/cover/quad-style-digital-meme-collage-ru.json"))
    types_path = root / manifest.get("inline_types_catalog", "memory/cover/inline-visual-types.json")
    types_catalog = load_json(types_path) if types_path.is_file() else {"types": {}}
    design_code_path = root / style.get("design_code", "memory/cover/cover-design-code.json")
    design_code = load_json(design_code_path) if design_code_path.is_file() else {}

    ref_urls: list[str] = []
    manifest_refs = manifest.get("reference_urls_hosted")
    if isinstance(manifest_refs, list) and manifest_refs:
        ref_urls = [str(u).strip() for u in manifest_refs if str(u).strip()]
    else:
        primary_refs = hero.get("reference_urls_primary")
        if isinstance(primary_refs, list) and primary_refs:
            ref_urls = [str(u).strip() for u in primary_refs if str(u).strip()]
        ref_urls_list = hero.get("reference_urls_hosted") or []
        if isinstance(ref_urls_list, list):
            for u in ref_urls_list:
                url = str(u).strip()
                if url and url not in ref_urls:
                    ref_urls.append(url)
        ref_url_single = (hero.get("reference_url_hosted") or "").strip()
        if ref_url_single and ref_url_single not in ref_urls:
            ref_urls.insert(0, ref_url_single)

    ref_urls = filter_portrait_reference_urls(ref_urls)
    topic_id = manifest.get("topic_id") or "B01"
    ref_urls = rotate_reference_urls(ref_urls, topic_id)
    primary_ref = ref_urls[0] if ref_urls else ""

    if not primary_ref:
        print(
            "❌ COVER HERO BLOCKER: reference_url_hosted/reference_urls_hosted missing. Run excalibur_blog_hero_reference_url.py",
            file=sys.stderr,
        )
        return 1

    prompt = build_prompt(manifest, style, hero, types_catalog, design_code, root)
    scheme = resolve_cover_scheme(manifest, root)
    use_s7 = (scheme.get("scheme_id") or "").startswith("S7")
    if primary_ref:
        if use_s7:
            prompt += (
                f"\n\ni2i reference URL (lighting/style anchor only): {primary_ref}\n"
                "Do NOT copy Elena/blog-host face onto top-left cover — generic woman 45-55 only."
            )
        else:
            prompt += (
                f"\n\nHOST REFERENCE (face only): {primary_ref}\n"
                f"{yoga_master_outfit_prompt(topic_id)}\n"
                "One rotated portrait reference per article — do not reuse same outfit as previous covers."
            )
    prompt_path = article_dir / "cover" / "quad-mcp-prompt.txt"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    print(f"OK prompt={prompt_path}")

    if args.write_batch:
        batch = {
            "pipeline": "quad_canvas_1x_mcp",
            "reference_url_hosted": primary_ref,
            "reference_urls_hosted": ref_urls,
            "reference_mcp_input_urls": [primary_ref],
            "output_canvas": "cover/canvas-quad.png",
            "jobs": [
                {
                    "slot": "canvas_quad",
                    "tool": "gpt-image-2",
                    "note": "ONE call, ONE portrait ref (rotated by topic_id), then split",
                    "mcp_args": {
                        "prompt": prompt,
                        "input_urls": [primary_ref],
                        "aspect_ratio": "16:9",
                        "resolution": "2K",
                    },
                }
            ],
        }
        batch_path = article_dir / "cover" / "quad-mcp-batch.json"
        save_json(batch_path, batch)
        print(f"OK batch={batch_path} jobs=1 input_urls=1 ref={primary_ref}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
