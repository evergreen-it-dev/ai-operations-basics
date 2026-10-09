---
name: jira
description: >-
  Jira: читання і правка задач, JQL, коментар, перехід статусу. On-prem через
  MCP mcp-atlassian-on-prem і PAT у workspace/keys/jira-onprem. Cloud — окремий
  MCP, якщо його підключили. Застосовувати на Jira, тікет, задачу, JQL.
---

# Jira

Проєкти й ключі не зашиті. Які проєкти є — дивитись у самому інстансі або в `context/company/`, якщо команда це описала.

## Який інструмент

```
On-prem (JIRA_URL з workspace/keys/jira-onprem) — MCP mcp-atlassian-on-prem
Cloud — той MCP, який підключили окремо
Один тікет / JQL / коментар / перехід → MCP
```

Налаштування: `tools/jira/mcp-atlassian/README.md`.

Типові tools: `jira_search`, `jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_transition_issue`.

Перед створенням задачі уточнити проєкт і тип, якщо їх не сказано. Не вигадувати ключ проєкту.

Перевірка доступу:

```bash
python3 tools/jira/jira-agent/scripts/jira_check.py
```
