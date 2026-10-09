# Agent orientation

1. `workspace/user.md` — хто користувач, мова, роль. Шаблон: `workspace.example/user.md.example`.
2. Правила в `.cursor/rules/`. Завжди увімкнені: письмо, мова, разові задачі, контекст.
3. Якщо задача схожа на skill — відкрити `.cursor/skills/<name>/SKILL.md`.
4. Факти компанії — `context/company/`. Політики — `context/onboarding/`. Немає файлу — не вигадувати.
5. Код і доки продукту — `context/products/<product-name>/`. Це git submodule: окремий клон репозиторію продукту. Skill — `.cursor/skills/products/SKILL.md`.
6. Макети Figma — `context/design/catalog.yaml` і `context/design/<figma-name>/design.md`. Спочатку локальний знімок. Skill — `.cursor/skills/figma/SKILL.md`.
7. Дизайн-система — `context/design/<slug>/DESIGN.md`. Skill — `.cursor/skills/design-md/SKILL.md`.
8. Голос автора — `workspace/my_voice.md`. Якщо файл порожній, на онбордингу збери його скілом `tone-of-voice`.
9. Люди, з якими є листування — `workspace/personas.md`. На онбордингу збери скілом `personas`. Не вигадуй роль, якої немає в листах і чатах.
10. Чим людина зайнята — `workspace/operations.md`. На онбордингу збери скілом `operations-analysis`: календар, чати, пошта, Jira і затреканий час.
11. Журнал чатів — `workspace/memory/`. Його пише хук, skill `workspace-chat-memory`. База про роботу з агентом — `context/onboarding/ai-basics/`.
12. Разова задача ні до чого конкретного — `tasks/<task-name>/task.md` і файли поруч. Skill `one-off-tasks`. Тека не в git.

Секрети лише в `workspace/keys/`. Токен Figma — `workspace/keys/figma`, як випустити — `workspace.example/README.md`. Реєстр Teams — `workspace/teams-chats.yaml`.

Claude Code бачить ті самі skills через міст:

```bash
make agent-bridge
```
