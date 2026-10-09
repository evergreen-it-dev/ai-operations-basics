# Operations approach

Каркас того, як агент у Cursor веде операційну роботу: правила, skills, локальні ключі, скрипти каналів.

Це зріз для показу. Репозиторій приватний: `evergreen-it-dev/ai-operations-basics`.

## Як це зібрано

Агент читає `.cursor/rules/` завжди або за темою, і skill у `.cursor/skills/<name>/SKILL.md`, коли запит збігається з описом. Секрети й реєстри чатів живуть у `workspace/` (не в git). Шаблони — `workspace.example/`. Факти компанії — `context/company/`. Політики — `context/onboarding/`. Код і доки продукту — `context/products/<product-name>/`: це git submodule, окремий клон репозиторію продукту. Макети Figma — `context/design/`: каталог у `catalog.yaml`, знімок макета в `<figma-name>/design.md`. Токен для API — personal access token у `workspace/keys/figma`, кроки в `workspace.example/README.md`.

## Що всередині

| Канал | Skill | Код |
|---|---|---|
| Teams | `teams-chat-review`, `teams-connect` | `tools/teams` |
| Telegram | `telegram-mcp` | `tools/telegram-mcp` |
| Jira | `jira`, `jira-connect` | `tools/jira` |
| Gmail | `gmail-tools` | `tools/google` |
| Drive | `google-drive-tools` | `tools/google` |
| Вікі | `folio` | `tools/folio` |
| Онбординг компанії | `onboarding` | `context/onboarding/` |
| Confluence | `confluence-import` | `tools/confluence-import` → `context/docs/confluence/` |
| Продукти | `products` | `context/products/<product-name>/` (git submodule) |
| Задачі | `productivity-update` | `workspace/TASKS.md` |
| Текст | `humor-writer`, субагент `writing-editor` | — |
| Голос | `tone-of-voice` | `workspace/my_voice.md` |
| Люди | `personas` | `workspace/personas.md` |
| Операції | `operations-analysis` | `workspace/operations.md` |
| Пам'ять | `workspace-chat-memory` | `workspace/memory/` |
| База про агентів | `onboarding` | `context/onboarding/ai-basics/` |
| Разова задача | `one-off-tasks` | `tasks/<task-name>/task.md` |
| Діаграми | `mermaid-flowcharts` | — |
| Дизайн | `figma`, `design-md`, `design-handoff`, `design-critique` | `context/design/` |

Мова чату береться з `workspace/user.md`, не зашита під одну людину.

## Чого тут немає навмисно

Реєстри чатів, токени, пошта, клієнти, проєкти Jira, папки Telegram і тексти онбордингу конкретної компанії. У шаблонах стоять `jira.example.com`, `folio.example.com`, порожні chatId.

Немає класифікатора вхідної пошти, масових скриптів переносу тікетів, фінансів, CRM, HR і продуктових інтеграцій.

`node_modules` і віртуальне оточення Python не скопійовані. Teams і Telegram треба зібрати локально (`npm install` / `bun install`). Інструкції — у README відповідного `tools/`.

## Перед тим як віддати

1. Пройтися `rg` по теці на назви людей, клієнтів і хости, якщо допишете свої приклади.
2. Заповнити `workspace.example` своїми плейсхолдерами, не бойовими ключами.
3. Окремо вирішити, чи ініціалізувати git і куди пушити.
