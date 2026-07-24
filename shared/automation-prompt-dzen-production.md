# Automation prompt — NaturalLift Дзен (production, draft phase)

Скопируй в Cursor Automation → Instructions.  
Расписание: 09:00 / 13:00 / 18:00 MSK (см. CLOUD-AUTOMATION.md).

```text
Ты работаешь в репозитории elenashimanovskaya-sketch/EXCALIBUR (Cursor Cloud).

Запусти полный пайплайн SEO/GEO статьи для naturallift.store → RSS /feed/dzen/ → Яндекс Дзен.
Оркестратор (Директор) — не выполняй роли worker сам.

ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_ALLOW_PUBLISH=yes — разрешает upload в WordPress.
ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_PUBLISH_DRAFT=yes — публикуем как ЧЕРНОВИК (не live), пока не отладим формат.
ОБЯЗАТЕЛЬНО: PUBLIC_SITE_URL=https://naturallift.store — publish на mayai.ru ЗАПРЕЩЁН (скрипт exit 4).
Никогда не передавай --site-base https://mayai.ru (legacy репо учителя).

Writer: Task(excalibur-blog-writer) — subagent **cursor-grok-4.5-medium** (.cursor/agents/excalibur-blog-writer.md).
НЕ inherit Director model для writer. НЕ excalibur_blog_gemini_writer.py без GEMINI_API_KEY.
Протоколы — HTML <table>, эталон B29. Запрещены title с «брейн-хаки» (0 запросов Wordstat).

0. Прочитай AGENTS.md и shared/agent-pipeline-pitfalls.md.
1. python3 scripts/excalibur_blog_doctor.py — preflight PASS.
2. python3 scripts/excalibur_blog_today.py — зафиксируй EXCALIBUR_RUN_DATE и EXCALIBUR_SUGGESTED_TOPIC_ID.
3. Сбрось .cursor/excalibur-blog-handoff.md: "# Excalibur BLOG — новая сессия".
4. Очисти .cursor/excalibur-blog-fragments/.
5. python3 scripts/excalibur_blog_research_start.py --topic-id <EXCALIBUR_SUGGESTED_TOPIC_ID или EXCALIBUR_TOPIC_ID>.
6. Task(excalibur-blog-research) → research-notes.md + wordstat gate.
7. Task(excalibur-blog-writer) → article.html + article.meta.json (~12k chars, голос Елены, таблицы).
8. python3 scripts/excalibur_blog_html_linter.py <article.html> — PASS до GEO QA.
9. Task(excalibur-blog-geo-qa) → PASS + QA JSON.
10. ПАРАЛЛЕЛЬНО Task(excalibur-blog-cover) + Task(excalibur-blog-schema).
   Cover SCRIPT GATE: hero_reference_url → quad_manifest --merge → cover_quad_prompt --write-batch
   → ONE MCP gpt-image-2 только jobs[0].mcp_args из quad-mcp-batch.json → quad_apply --inject-html (PASS).
   S7: NO Cyrillic on cover.png. Inline: avoid comparison_table_ui gibberish — infographic_card/workflow.
11. Task(excalibur-blog-indexer).
12. Task(excalibur-blog-publish) — WP upload с --draft (или env EXCALIBUR_BLOG_PUBLISH_DRAFT=yes), обнови shared/published-articles.md.

Fallback: Task(generalPurpose) per role + .cursor/agents/<role>.md + .cursor/skills/<skill>/SKILL.md.

Запрещено:
- single-agent pipeline;
- cover/schema до GEO QA PASS;
- live publish без явного EXCALIBUR_BLOG_PUBLISH_DRAFT=no;
- секреты в handoff/commit/log;
- «плоские» протоколы одним абзацем вместо <table>.

Финальный ответ:
- topic_id, article_dir;
- QA verdict;
- draft URL на naturallift.store (post_status=draft);
- напоминание: в Дзен уйдёт только после publish → проверка вручную.
```

## Cursor Dashboard — Secrets (обязательно)

| Secret | Значение |
|--------|----------|
| `EXCALIBUR_BLOG_ALLOW_PUBLISH` | `yes` |
| `EXCALIBUR_BLOG_PUBLISH_DRAFT` | `yes` (фаза отладки; потом `no` для live) |
| `PUBLIC_SITE_URL` | `https://naturallift.store` |
| `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` | из teya.env.local / site.inv |
| `YANDEX_CLOUD_FOLDER_ID`, `YANDEX_CLOUD_OAUTH_TOKEN` | Wordstat gate |
| `NATURALLIFT_TELEGRAM_URL` | `https://t.me/silver_cream` |
| `NATURALLIFT_TELEGRAM_CHANNEL_TITLE` | `Елена Шим/Фейс йога и Омоложение лица` |

## GitHub + Cursor Cloud

1. [cursor.com](https://cursor.com) → Settings → Integrations → **GitHub App** → доступ к `EXCALIBUR` и `naturallift`.
2. Cloud Agents → Secrets — таблица выше.
3. Automations → Create → Schedule → cron из CLOUD-AUTOMATION.md → prompt выше.

## naturallift-site

Тема WP, Dzen RSS plugin, реестр B30+ — репозиторий `elenashimanovskaya-sketch/naturallift`.
Контент-план синхронизируется через `shared/articles-registry.md` и `teya-memory/.../12-articles-registry.md`.
