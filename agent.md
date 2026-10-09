# Agent orientation

1. `workspace/user.md` — хто користувач, мова, роль. Шаблон: `workspace.example/user.md.example`.
2. Правила в `.cursor/rules/`. Завжди увімкнені: письмо, мова, разові задачі, контекст.
3. Якщо задача схожа на skill — відкрити `.cursor/skills/<name>/SKILL.md`.
4. Факти компанії — `context/company/`. Політики — `context/onboarding/`. Немає файлу — не вигадувати.
5. Код і доки продукту — `context/products/<product-name>/`. Це git submodule: окремий клон репозиторію продукту. Skill — `.cursor/skills/products/SKILL.md`.
6. Макети Figma — `context/design/catalog.yaml` і `context/design/<figma-name>/design.md`. Спочатку локальний знімок. Skill — `.cursor/skills/figma/SKILL.md`.
7. Дизайн-система — `context/design/<slug>/DESIGN.md`. Skill — `.cursor/skills/design-md/SKILL.md`.

Секрети лише в `workspace/keys/`. Токен Figma — `workspace/keys/figma`, як випустити — `workspace.example/README.md`. Реєстр Teams — `workspace/teams-chats.yaml`.

Claude Code бачить ті самі skills через міст:

```bash
make agent-bridge
```
