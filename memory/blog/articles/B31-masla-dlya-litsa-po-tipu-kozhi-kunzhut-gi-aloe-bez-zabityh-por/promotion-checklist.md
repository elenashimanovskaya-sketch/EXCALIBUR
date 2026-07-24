# Promotion checklist — B31 masla-dlya-litsa-po-tipu-kozhi-kunzhut-gi-aloe-bez-zabityh-por

Дата публикации: 2026-07-24  
Draft URL (WP): [REDACTED]/?p=652  
Live URL (после publish): [REDACTED]/blog/masla-dlya-litsa-po-tipu-kozhi-kunzhut-gi-aloe-bez-zabityh-por/

Excalibur создаёт этот файл после `✅ ARTICLE OK` (до или после WP publish).

## Сразу после publish

- [ ] Открыть live URL — title, excerpt, featured image, FAQ
- [ ] View source — JSON-LD BlogPosting + FAQPage + HowTo (theme или plugin)
- [ ] Проверить internal links из статьи (200)
- [ ] Яндекс.Вебмастер / GSC — URL отправлен (если настроено)

## Соцсети / каналы (из conversion-tracking-map)

| Канал | Действие | Статус |
|-------|----------|--------|
| Telegram | Пост: hook + ссылка + 1 факт из статьи | ☐ |
| VK / Max | Адаптировать под ЦА | ☐ |
| Email / рассылка | Если есть в conversion map | ☐ |

## Snippet для Telegram (черновик)

```
Кунжут, гхи или алоэ на лицо — и утром «масляный блин»? Чаще виновата не банка, а несовпадение масла с типом кожи.

• Таблица Вата / Пита / Капха → кунжут, гхи или гель алоэ
• Патч-тест 48 часов перед смесью на всё лицо
• 3 рецепта смесей за 2 минуты + чеклист на 7 дней

Читать: [REDACTED]/blog/masla-dlya-litsa-po-tipu-kozhi-kunzhut-gi-aloe-bez-zabityh-por/
```

## Перелинковка

- [ ] Добавить ссылку на новый пост с главной blog section (если Aurora не auto)
- [ ] Обновить B30 (мимика) → relative `/blog/masla-dlya-litsa-.../` вместо legacy URL (если ещё absolute)
- [ ] После publish перезапустить interlinker — inbound по anchor «масло для лица», «кунжутное масло для лица»

## Метрики (7 дней)

- [ ] Metrika / GA4 — goal `blog_read` или из conversion map
- [ ] Позиция primary query «масла для лица аюрведа» (ручная проверка / Wordstat)

## Notes

Indexer: interlinker --apply — 0 автоматических вставок в B31 (anchor_variants B31 не встречаются в других статьях без уже существующего slug; outbound в B31 уже через absolute naturallift.store). Глобально применено 4 ссылки (B07, B08, B11, B30 → другие посты). llms.txt и llms-full.txt обновлены: 30 статей в `memory/blog/llms.txt`, B31 включена. После publish — перезапустить interlinker с `--site-base [REDACTED]` для inbound из постов про уход и гуаша.
