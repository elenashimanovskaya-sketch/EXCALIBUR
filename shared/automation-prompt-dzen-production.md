# Automation prompt — NaturalLift Дзен (production)

Скопируй в Cursor Automation → Instructions.  
Расписание: 09:00 / 13:00 / 18:00 MSK (см. CLOUD-AUTOMATION.md).

```text
Ты работаешь в репозитории elenashimanovskaya-sketch/EXCALIBUR (Cursor Cloud).

Запусти полный пайплайн SEO/GEO статьи для naturallift.store → RSS /feed/dzen/ → Яндекс Дзен.
Оркестратор (Директор) — не выполняй роли worker сам.

ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_ALLOW_PUBLISH=yes — публикуем live в WordPress сразу после QA PASS.
ОБЯЗАТЕЛЬНО: PUBLIC_SITE_URL=https://naturallift.store — publish на mayai.ru ЗАПРЕЩЁН (скрипт exit 4).
Никогда не передавай --site-base https://mayai.ru (legacy репо учителя).

0. Прочитай AGENTS.md и shared/agent-pipeline-pitfalls.md.
1. python3 scripts/excalibur_blog_doctor.py — preflight PASS.
2. python3 scripts/excalibur_blog_today.py — зафиксируй EXCALIBUR_RUN_DATE и EXCALIBUR_SUGGESTED_TOPIC_ID.
3. Сбрось .cursor/excalibur-blog-handoff.md: "# Excalibur BLOG — новая сессия".
4. Очисти .cursor/excalibur-blog-fragments/.
5. python3 scripts/excalibur_blog_research_start.py --topic-id <EXCALIBUR_SUGGESTED_TOPIC_ID или EXCALIBUR_TOPIC_ID>.
6. Task(excalibur-blog-research) → research-notes.md + wordstat gate.
7. Task(excalibur-blog-writer) → article.html + article.meta.json (~12k chars, голос Елены).
8. Task(excalibur-blog-geo-qa) → PASS + QA JSON.
9. ПАРАЛЛЕЛЬНО Task(excalibur-blog-cover) + Task(excalibur-blog-schema).
   Cover: MCP gpt-image-2 quad → split → inject figures.
10. Task(excalibur-blog-indexer).
11. Task(excalibur-blog-publish) — live publish в WP, обнови shared/published-articles.md и articles-registry.

Fallback: Task(generalPurpose) per role + .cursor/agents/<role>.md + .cursor/skills/<skill>/SKILL.md.

Запрещено:
- single-agent pipeline;
- cover/schema до GEO QA PASS;
- publish:no / draft (production run);
- секреты в handoff/commit/log.

Финальный ответ:
- topic_id, article_dir;
- QA verdict;
- publish URL на naturallift.store;
- напоминание: Дзен подхватит из /feed/dzen/ в течение ~1 ч.
```

## Cursor Dashboard — Secrets (обязательно)

| Secret | Значение |
|--------|----------|
| `EXCALIBUR_BLOG_ALLOW_PUBLISH` | `yes` |
| `PUBLIC_SITE_URL` | `https://naturallift.store` |
| `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` | из teya.env.local / site.inv |
| `YANDEX_CLOUD_FOLDER_ID`, `YANDEX_CLOUD_OAUTH_TOKEN` | Wordstat gate |

## GitHub + Cursor Cloud

1. [cursor.com](https://cursor.com) → Settings → Integrations → **GitHub App** → доступ к `EXCALIBUR` и `naturallift`.
2. Cloud Agents → Secrets — таблица выше.
3. Automations → Create → Schedule → cron из CLOUD-AUTOMATION.md → prompt выше.

## naturallift-site

Тема WP, Dzen RSS plugin, реестр B30+ — репозиторий `elenashimanovskaya-sketch/naturallift`.
Контент-план синхронизируется через `shared/articles-registry.md` и `teya-memory/.../12-articles-registry.md`.
