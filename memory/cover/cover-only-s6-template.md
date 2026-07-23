# Cover-only S6 (YouTube split) — legacy B07–B14

**С B15:** схема **S7_problem_hero** — см. `memory/cover/cover-problem-hero-template.md` (герой + проблема, **без текста** на картинке).

## Пайплайн на статью

1. Wordstat MCP (`wordstat_get_top_requests`) по `primary_query` → hook из топ-1/2 фразы.
2. `cover/cover-only-prompt.txt` — один кадр 16:9, featured image.
3. MCP `gpt-image-2`, `input_urls`: hero ref, `aspect_ratio` 16:9, `resolution` 2K.
4. Сохранить как `cover/cover.png` → publish draft (`excalibur_blog_wp_publish.py --draft`).
5. Quad (4 панели + inline) — **позже**, когда нужны inline; cover S6 не дублировать в quad collage.

## Фиксированный каркас S6

- LEFT 42%: типографика, тёмный blur фон, без фото.
- Line 1 fuchsia #e91e8c: глагол («КАК УБРАТЬ» / «КАК СНЯТЬ»).
- Line 2 white: объект (зона лица/шеи).
- Brushstroke: уточнение из Wordstat («без ботокса», «без филлеров», «дома»).
- Caption: «7 минут дома» / «5 минут дома».
- RIGHT 58%: Елена, **один приём**, outfit **уникальный** на статью.
- Запрет: до/после, виски, sticky-note коллаж.

## Очередь B13–B16

| topic | hook | pose | outfit |
|-------|------|------|--------|
| B13 | КАК УБРАТЬ / МОРЩИНЫ НА ЛБУ / без ботокса | ладонь на лоб | белый топ |
| B14 | КАК УБРАТЬ / МЕЖБРОВНУЮ СКЛАДКУ / упражнения | пальцы между бровей | серо-лиловый |
| B15 | КАК УБРАТЬ / КИСЕТНЫЕ МОРЩИНЫ / без филлеров | пальцы у верхней губы | терракотовый |
| B16 | КАК УБРАТЬ / КОЛЬЦА ВЕНЕРЫ / на шее | рука на боковой шее | cobalt top |

## До/после (только S4, редко)

Клиентка 45–55, **не** Елена. До — проблема видна, после — тот же ракурс, улучшение очевидно.
