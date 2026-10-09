# Agent orientation

1. `workspace/user.md` — хто користувач, мова, роль. Шаблон: `workspace.example/user.md.example`.
2. Правила в `.cursor/rules/`. Завжди увімкнені: письмо, мова, разові задачі, контекст.
3. Якщо задача схожа на skill — відкрити `.cursor/skills/<name>/SKILL.md`.
4. Факти компанії — `context/company/`. Політики — `context/onboarding/`. Немає файлу — не вигадувати.

Секрети лише в `workspace/keys/`. Реєстр Teams — `workspace/teams-chats.yaml`.

Claude Code бачить ті самі skills через міст:

```bash
make agent-bridge
```
