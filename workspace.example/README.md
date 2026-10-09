# workspace.example

Шаблони. Живі файли — у `workspace/`, ця тека в `.gitignore`.

```bash
mkdir -p workspace/keys workspace/memory
cp workspace.example/user.md.example workspace/user.md
cp workspace.example/personas.md.example workspace/personas.md
cp workspace.example/my_voice.md.example workspace/my_voice.md
cp workspace.example/teams-access.yaml workspace/teams-access.yaml
cp workspace.example/teams-chats.yaml workspace/teams-chats.yaml
cp workspace.example/telegram-access.yaml workspace/telegram-access.yaml
cp workspace.example/TASKS.md.example workspace/TASKS.md
cp workspace.example/keys/google.example workspace/keys/google
cp workspace.example/keys/jira-onprem.example workspace/keys/jira-onprem
cp workspace.example/keys/folio.example workspace/keys/folio
cp workspace.example/keys/telegram.example workspace/keys/telegram
cp workspace.example/keys/confluence.example workspace/keys/confluence
cp workspace.example/keys/figma.example workspace/keys/figma
```

Після копіювання заміни плейсхолдери. Секрети в git не класти.

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
