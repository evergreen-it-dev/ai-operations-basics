# Operations approach

Орієнтир для Claude Code. Правила й skills живуть у `.cursor/`.

1. `workspace/user.md` — роль і мова.
2. Skill — `.cursor/skills/<name>/SKILL.md`.
3. Компанія — `context/company/`. Онбординг — `context/onboarding/`.
4. Код і доки продукту — `context/products/<product-name>/`, git submodule (клон репозиторію). Skill — `.cursor/skills/products/SKILL.md`.
5. Макети Figma — `context/design/`. Skill — `.cursor/skills/figma/SKILL.md`. Дизайн-система — `context/design/<slug>/DESIGN.md`, skill `.cursor/skills/design-md/SKILL.md`.

`workspace/` і `tasks/` локальні, не в git.

Чорновики Codex і Claude не класти в корінь. Не створювати `.tmp`, `.build`, `.codex-build`, `scratch`, `tmp`. Разова задача — `tasks/<task-name>/` з `task.md`. Дампи каналів — `output/`. Ключі й журнал — `workspace/`. Те саме в `AGENTS.md`.

<!-- BEGIN GENERATED: rules-index (tools/agents/sync_agent_bridge.py) -->

### Завжди застосовувати (`alwaysApply: true`)

Прочитай ці файли на початку сесії — вони задають мову, контекст і поведінку:

- **[`agent-data`](.cursor/rules/agent-data.mdc)** — Де Claude, Codex і Cursor кладуть дані. Не створювати .tmp, .build, .codex-build і інші чорнові теки в корені.
- **[`general-writing`](.cursor/rules/general-writing.mdc)** — Загальні правила письма агента: без слопу, головне зверху, без інлайн-коду посеред речення. Перед чернеткою читай context/company/personas.md, за наявності workspace/personas.md, і workspace/my_voice.md. Чернетка людині назовні — через субагента writing-editor (спочатку знахідки слопу, потім правка).
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
