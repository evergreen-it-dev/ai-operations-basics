# workspace.example

Шаблони. Живі файли — у `workspace/`, ця тека в `.gitignore`.

macOS, Linux:

```bash
python3 tools/workspace/setup_workspace.py
```

Windows (PowerShell):

```powershell
py -3 tools/workspace/setup_workspace.py
```

Скрипт створює `workspace/keys` і `workspace/memory`, копіює шаблони, яких ще немає, і записує ОС у поле `OS` файлу `workspace/user.md`. Наявні файли не перезаписує.

Після копіювання заміни плейсхолдери. Секрети в git не класти.

ОС агент визначає сам із середовища і не питає. Команди в SKILL.md записані для macOS і Linux, на Windows агент перекладає їх за правилом `.cursor/rules/platform.mdc`.

## Що зробити далі

Підключи джерела і зніми локальні копії. Для кожного каналу спершу готовий коннектор свого агента: Claude, Codex чи Cursor (правило `.cursor/rules/connectors.mdc`). Ключі в `workspace/keys/` і скрипти з `tools/` потрібні лише там, де готового коннектора немає: особистий Telegram, Jira і Confluence on-prem, Folio. Немає URL або токена — спитай, не вигадуй хост і репозиторій.

1. Confluence. Заповни `workspace/keys/confluence`. Стягни доку проєктів і продуктів скілом `confluence-import` у `context/docs/confluence/<спейс>/`. Потрібен URL спейсу або кореневої сторінки.
2. Figma. Спершу готовий коннектор Figma свого агента. Без нього — токен у `workspace/keys/figma`, як випустити — розділ нижче.
3. Макети. Опиши їх у `context/design/catalog.yaml` і `context/design/<figma-name>/design.md`: екрани і компоненти з параметрами. Скіл `figma`.
4. Продукти. Репозиторій продукту — submodule у `context/products/<product-name>/`. Скіл `products`. Доку з вікі — пункт 1, не копія коду в `context/company/`.
5. Tone of voice. Підключи Gmail, Telegram, Teams і систему задач. Скіл `tone-of-voice` збирає 20–30 власних повідомлень (по 5 листів 1-1, чатів 1-1, груп і задач) і пише `workspace/my_voice.md`. Файл локальний, у git не класти.
6. Teammates і персони. Ті самі канали. Скіл `personas` дивиться, з ким є листування, і пише в `workspace/personas.md`, хто це і чим займається. Імена в git не класти.
7. Реєстр операцій. Скіл `operations-analysis` зводить календар, чати, пошту, задачі Jira і затреканий час. Пише `workspace/operations.md`. Файл локальний.

## Figma

Щоб читати макети, потрібен personal access token. Один рядок у `workspace/keys/figma`. У git не класти.

Як випустити: [Personal access tokens](https://developers.figma.com/docs/rest-api/personal-access-tokens/).

1. Увійти в Figma.
2. У списку файлів відкрити меню акаунта зліва вгорі і вибрати Settings.
3. Вкладка Security.
4. У блоці Personal access tokens натиснути Generate new token.
5. Задати строк дії і scopes. Для цього репозиторію: `file_content:read`, `file_metadata:read`, `folders:read`. Список scopes — [Scopes](https://developers.figma.com/docs/rest-api/scopes/).
6. Generate token. Рядок показують один раз, скопіювати одразу.
7. Вставити в `workspace/keys/figma` замість плейсхолдера.

Запит до API йде із заголовком `X-Figma-Token`. Токен діє від імені акаунта, який його випустив, і лише для файлів, які цей акаунт бачить. Якщо в Security видно чужу активність токена — відкликати його там само.
