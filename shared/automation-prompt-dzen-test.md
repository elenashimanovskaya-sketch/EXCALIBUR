# Automation prompt — TEST run (NaturalLift Дзен)

Создай **отдельную** automation (не production 09/13/18). Имя: `naturallift-dzen-test`.

## Dashboard

| Поле | Значение |
|------|----------|
| Repository | `elenashimanovskaya-sketch/EXCALIBUR` |
| Branch | `master` |
| Model (Director) | **Composer 2.5** (Cloud; Grok slug недоступен) |
| Trigger | Manual / Run now (или cron `0 12 * * *` для разового слота) |

## Secrets (минимум)

| Secret | TEST | Production |
|--------|------|------------|
| `EXCALIBUR_BLOG_ALLOW_PUBLISH` | `yes` | `yes` |
| `EXCALIBUR_BLOG_PUBLISH_DRAFT` | `yes` | `no` (когда формат ок) |
| `EXCALIBUR_TOPIC_ID` | `B34` (следующая queued после B33) | *(пусто — today.py выберет P0)* |
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

Writer: subagent `excalibur-blog-writer` с **`model: inherit`** — та же модель, что Director (Composer 2.5). Slug `cursor-grok-4.5-medium` в Cloud **не использовать**.

**После правки этого файла (или agents/skills/scripts):** commit → `git push origin master` без паузы. Cloud читает GitHub, не локальный диск. Instructions в Dashboard UI — копипаст вручную; файл в репо — источник правды для агента и бэкап.

---

## Instructions (скопировать целиком)

```text
Ты работаешь в репозитории elenashimanovskaya-sketch/EXCALIBUR (Cursor Cloud).

ТЕСТОВЫЙ ЗАПУСК пайплайна SEO/GEO → naturallift.store → /feed/dzen/.
Оркестратор (Директор) — не выполняй роли worker сам. Каждая роль = Task(...).
Если Cloud не принимает excalibur-blog-* как Task types → Task(generalPurpose) + .cursor/agents/<role>.md (см. AGENTS.md).

ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_ALLOW_PUBLISH=yes
ОБЯЗАТЕЛЬНО: EXCALIBUR_BLOG_PUBLISH_DRAFT=yes — только черновик WP, не live
ОБЯЗАТЕЛЬНО: PUBLIC_SITE_URL=https://naturallift.store — mayai.ru ЗАПРЕЩЁН (exit 4)
ОБЯЗАТЕЛЬНО: EXCALIBUR_TOPIC_ID из Secrets (напр. B34) — не бери случайный P0 без env
ОБЯЗАТЕЛЬНО: MCP-KV подключён в Cloud Integrations (gpt-image-2 + wordstat)

Writer: Task(excalibur-blog-writer) — subagent model: inherit (модель Director = Composer 2.5 в Automation settings).
НЕ cursor-grok-4.5-medium — slug недоступен в Cloud. НЕ excalibur_blog_gemini_writer.py без GEMINI_API_KEY.
Пиши по memory/brief/elena-dzen-writer-prompt.md: короткие абзацы, HTML <table> для протоколов, <ol> для чеклистов. Эталон B29.

0. AGENTS.md + shared/agent-pipeline-pitfalls.md + shared/pipeline-task-map.md
1. python3 scripts/excalibur_blog_doctor.py — PASS
2. python3 scripts/excalibur_blog_today.py — дата; topic = EXCALIBUR_TOPIC_ID из env
3. .cursor/excalibur-blog-handoff.md → "# Excalibur BLOG — новая сессия"
4. Очисти .cursor/excalibur-blog-fragments/
5. python3 scripts/excalibur_blog_research_start.py --topic-id $EXCALIBUR_TOPIC_ID
6. Task(excalibur-blog-research)
7. Task(excalibur-blog-writer) → article.html + article.meta.json (~12k, таблицы)
   Writer GATE:
     — НЕ вставлять <figure class="inline-quad"> и cover/*.png (только cover-агент)
     — 3× <h2> до FAQ (текст = h2_anchor в quad-manifest); <!-- scheme_1 --> <!-- scheme_2 -->
     — python3 scripts/excalibur_blog_article_format.py <article_dir>/article.html --write
   TELEGRAM GATE (writer, BLOCKER до publish):
     Финал article.html (после FAQ) — ТОЛЬКО из Secrets env:
       URL = NATURALLIFT_TELEGRAM_URL (= https://t.me/silver_cream)
       title = NATURALLIFT_TELEGRAM_CHANNEL_TITLE (= «Елена Шим/Фейс йога и Омоложение лица»)
     Шаблон: <p>🔥 <a href="{URL}">Мой Telegram-канал «{title}»</a></p> + blockquote ❓
     ЗАПРЕЩЕНО: «Silver Cream» как название канала; href="/" или выдуманный URL
     Перед publish: если в финале Telegram есть «Silver Cream» → FAIL, вернуть writer
8. python3 scripts/excalibur_blog_html_linter.py <article_dir>/article.html — PASS
9. Task(excalibur-blog-geo-qa) → PASS (cover||schema только после PASS)
10. ПАРАЛЛЕЛЬНО Task(excalibur-blog-cover) + Task(excalibur-blog-schema)
    Cover-агент выполняет SCRIPT GATE (BLOCKER):
      a) python3 scripts/excalibur_blog_hero_reference_url.py  (без --article-dir)
      b) python3 scripts/excalibur_blog_quad_manifest.py --article-dir <dir> --merge
      c) правка cover/quad-manifest.json: cover_problem, scene_hint; style из topics cover_style
      d) python3 scripts/excalibur_blog_cover_quad_prompt.py --article-dir <dir> --write-batch
      e) ONE CallMcpTool user-mcp-kv gpt-image-2 — ТОЛЬКО jobs[0].mcp_args из cover/quad-mcp-batch.json
         MCP tool = gpt-image-2 ONLY. Нет GPT 5.5 / nano_banana / grok-imagine для cover.
      f) python3 scripts/excalibur_blog_quad_apply.py --article-dir <dir> --url <canvas_url> --inject-html
      g) cover/quad-split-report.json → status PASS; html_inject без FAIL
    S7 cover: NO Cyrillic на cover.png.
    INLINE TEXT GATE (на PNG):
      — только иконки + цифры + max 2 слова кириллицей на элемент
      — prefer infographic_card / workflow_diagram
      — ЗАПРЕЩЕНО: comparison_table_ui; checklist_board с длинным списком слов
      — длинные таблицы и чеклисты — только в HTML <table>/<ol> статьи
    ЗАПРЕЩЕНО: freestyle MCP prompt; 4 отдельных MCP; пропуск quad-mcp-batch.json
    Fragment: .cursor/excalibur-blog-fragments/cover.md (=== EXCALIBUR BLOG COVER ===)
11. Task(excalibur-blog-indexer)
12. Task(excalibur-blog-publish) — draft (--draft или EXCALIBUR_BLOG_PUBLISH_DRAFT=yes)

Pre-finish checklist (Director, все PASS):
  [ ] Telegram финал = «Елена Шим/Фейс йога и Омоложение лица», НЕ Silver Cream
  [ ] cover/quad-mcp-batch.json + quad-mcp-result.json; MCP = jobs[0].mcp_args
  [ ] cover/quad-split-report.json status=PASS; 3 inline-quad figure
  [ ] post_status=draft; preview через WP Admin (?p=ID гостям не виден)

Запрещено: single-agent pipeline; cover до QA; live publish; mayai.ru; «плоские» таблицы в <p>; «брейн-хаки» в title; Silver Cream как название TG-канала.

Финал: topic_id, article_dir, QA verdict, post_status=draft, wp_post_id, admin preview hint, writer_model=inherit (Director=Composer 2.5).
```

