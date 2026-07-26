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
| `EXCALIBUR_TOPIC_ID` | `B33` (следующая queued после B32) | *(пусто — today.py выберет P0)* |
| `PUBLIC_SITE_URL` | `https://naturallift.store` | то же |
| `FTP_*` | из site.env.local | то же |
| Wordstat | `YANDEX_CLOUD_*` | то же |
| Telegram | `NATURALLIFT_TELEGRAM_URL`, `NATURALLIFT_TELEGRAM_CHANNEL_TITLE` | то же |

**Telegram — значения (не выдумывать):**

| Secret | Значение |
|--------|----------|
| `NATURALLIFT_TELEGRAM_URL` | `https://t.me/silver_cream` |
| `NATURALLIFT_TELEGRAM_CHANNEL_TITLE` | `Елена Шим/Фейс йога и Омоложение лица` |

«Silver Cream» — **косметика**, не название канала. В финале статьи **запрещено** подставлять Silver Cream как title канала.

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
ОБЯЗАТЕЛЬНО: EXCALIBUR_TOPIC_ID из Secrets (напр. B33) — не бери случайный P0 без env

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
   TELEGRAM GATE (writer, BLOCKER до publish):
     Финал article.html (после FAQ) — ТОЛЬКО из Secrets env:
       URL = NATURALLIFT_TELEGRAM_URL (= https://t.me/silver_cream)
       title = NATURALLIFT_TELEGRAM_CHANNEL_TITLE (= «Елена Шим/Фейс йога и Омоложение лица»)
     Шаблон: <p>🔥 <a href="{URL}">Мой Telegram-канал «{title}»</a></p> + blockquote ❓
     ЗАПРЕЩЕНО в title канала: «Silver Cream», silver_cream как название, выдуманные имена.
     Перед publish: если в финальной строке Telegram есть «Silver Cream» → FAIL, вернуть writer.
8. python3 scripts/excalibur_blog_html_linter.py <article.html> — PASS
9. Task(excalibur-blog-geo-qa) → PASS
10. ПАРАЛЛЕЛЬНО Task(excalibur-blog-cover) + Task(excalibur-blog-schema)
    Cover SCRIPT GATE (BLOCKER — cover без скриптов = incident):
      a) python3 scripts/excalibur_blog_hero_reference_url.py
      b) python3 scripts/excalibur_blog_quad_manifest.py --article-dir <dir> --merge
      c) правка cover/quad-manifest.json: cover_problem + scene_hint; inline types
         prefer infographic_card / checklist_board / workflow_diagram
         НЕ comparison_table_ui (латиница на PNG)
      d) python3 scripts/excalibur_blog_cover_quad_prompt.py --article-dir <dir> --write-batch
      e) ONE CallMcpTool user-mcp-kv gpt-image-2 — ТОЛЬКО jobs[0].mcp_args из cover/quad-mcp-batch.json
         (prompt, input_urls, aspect_ratio, resolution — из batch, не импровизировать)
      f) python3 scripts/excalibur_blog_quad_apply.py --article-dir <dir> --url <canvas_url> --inject-html
      g) cover/quad-split-report.json → status PASS; html_inject без FAIL
    S7: NO Cyrillic on cover.png. Inline: ALL text Cyrillic ONLY.
    ЗАПРЕЩЕНО: freestyle MCP; 4 отдельных MCP; пропуск quad-mcp-batch.json.
11. Task(excalibur-blog-indexer)
12. Task(excalibur-blog-publish) — draft (--draft или EXCALIBUR_BLOG_PUBLISH_DRAFT=yes)

Pre-finish checklist (Director, все PASS):
  [ ] Telegram финал = «Елена Шим/Фейс йога и Омоложение лица», НЕ Silver Cream
  [ ] cover/quad-mcp-batch.json есть; MCP = jobs[0].mcp_args
  [ ] cover/quad-split-report.json status=PASS
  [ ] 3 inline-quad figure в article.html

Запрещено: single-agent pipeline; cover до QA; live publish; mayai.ru; «плоские» таблицы в <p>; «брейн-хаки» в title; Silver Cream как название TG-канала.

Финал: topic_id, article_dir, QA verdict, post_status, ссылки (см. ниже), writer_model=cursor-grok-4.5-medium.
```

## Черновик vs опубликовано (URLs)

| Статус | Что видит гость | Где смотреть |
|--------|-----------------|--------------|
| **draft** (`EXCALIBUR_BLOG_PUBLISH_DRAFT=yes`) | `?p=ID` **не работает** без входа | WP Admin → Записи → Черновики → Просмотр |
| **preview** | `?p=ID&preview=true` | Только если залогинена в WP |
| **publish** (`EXCALIBUR_BLOG_PUBLISH_DRAFT=no`) | `https://naturallift.store/<slug>/` | Публичная ссылка + RSS `/feed/dzen/` |

После publish скрипт пишет в лог: `public_url=...` (не путать с `?p=652`).

---

## Как запустить тест (следующая статья B33)

1. Cursor → **Automations** → открой `naturallift-dzen-test` (или Create).
2. **Secrets:** `EXCALIBUR_TOPIC_ID=B33`, оба `NATURALLIFT_TELEGRAM_*` (см. таблицу выше).
3. Вставь Instructions из блока выше (если менялся файл — перекопируй целиком).
4. **Save** → **Run now**.
5. Run log: writer = **Grok 4.5 Medium**; cover = quad-mcp-batch + quad-split PASS.
6. WP → **Записи → Черновики** — preview; проверь TG-финал и 3 inline-картинки (кириллица).

Старую `naturallift-dzen-test-2135` с текстом «Брейн-хаки B30 live» — **отключи** или перезапиши prompt.
