---
name: telegram-mcp
description: >-
  Особистий Telegram через локальний MCP (MTProto, не Bot API): папки, діалоги,
  непрочитане, пошук, медіа за t.me. Застосовувати на Telegram, unread, /telegram.
  Папки й боти-дайджести, які пропускати, беруться з workspace/telegram-access.yaml.
---

# Telegram (локальний MCP)

Сервер: `tools/telegram-mcp`. Транспорт HTTP, типово `http://localhost:3000/mcp`.

## Запуск

```bash
cd tools/telegram-mcp
cp .env.example .env
# TELEGRAM_API_ID і TELEGRAM_API_HASH з https://my.telegram.org
# або python3 scripts/sync_telegram_keys.py після workspace/keys/telegram
bun install
bun auth
bun dev
```

Сесія в `.env` і `bot-data/` — це пароль. У git не комітити.

## Безпека

- Read-only, доки write-tools не увімкнені в `bot-data/config.yml`. Не вмикати без явного запиту.
- Не дампити весь акаунт. Вузький запит: chatId, дати, limit.
- `markAsRead` лише за явним проханням.
- Вихідні (`fromMe: true`) в огляді непрочитаного не показувати.

## Інструменти

| Інструмент | Навіщо |
|---|---|
| `list_folders` | Папки акаунта |
| `get_folder_chats` | Чати папки |
| `list_dialogs` | Основний список; `type=user` — особисті 1:1 |
| `search_messages` | Пошук, у відповіді є chatId |
| `get_messages` | Повідомлення чату, `onlyUnread`, `markAsRead` |
| `search_dialogs` | Пошук за назвою |
| `media_download` | Файл медіа |
| `message_from_link` | Повідомлення за t.me |

## Непрочитане

1. `list_folders`.
2. Пропустити папки з `exclude_folder_titles` у `workspace/telegram-access.yaml` (шаблон у `workspace.example/`). Якщо користувач явно просить одну з них — читати лише її.
3. Для решти папок — `get_folder_chats`.
4. Особисті 1:1 додати через `list_dialogs` з `type: "user"`, якщо користувач не просив огляд без них.
5. По кожному chatId — `get_messages` з `onlyUnread: true`, `markAsRead: false`, limit близько 15, пауза між викликами. FloodWait чекати і повторювати.
6. Чати, де в непрочитаному лише вихідні, у звіт не брати.
7. Імена й id з `digest_chat_names` / `digest_chat_ids` зводити в одне саммарі, не списком кожної новини.

Після огляду кількох чатів зберегти в `output/telegram/`:

- `YYYY-MM-DD_HH-mm-ss_telegram_dump.json`
- `YYYY-MM-DD_HH-mm-ss_telegram_analysis.md`

Готовий прогін: `python3 tools/telegram-mcp/scripts/unread_folder_scan.py`.