## Черновик vs опубликовано (URLs)

| Статус | Что видит гость | Где смотреть |
|--------|-----------------|--------------|
| **draft** (`EXCALIBUR_BLOG_PUBLISH_DRAFT=yes`) | `?p=ID` **не работает** без входа | WP Admin → Записи → Черновики → Просмотр |
| **preview** | `?p=ID&preview=true` | Только если залогинена в WP |
| **publish** (`EXCALIBUR_BLOG_PUBLISH_DRAFT=no`) | `https://naturallift.store/<slug>/` | Публичная ссылка + RSS `/feed/dzen/` |

После publish скрипт пишет в лог: `public_url=...` (не путать с `?p=652`).

---

## Как запустить тест (следующая статья B34)

1. Cursor → **Automations** → открой `naturallift-dzen-test` (или Create).
2. **Model (Director):** Composer 2.5 — обязательно для Cloud.
3. **Secrets:** `EXCALIBUR_TOPIC_ID=B34`, оба `NATURALLIFT_TELEGRAM_*`, MCP-KV, FTP, Wordstat (см. таблицы выше).
4. Вставь Instructions из блока выше (если менялся файл — перекопируй целиком).
5. **Save** → **Run now**.
6. Run log: writer = inherit → Composer 2.5; cover = quad-mcp-batch + quad-split PASS.
7. WP → **Записи → Черновики** — preview; проверь TG-финал и 3 inline-картинки (кириллица).

Старую `naturallift-dzen-test-2135` с текстом «Брейн-хаки B30 live» — **отключи** или перезапиши prompt.
