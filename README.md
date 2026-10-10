# Operations approach

Каркас операційної роботи для Codex, Claude Code і Cursor: спільні правила, навички, локальні ключі та скрипти каналів.

Це зріз для показу. Репозиторій: `evergreen-it-dev/ai-operations-basics`.

Початок роботи для агента — [AGENTS.md](AGENTS.md). Разові результати — tasks/&lt;task-name&gt;/, дампи — output/, ключі й журнал — workspace/. Чорновики не складати в корінь, .tmp чи .build.

## Спільні правила для Codex, Claude Code і Cursor

Назва .cursor історична: правила й навички в ній спільні для всіх агентів цього репозиторію. Оригінали залишаються в одному місці, а агенти отримують до них доступ через свої точки входу.

| Агент | Правила | Навички |
|---|---|---|
| Codex | AGENTS.md з індексом .cursor/rules/ | .agents/skills → ../.cursor/skills |
| Claude Code | CLAUDE.md з посиланням на AGENTS.md та індексом правил | .claude/skills → ../.cursor/skills |
| Cursor | .cursor/rules/, починаючи з 00_project-orientation.mdc | .cursor/skills/ |

Codex використовує AGENTS.md для інструкцій проєкту й виявляє локальні навички в .agents/skills, зокрема через символічні посилання. Джерела: [інструкції AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [локальні навички Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

Теку .cursor цілком не перейменовуємо: в ній є також налаштування Cursor — hooks.json, hooks/ і команди. .agents/skills дає Codex доступ до спільних навичок без дублювання файлів і зміни наявних посилань. Міст не переносить конфігурацію MCP чи хуків між агентами.

Після клонування або зміни правил перевір підключення:

```bash
make agent-bridge
make agent-bridge-check
```

Скрипт створює символічні посилання й оновлює індекси правил у AGENTS.md та CLAUDE.md. Звичайні файли й теки на місці посилань він не перезаписує. Перевірка з --check нічого не змінює. Для клону без підтримки symlinks агент може читати SKILL.md напряму з .cursor/skills/; для автоматичного виявлення навичок потрібні робочі символічні посилання.

## Як це зібрано

Агент читає загальні правила на початку сесії, тематичні — під задачу, а відповідний SKILL.md — перед виконанням навички. Секрети й реєстри чатів живуть у workspace/ (не в git). Шаблони — workspace.example/. Факти компанії — context/company/. Політики — context/onboarding/. Код і доки продукту — context/products/&lt;product-name&gt;/: репозиторій продукту підключається як git submodule. Макети Figma — context/design/: каталог у catalog.yaml, знімок макета в &lt;figma-name&gt;/design.md. Токен для API — personal access token у workspace/keys/figma, кроки в workspace.example/README.md.

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
