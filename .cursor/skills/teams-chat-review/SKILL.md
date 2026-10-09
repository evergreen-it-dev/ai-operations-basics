---
name: teams-chat-review
description: >-
  Огляд непрочитаних повідомлень Microsoft Teams по групах пріоритету з
  workspace/teams-chats.yaml: P0 favorites, P1 team, P2 operations.
  Застосовувати, коли користувач питає про Teams, непрочитані, нові чати,
  /teams, teams review. Не сканувати всі чати акаунта.
---

# Teams Chat Review

## Приватність

Перед fetch — `workspace/teams-access.yaml` (rule teams-privacy).

- Не викликати `list_chats` і `search_messages`. Це обходить реєстр і чіпає особисті чати.
- `get_chat_messages` — лише chatId з `workspace/teams-chats.yaml`, які не в `exclude_groups` (типово без `p0_1on1`).
- Новий робочий чат додавати в YAML вручну.

## Дві фази

Якщо файл `output/teams/teams_review_*.json` молодший за 10 хвилин — фазу 1 пропустити.

### Фаза 1 — дамп

```bash
cd tools/teams
node dump_review.js
node dump_review.js --days 2 --ops-days 7
```

Скрипт читає реєстр і політику, тягне лише дозволені чати, пише:

- `output/teams/teams_review_<YYYY-MM-DD_HHMM>.json`
- `output/teams/teams_review_<YYYY-MM-DD_HHMM>.md`

Потрібен зібраний MCP (`npm install && npm run build` у `tools/teams`), бо дамп імпортує `dist/`.

### Фаза 2 — аналіз

Прочитати свіжий Markdown/JSON. Якщо повідомлень менше ніж 200 — розбір в основному агенті. Якщо більше — паралельні субагенти по групах P0, P1, P2.

Звіт у чат: mentions першими, далі P0, P1, P2. По кожному пункту — хто, про що, чи є дія. Без переказу всього треду.

## Групи

| Група в YAML | Пріоритет | Як читати |
|---|---|---|
| mentions | P0 | Тегнули — першим |
| `p0_group` | P0 | Непрочитані за вікно `--days` |
| `p1_team`, `p1_standup`, `p1_onboarding`, `p1_internal` | P1 | Те саме вікно |
| решта, типово operations | P2 | Вікно `--ops-days`, коротко |

Реєстр: `workspace/teams-chats.yaml`. Шаблон із порожніми id: `workspace.example/teams-chats.yaml`.

Резолв alias:

```bash
node tools/teams/resolve_chat.js team-chat
```

Якщо id порожній — запитати chatId. Не робити глобальний пошук.
