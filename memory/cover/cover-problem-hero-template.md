# Cover S7 — герой + проблема (без текста на картинке)

**Все статьи** (с 2026-07-04): top-left cover = **S7_problem_hero** по умолчанию. Legacy S1–S6 только если явно в `meta.cover_scheme_id`.

Заголовок на сайте **над** фото → на обложке **нет** кириллицы. Текст, UI, чеклисты — **только 3 inline-панели** quad.

## Правило по типу темы

| Тип | Cover (top-left) |
|-----|------------------|
| Фейс-йога, упражнения, массаж лица | Split до/после в одном кадре: слева проблема, справа та же женщина мягче |
| Морщины, линии, заломы, шея, губы | Generic woman 45-55 + зона проблемы; split или жест/стрелки без букв |
| Любая тема | Нейроперсонаж, **не Елена**, без текста на cover |

Шаблон промпта: `memory/cover/cover-only-universal-s7.txt`

С **B15** главная обложка (top-left quad + featured) — схема **S7_problem_hero**.

Inline-панели (3 схемы справа/снизу) — **без изменений**, как сейчас.

## Варианты (ротация по номеру темы)

| variant | Когда | Визуал |
|---------|-------|--------|
| closeup_problem_gesture | B15, B18… | Крупный план зоны + палец/ладонь, **проблема видна** (линии/залом), тонкие жёлтые стрелки без букв |
| split_subtle_before_after | B16, B19… | **До/после в одном кадре:** слева проблема чётко видна, справа та же женщина/ракурс — мягче |
| ghost_correct_overlay | B17, B20… | Основной кадр «правильно», полупрозрачный «неправильно» + красный X без слов |

## Герой

- **По умолчанию:** женщина 45-55, relatable, не «пластик» — **не обязательно Елена**.
- `host_rule: use_elena_reference` в manifest — только если нужен эталон с reference.

## Правило читаемости проблемы (с B15+, на будущее)

- На обложке **сразу видно**, о чём статья: проблемная зона не retouch «до гладкости».
- **Кисетные морщины** → вертикальные линии над верхней губой видны; ideal — split до/после (слева линии глубже + жёлтые стрелки, справа мягче).
- **Залом/морщины/мешки** → соответствующий дефект читается в thumbnail, не только жест рукой.
- До/после — **одна женщина, один ракурс**, без «другой модели» и без текста на картинке.

## B15 — готовый промпт cover-only (16:9 featured)

```text
Editorial wellness photograph, single 16:9 frame, clean neutral beige studio background #d4c4b0, soft natural window light.

Subject: Russian woman 45-55, relatable natural skin with visible vertical perioral lines above upper lip (kishet wrinkles), NOT retouched to perfection.

Composition variant split_subtle_before_after inside one frame: left half slightly deeper lip lines, right half same woman same angle but softer relaxed expression, subtle improvement NOT plastic surgery ad.

Alternative: close-up mouth/nose area, fingertip gently touching upper lip border showing problem zone. Optional thin pale yellow curved arrows indicating gentle massage direction — NO text, NO letters.

Do NOT use blog host Elena from reference unless explicitly requested. Generic mature woman.

NO Cyrillic, NO Latin headlines, NO logos, NO sticky notes, NO meme collage, NO syringe, NO clinic.

Premium human editorial photo, shallow depth of field, warm skin tones.
```

MCP: `gpt-image-2`, `aspect_ratio` 16:9, `resolution` 2K. `input_urls` опционально (для S7 generic woman reference не обязателен; для quad batch hero refs остаются для совместимости пайплайна).

## Quad: только top-left меняется

Скрипт `excalibur_blog_cover_quad_prompt.py` для `cover_scheme_id: S7_problem_hero` подставляет блок `cover_problem_hero_prompt_block`. Top-right / bottom-left / bottom-right — **старые inline промпты без изменений**.

## Команды (B15)

```bash
python scripts/excalibur_blog_quad_manifest.py --article-dir memory/blog/articles/B15-... --merge
python scripts/excalibur_blog_cover_quad_prompt.py --article-dir memory/blog/articles/B15-... --write-batch
# ONE MCP gpt-image-2 → quad_apply → split → inject
```
