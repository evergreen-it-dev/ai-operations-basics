---
name: gmail-tools
description: >-
  Вибірка листів Gmail із пресетами (непрочитані, за ~24 год, фільтри), зняття мітки
  непрочитаного та compose (draft/send) через tools/google/gmail_tool.py та OAuth.
  Застосовувати, коли користувач просить Gmail, вхідні, непрочитані листи, фільтри пошти,
  вигрузити листи, позначити прочитаним, надіслати/чернетку листа або згадує slash-команду gmail-fetch.
---

# Gmail (локальні скрипти)

**OAuth-особа:** перед будь-якою операцією — rule **google-oauth-identity** (`.cursor/rules/google-oauth-identity.mdc`): `check_oauth_identity.py`. При MISMATCH — стоп і **явне** підтвердження користувача.

Усі команди з каталогу **`tools/google`** відносно кореня цього репозиторію. Інтерпретатор: **`tools/google/.venv/bin/python`**. Робоча директорія для викликів: **`tools/google`**.

**Активний GCP-профіль:** `workspace/keys/google` (шаблон `workspace.example/keys/google.example`) — `project_id`, шляхи до OAuth client secret, token, service account. У коді немає жорсткої прив’язки до проєкту. Перевірка: `oauth_login.py --show-profile`.

Перед першим доступом до пошти один раз: `oauth_login.py` (токен за шляхом з профілю, зазвичай `workspace/keys/google_oauth_token.json`).

## Скрипт

| Задача | Команда |
|--------|---------|
| Список листів | `gmail_tool.py messages …` |
| Позначити прочитаними | `gmail_tool.py mark-read --ids <id> [<id> …]` |
| Список фільтрів | `gmail_tool.py filters` |
| Список міток | `gmail_tool.py labels` |
| Чернетка / лист | `gmail_tool.py compose` (без `--apply` — dry-run) |
| Список листів на диск | `gmail_tool.py messages … --save` → `output/gmail/` |

Шаблон оболонки:

```bash
cd "<workspace>/tools/google" && ./.venv/bin/python gmail_tool.py …
```

Підстав фактичний шлях до workspace.

## Вибірка листів (`messages`)

Відповідність запиту користувача та прапорів:

| Намір | Прапори |
|-------|---------|
| Усі непрочитані | `--preset unread` |
| Усі за останні ~24 год | `--preset last-24h` |
| Непрочитані за ~24 год | `--preset unread-24h` |
| За збереженим фільтром (відомий id) | `--filter-id <ID>` |
| Фільтр за підказкою (домен, частина правила) | `--filter-match <підрядок>` — перше збіг за id або JSON критеріїв |

Додатково: `--label` / `--label-name`, `-q` для операторів Gmail. Частини з’єднуються в один запит (фільтр → пресет → `-q`).

Рекомендований обсяг: **`--max`** 50–150 для широких вибірок. Для дампу на диск додавай **`--save`**: JSON у `tools/google/output/gmail_messages_<timestamp>.json`, шлях до файлу — у stderr.

Приклади:

```bash
./.venv/bin/python gmail_tool.py messages --preset unread --max 100 --save
./.venv/bin/python gmail_tool.py messages --preset unread-24h --max 80 --save
./.venv/bin/python gmail_tool.py messages --filter-match example.com --preset unread --max 50 --save
```

Якщо потрібен id фільтра: спочатку `gmail_tool.py filters` або `filters --save`, потім `--filter-id`.

## Позначити як прочитані (`mark-read`)

Message id — рядок з API (не thread id). Джерела id:

1. Перша колонка в режимі summary при `messages` (формат `id \t…`).
2. Поле **`id`** у об’єктах у **`items`** у збереженому JSON (`--save`).
3. Явний список від користувача.

Команда:

```bash
./.venv/bin/python gmail_tool.py mark-read --ids abc111 def222
```

Опційно **`--save`** — записує json з переліком id у `output/`.

**Політика:** виконуй `mark-read` лише якщо користувач явно просить позначити прочитаним (конкретні листи або «усі з останньої вибірки»). Якщо користувач перелічив теми/відправників без id — спочатку зроби вибірку через `messages`, зістав із запитом, потім підтвердження або перелік id перед зняттям UNREAD.

## Надіслати або чернетка (`compose`)

Без **`--apply`** — лише preview (нічого не створює). `--mode draft` (за замовчуванням) або `send`. Send лише якщо користувач явно попросив відправити.

```bash
./.venv/bin/python gmail_tool.py compose \
  --to client@example.com \
  --subject "Тема" \
  --body-file letter.txt \
  --mode draft
./.venv/bin/python gmail_tool.py compose … --mode draft --apply
```

`--html` якщо тіло HTML. **Політика:** `--apply` лише після явного confirm у чаті.

## Після вибірки

Стисло підсумуй у чаті: кількість листів, теми/відправники. Не копіюй повністю тіла листів і зайві персональні дані. Порожня вибірка — повідом явно. Помилка 403/авторизації — нагадай про `oauth_login.py`.
