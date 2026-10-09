---
name: teams-connect
description: >-
  Підключення Microsoft Teams: MCP, реєстр робочих чатів, перший дамп.
  Застосовувати при «підключити Teams», teams MCP, /teams-connect.
disable-model-invocation: true
---

# Microsoft Teams — підключення

Після підключення щоденний огляд робить skill teams-chat-review.

## Чекліст

- [ ] MCP Teams у `~/.cursor/mcp.json` (сервер з `tools/teams`, після `npm install && npm run build`)
- [ ] Авторизація Graph (перший запуск)
- [ ] `cp workspace.example/teams-access.yaml workspace/teams-access.yaml` і заповнити account
- [ ] `cp workspace.example/teams-chats.yaml workspace/teams-chats.yaml` і вписати свої chatId
- [ ] Тест: `cd tools/teams && node dump_review.js`
- [ ] Файл `output/teams/teams_review_*.json` з’явився

Особисті 1:1 у загальний реєстр не класти. Для них окремий локальний файл `workspace/teams-chats-personal.yaml`, його не комітити. Група `p0_1on1` у політиці доступу виключена.
