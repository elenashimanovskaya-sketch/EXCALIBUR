---
name: excalibur-research
description: Excalibur BLOG Research — topic research перед статьёй (SERP, факты, угол). Gate до article.html.
---

# Excalibur BLOG — Research

## Когда

**Шаг 0 (скрипт, обязательно):** перед любым research — зафиксировать дату и собрать свежий SERP.

```bash
python scripts/excalibur_blog_research_start.py --topic-id B01
```

Wordstat включён **по умолчанию** (`--no-wordstat` только для отладки без API-ключей).

Создаёт в папке статьи:

- `research-context.json` — сегодняшняя дата, год, окно свежести, тема, список поисковых запросов
- `research-serp.json` — результаты web-поиска по запросам с `{year}` и текущим месяцем

`--dry-run` — только дата и запросы без HTTP.

Перед **каждой** статьей затем пиши `research-notes.md`. Без него нельзя утверждать цены, даты, версии, статистику.

## Вход

- Карточка из `memory/topics/blog-topics.md`
- `memory/brief/site-brief.md`, `fact-bank.md`
- `shared/quality-blog.md`
- MCP сервер `user-mcp-kv` — инструменты `wordstat_*` (если SSL ok)
- **Локально (надёжно):** `python3 scripts/excalibur_wordstat.py` → Search API v2
- Креды: `YANDEX_CLOUD_API_KEY` + `YANDEX_CLOUD_FOLDER_ID` в `memory/site.env.local`

## Обязательное использование Wordstat

1. **Сначала локальный скрипт** (обход SSL-бага MCP):
```bash
python3 scripts/excalibur_blog_research_start.py --topic-id B13 --wordstat
# или
python3 scripts/excalibur_wordstat.py --phrase "морщины на лбу без ботокса" --markdown --out research-wordstat.json
```
2. **MCP fallback:** `wordstat_get_top_requests` на `user-mcp-kv` — только если локальный скрипт недоступен и MCP не падает с SSL.
3. В `research-notes.md` — таблица: Фраза | Показы/мес из `research-wordstat.json` или MCP.
4. Если нет кредов — `⚠️ WORDSTAT BLOCKER`, не выдумывать частотности.

## Gate перед publish

```bash
python scripts/excalibur_blog_wordstat_gate.py --article-dir memory/blog/articles/<topic_id>-<slug>
```

`excalibur_blog_wp_publish.py` вызывает gate автоматически (`--skip-wordstat-gate` только аварийно).

## Quad + publish (автоматически после статьи)

**Политика:** не ждать команды пользователя — после canvas от MCP сразу live publish.

```bash
python scripts/excalibur_blog_quad_publish.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --canvas-url <mcp_url> \
  --skip-manifest
```

По умолчанию: `post_status=publish`. Opt-out: `--no-publish` или `--draft`.

**BLOCK если:** primary_query &lt; 200/мес или title hook (до `:`) &lt; 200/мес — как B20 «сутулость и лицо»=13.

## Устаревшее (не использовать OAuth v1)

~~`401 Unauthorized` OAuth token~~ — legacy api.wordstat.yandex.net снят. Нужен Api-Key из AI Studio.

## Выход

`memory/blog/articles/<topic_id>-<slug>/research-context.json`  
`memory/blog/articles/<topic_id>-<slug>/research-serp.json`  
`memory/blog/articles/<topic_id>-<slug>/research-wordstat.json` (при `--wordstat`)  
`memory/blog/articles/<topic_id>-<slug>/research-notes.md` (с разделом по Вордстату!)

## Замена уличных поисковиков

   Мы **отказываемся** от ненадежных сторонних утилит и парсеров DuckDuckGo («уток»).
   - Агент имеет полноценный доступ в интернет через нативный инструмент **`WebSearch`** (или `WebFetch` для чтения конкретных страниц).
   - Для анализа конкурентов в SERP **всегда используй инструмент `WebSearch`**. Ищи статьи, руководства, гайды по `primary_query` и ключевым словам в Яндексе и Google.
   - Игнорируй сырой `research-serp.json` из шага 0, если он пуст, неполный или нерелевантный. Твой собственный поиск через `WebSearch` — приоритетный источник свежих данных 2026 года.

## Правила

0. **Сначала** `excalibur_blog_research_start.py` (шаг 0) — для валидации даты/года и utility-gate темы.
1. Web research 15–25 мин: используй инструмент **`WebSearch`** Курсора для глубинного анализа ТОП-5 конкурентов в реальном времени. Приоритетный источник фактов — `fact-bank.md`.
2. Wordstat: `excalibur_wordstat.py` или `--wordstat` в research_start (см. выше); MCP — fallback.
3. Извлеки минимум 10–15 проверенных фактов (цифр/утверждений) с точными URL источников из твоего интернет-поиска.
4. Каждая цифра → таблица фактов в `research-notes.md` или не использовать.
5. Не копировать структуру конкурента 1:1.

## Blockers

- `❌ RESEARCH BLOCKER` — тема не найдена и не создана из запроса пользователя
- `❌ RESEARCH BLOCKER` — нет источников для ключевых утверждений
