# Спільні інструкції для агентів

Це репозиторій операційної роботи: навички, правила, інтеграції в tools/ і контекст компанії. Цей файл — точка входу для Codex, Claude Code, Cursor та інших агентів.

## Як почати

1. Прочитай README.md і правила «Завжди застосовувати» з індексу нижче. Уже прочитані в цій сесії файли повторно не відкривай, якщо вони не змінилися.
2. Перевір workspace/user.md, якщо він є. Явні вказівки користувача щодо мови й задачі мають пріоритет. Відсутність особистого профілю не блокує роботу з кодом і правилами.
3. Відкрий тематичне правило та відповідний SKILL.md. Читай лише потрібний для задачі контекст, а не всі навички, журнали й дампи.
4. Перед змінами перевір git status і локальні AGENTS.md у теках, з якими працюєш. Зберігай чужі незакомічені зміни.

## .cursor — спільне джерело інструкцій

Назва .cursor історична. Правила в .cursor/rules/ і навички в .cursor/skills/ застосовуються до всіх агентів цього репозиторію, зокрема Codex. Не пропускай їх через назву теки або розширення .mdc.

| Що | Як використовувати |
|---|---|
| .cursor/rules/*.mdc | Спільні правила. alwaysApply: true — на початку сесії; решта — за темою або відповідними globs у метаданих. |
| .cursor/skills/&lt;name&gt;/SKILL.md | Єдине джерело навички; допоміжні файли лежать поруч. |
| .agents/skills | Символічне посилання на ../.cursor/skills для виявлення навичок Codex. |
| .claude/skills, .claude/commands, .claude/agents | Символічні посилання на відповідні теки .cursor для Claude Code. |
| .cursor/commands/, .cursor/agents/ | Сценарії команд і ролі агентів. Інший агент може прочитати інструкцію; механізм запуску залежить від його середовища. |
| .cursor/hooks.json, .cursor/hooks/ | Налаштування й код хуків Cursor. Їхня наявність не означає, що вони працюють у Codex або Claude Code. |

Codex має читати правила .mdc за цим індексом: саме посилання в AGENTS.md не завантажує їхній повний текст. Якщо навички немає в автоматичному списку, відкрий її SKILL.md напряму. Не вигадуй інструменти MCP, команди чи типи субагентів, яких немає в поточному середовищі.

Редагуй оригінали в .cursor/, не створюй окремі копії для кожного агента. Після зміни правил або структури навичок виконай:

```bash
make agent-bridge
make agent-bridge-check
```

Індекси нижче та в CLAUDE.md генеруються скриптом tools/agents/sync_agent_bridge.py. Не редагуй блоки GENERATED вручну. Міст підключає файли інструкцій; він не встановлює MCP, залежності чи хуки для іншого агента.

## Де шукати контекст

| Що | Де |
|---|---|
| Користувач, мова, часовий пояс | workspace/user.md; шаблони налаштування — workspace.example/ |
| Факти про компанію та адресатів | context/company/; особисті доповнення — workspace/personas.md |
| Політики й база про агентів | context/onboarding/; імпорт Confluence — context/docs/confluence/ |
| Код і доки продукту | context/products/&lt;product-name&gt;/; для підключення репозиторію — навичка products |
| Макети Figma й дизайн-системи | context/design/; навички figma і design-md |
| Голос користувача, операції, задачі | workspace/my_voice.md, workspace/operations.md, workspace/TASKS.md |
| Пам'ять попередніх чатів | workspace/memory/; відсутній запис не відновлюй із припущень |

Teams — навичка teams-chat-review, правила teams-review і teams-privacy. Jira — навичка jira, для підключення — jira-connect. Teams і Jira використовуй лише через API/MCP та локальні скрипти цих інтеграцій, без браузера. Якщо підключення немає, перевір відповідну інструкцію; не підміняй API браузером.

Не виводь секрети з workspace/keys/ у чат, логи чи diff. Не вигадуй хости, людей, ролі й факти замість відсутнього контексту.

## Де зберігати результат

Чорновики не класти в корінь репозиторію. Не створювати `.tmp`, `.build`, `.codex-build`, `scratch`, `tmp`.

| Що | Куди |
|---|---|
| Разова задача і всі її файли | `tasks/<task-name>/`, всередині `task.md` |
| Дампи каналів | `output/<канал>/` |
| Ключі, журнал чатів, голос, персони, операції | `workspace/` |
| Факти і база про агентів | `context/` |

tasks/, output/ і workspace/ у git не входять. Нові разові результати зберігай там. Запит змінити код, правила або документацію цього репозиторію вже дозволяє редагувати відповідні стабільні файли на місці; додаткове підтвердження для цього не потрібне.

## Перевірка змін

Для правил і підключення агентів — make agent-bridge-check. Для коду — перевірки з README та конфігурації зміненого tools/&lt;name&gt;/; єдиного набору тестів на всі інтеграції немає. У фінальній відповіді коротко вкажи, що змінилося, які перевірки виконано та що залишилося неперевіреним.

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
