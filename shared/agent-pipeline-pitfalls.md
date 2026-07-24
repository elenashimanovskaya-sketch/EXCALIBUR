# Excalibur BLOG — типичные сбои пайплайна

## Cloud / Task

- Cloud не принимает `excalibur-blog-*` как Task types → fallback `Task(generalPurpose)` + `.cursor/agents/<role>.md` + skill path.
- Parent-agent сам пишет статью вместо `excalibur-blog-writer` → **блокер**, перезапуск writer Task.
- Объединение cover+schema в один Task → запрещено; только параллельные отдельные Task.

## Handoff / fragments

- Параллельные `cover` и `schema` пишут в `.cursor/excalibur-blog-fragments/cover.md` и `schema.md`, директор переносит в handoff.
- Не коммитить `.cursor/excalibur-blog-handoff.md` и fragments.

## Research / дата

- Перед пайплайном: `python3 scripts/excalibur_blog_today.py` и `python3 scripts/excalibur_blog_research_start.py --topic-id …`.
- Если `EXCALIBUR_RUN_DATE` нет в выводе today.py — старая ветка/код, **блокер**.

## Publish

- `EXCALIBUR_BLOG_ALLOW_PUBLISH=yes` только в Cloud Secrets, не в git.
- Publish без обновления `shared/published-articles.md` → следующий прогон может дублировать slug.

## QA

- Шаг cover||schema **только после** GEO QA PASS.
- MCP URLs в production article.html → fix перед publish.

## Cover / quad

- Cover **без скриптов** (`quad_manifest` → `cover_quad_prompt` → `quad_apply`) → мусорные PNG (кириллица на cover, gibberish-таблицы). **BLOCKER**.
- MCP prompt **только** из `cover/quad-mcp-batch.json` → `jobs[0].mcp_args`.
- Default cover: **S7_problem_hero** — editorial photo, **без текста** на cover; hook только на сайте над фото.
- `comparison_table_ui` в inline quad часто ломает кириллицу → prefer `infographic_card` / `workflow_diagram`; таблицы — в HTML статьи.
