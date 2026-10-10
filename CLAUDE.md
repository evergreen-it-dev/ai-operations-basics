# Operations approach

Спочатку прочитай [AGENTS.md](AGENTS.md) — спільні інструкції, карту репозиторію, правила зберігання файлів і перевірки. Уже прочитані в поточній сесії правила повторно не відкривай.

.cursor/rules/ і .cursor/skills/ — спільне джерело для Claude Code, Codex і Cursor. Claude Code отримує навички, команди й ролі через посилання .claude/skills, .claude/commands і .claude/agents. Налаштування хуків Cursor автоматично сюди не переносяться.

Після зміни правил — make agent-bridge, потім make agent-bridge-check. Індекс нижче генерується з тих самих файлів, що й індекс AGENTS.md.

<!-- BEGIN GENERATED: rules-index (tools/agents/sync_agent_bridge.py) -->

### Завжди застосовувати (`alwaysApply: true`)

Прочитай ці файли на початку сесії — вони задають мову, контекст і поведінку:

- **[`00_project-orientation`](.cursor/rules/00_project-orientation.mdc)** — Спільна точка входу для Codex, Claude Code і Cursor. Правила й навички в .cursor застосовуються до всіх агентів; почни з AGENTS.md.
- **[`agent-data`](.cursor/rules/agent-data.mdc)** — Де Claude, Codex і Cursor кладуть дані. Не створювати .tmp, .build, .codex-build і інші чорнові теки в корені.
- **[`general-writing`](.cursor/rules/general-writing.mdc)** — Загальні правила письма агента: без слопу, головне зверху, без інлайн-коду посеред речення. Для чернетки від імені користувача читай наявні personas і my_voice. Текст назовні перевір за інструкцією writing-editor.
- **[`one-off-tasks`](.cursor/rules/one-off-tasks.mdc)** — Разова задача ні до чого конкретного: tasks/<task-name>/ з task.md і всіма файлами цієї задачі. Тека не в git.
- **[`reply-language`](.cursor/rules/reply-language.mdc)** — Мова відповідей береться з workspace/user.md (поле Language). Нові документи — тією ж мовою, що й аудиторія тексту. Іншу мову — лише за явним запитом.
- **[`workspace-context`](.cursor/rules/workspace-context.mdc)** — Перед узагальненою відповіддю про користувача або компанію читай workspace/user.md і context/company/. Код продукту — context/products/<product-name>, git submodule. Макети Figma — context/design, локальний знімок. Не вигадуй імена, ролі й факти.

### За темою (`alwaysApply: false`)

Відкрий правило, коли тема запиту збігається з описом:

| Rule | Коли читати |
|------|-------------|
| [`confluence-import`](.cursor/rules/confluence-import.mdc) | Активація: вигрузити Confluence, імпорт спейсу, коренева сторінка Confluence, confluence import, /confluence-import. REST-скрипт, не MCP. |
| [`design-md`](.cursor/rules/design-md.mdc) | Активація: дизайн-система, DESIGN.md, designmd, токени UI. Формат designmd.ai. Файл context/design/<slug>/DESIGN.md. Не плутати зі знімком макета design.md. |
| [`figma`](.cursor/rules/figma.mdc) | Активація: Figma, макет, компонент, варіант, дизайн екрана, context/design. Спочатку локальний знімок. Далі лише Figma MCP або REST API. Браузер не відкривати. |
| [`folio`](.cursor/rules/folio.mdc) | Активація: Folio, внутрішня вікі, list_spaces, read_page, search_pages, /folio. URL з FOLIO_BASE_URL. Не плутати з Confluence-онбордингом у context/onboarding. |
| [`gmail-tools`](.cursor/rules/gmail-tools.mdc) | Активація: Gmail, вхідні, непрочитані, /gmail-fetch. Команди з tools/google, skill gmail-tools. Ключі API не вигадувати. |
| [`google-drive-tools`](.cursor/rules/google-drive-tools.mdc) | Активація: Google Drive, папка на диску, drive_tool. Спільний OAuth з Gmail, skill google-drive-tools. |
| [`google-oauth-identity`](.cursor/rules/google-oauth-identity.mdc) | Перед Gmail і Drive перевірити, що OAuth-токен належить email з workspace/user.md. Якщо інший акаунт — стоп і явне підтвердження. |
| [`jira`](.cursor/rules/jira.mdc) | Активація: Jira, тікет, JQL, коментар або перехід статусу задачі Jira. Навичка jira; доступ лише через API/MCP, без браузера. |
| [`mermaid-flowcharts`](.cursor/rules/mermaid-flowcharts.mdc) | Активація: Mermaid, flowchart, блок-схема, діаграма процесу, graph у Markdown. Перед блоком mermaid — skill mermaid-flowcharts. |
| [`onboarding`](.cursor/rules/onboarding.mdc) | Загальні питання про компанію, політики, відпустки, «де це написано». Спочатку skill onboarding і context/onboarding. Сетап репозиторію: Confluence, Figma, макети, доки продуктів, tone of voice, персони, реєстр операцій — workspace.example/README.md. |
| [`operations-analysis`](.cursor/rules/operations-analysis.mdc) | Активація: реєстр операцій, чим я зайнятий, operations.md, календар і чати за місяць, затреканий час, /operations-analysis. |
| [`personas`](.cursor/rules/personas.mdc) | Активація: персони, teammates, з ким листуюсь, хто в команді, /personas. Люди з чатів і листів, без вигаданих ролей. |
| [`products`](.cursor/rules/products.mdc) | Активація: код або доки продукту, context/products, репозиторій продукту. Тека context/products/<product-name> — git submodule, окремий клон репо. |
| [`teams-privacy`](.cursor/rules/teams-privacy.mdc) | Політика приватності Microsoft Teams: не читати особисті чати, не сканувати весь Teams. Разом із teams-review і teams-chat-review. |
| [`teams-review`](.cursor/rules/teams-review.mdc) | Активація: Teams, непрочитані, нові чати, /teams, teams review. Питання про Microsoft Teams — skill teams-chat-review. |
| [`telegram-mcp`](.cursor/rules/telegram-mcp.mdc) | Активація: Telegram, непрочитані, особисті чати, /telegram. Лише локальний MCP у tools/telegram-mcp. Папки-виключення — workspace/telegram-access.yaml. |
| [`tone-of-voice`](.cursor/rules/tone-of-voice.mdc) | Активація: tone of voice, голос, my_voice, як я пишу, /tone-of-voice. Спочатку Gmail, Telegram, Teams. Корпус — лише тексти користувача. |
| [`workspace-chat-memory`](.cursor/rules/workspace-chat-memory.mdc) | Активація: пам'ять, memory, журнал чатів, що ми вже робили. Журнал у workspace/memory, пише хук, не агент. |

<!-- END GENERATED: rules-index -->
