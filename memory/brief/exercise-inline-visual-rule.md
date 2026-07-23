# Exercise inline visual — правило cover pipeline

Обновлено: 2026-07-07. Эталон: B18 «Ковш» (Елена пошагово на фото).

## Когда

Статья про **упражнение** (how_to, H1/запрос с «упражнен», «техника», «ковш», «рамка», H2 «…пошагово»).

## Inline-панель

- `visual_type`: **exercise_steps_host**
- Слот: inline на H2 с пошаговой техникой (обычно «Техника … пошагово»)
- Елена **на каждом шаге** делает движение — как домашний урок, «снимает себя»
- 4-5 шагов, подписи: Подготовка, Положение рук, Движение, Фиксация, Повторение
- Sticky note: «3-5 минут ежедневно»
- Розовые стрелки направления, torn paper, fuchsia palette

## Скрипты

- `memory/cover/inline-visual-types.json` → тип `exercise_steps_host`
- `scripts/excalibur_blog_quad_manifest.py` → `is_exercise_article`, `exercise_h2_slot_index`
- `scripts/excalibur_blog_cover_quad_prompt.py` → host face REQUIRED на exercise-панели

## meta (опционально)

`article.meta.json`: `"has_exercise": true` — явный флаг.
