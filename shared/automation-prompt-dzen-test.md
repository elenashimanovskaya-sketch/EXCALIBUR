# Automation prompt — TEST run (NaturalLift Дзен)

Создай **отдельную** automation (не production 09/13/18). Имя: `naturallift-dzen-test`.

## Dashboard

| Поле | Значение |
|------|----------|
| Repository | `elenashimanovskaya-sketch/EXCALIBUR` |
| Branch | `master` |
| Model (Director) | Composer 2.5 или Grok — на выбор |
| Trigger | Manual / Run now (или cron `0 12 * * *` для разового слота) |

## Secrets (минимум)

| Secret | TEST | Production |
|--------|------|------------|
| `EXCALIBUR_BLOG_ALLOW_PUBLISH` | `yes` | `yes` |
| `EXCALIBUR_BLOG_PUBLISH_DRAFT` | `yes` | `no` (когда формат ок) |
| `EXCALIBUR_TOPIC_ID` | `B31` (или другая queued) | *(пусто — today.py выберет P0)* |
| `PUBLIC_SITE_URL` | `https://naturallift.store` | то же |
| `FTP_*` | из site.env.local | то же |
| Wordstat | `YANDEX_CLOUD_*` | то же |

Writer **не** из Director model: subagent `excalibur-blog-writer` в репо с `model: cursor-grok-4.5-medium`.

---

## Instructions (скопировать целиком)

```text
Ты работаешь в репозитории elenashimanovskaya-sketch/EXCALIBUR (Cursor Cloud).

ТЕСТОВЫЙ ЗАПУСК пайплайна SEO/GEO → naturallift.store → /feed/dzen/.
Оркестратор (Директор) — не выполняй роли worker сам.

ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_ALLOW_PUBLISH=yes
ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_PUBLISH_DRAFT=yes — только черновик WP, не live
ОБЯЗАТЕЛЬНО: PUBLIC_SITE_URL=https://naturallift.store — mayai.ru ЗАПРЕЩЁН (exit 4)
ОБЯЗАТЕЛЬНО: EXCALIBUR_TOPIC_ID из Secrets (напр. B31) — не бери случайный P0 без env

Writer: Task(excalibur-blog-writer) — модель subagent cursor-grok-4.5-medium (frontmatter .cursor/agents/excalibur-blog-writer.md).
НЕ excalibur_blog_gemini_writer.py. НЕ inherit model Director для writer.
Пиши по memory/brief/elena-dzen-writer-prompt.md: короткие абзацы, HTML <table> для протоколов, <ol> для чеклистов. Эталон B29.

0. AGENTS.md + shared/agent-pipeline-pitfalls.md
1. python3 scripts/excalibur_blog_doctor.py — PASS
2. python3 scripts/excalibur_blog_today.py — дата; topic = EXCALIBUR_TOPIC_ID из env
3. .cursor/excalibur-blog-handoff.md → "# Excalibur BLOG — новая сессия"
4. Очисти .cursor/excalibur-blog-fragments/
5. python3 scripts/excalibur_blog_research_start.py --topic-id $EXCALIBUR_TOPIC_ID
6. Task(excalibur-blog-research)
7. Task(excalibur-blog-writer) → article.html + meta (~12k, таблицы)
8. python3 scripts/excalibur_blog_html_linter.py <article.html> — PASS
9. Task(excalibur-blog-geo-qa) → PASS
10. ПАРАЛЛЕЛЬНО Task(excalibur-blog-cover) + Task(excalibur-blog-schema)
    Cover: ONE MCP gpt-image-2 quad → split → inject
11. Task(excalibur-blog-indexer)
12. Task(excalibur-blog-publish) — draft (--draft или EXCALIBUR_BLOG_PUBLISH_DRAFT=yes)

Запрещено: single-agent pipeline; cover до QA; live publish; mayai.ru; «плоские» таблицы в <p>; «брейн-хаки» в title.

Финал: topic_id, article_dir, QA verdict, draft URL naturallift.store, writer_model=cursor-grok-4.5-medium.
```

## Как запустить тест

1. Cursor → **Automations** → **Create** (или дублируй старую test-2135 и замени Instructions).
2. Вставь prompt выше, проверь Secrets.
3. **Save** → **Run now** (или Manual trigger).
4. Смотри run log: writer subagent должен показать **Grok 4.5 Medium**.
5. WP → **Записи → Черновики** — новая статья B31.

Старую `naturallift-dzen-test-2135` с текстом «Брейн-хаки B30 live» — **отключи** или перезапиши prompt.
