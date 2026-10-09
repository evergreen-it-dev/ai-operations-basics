---
name: jira-connect
description: >-
  Підключення Jira: PAT, MCP, перша перевірка. Застосовувати при «підключити Jira».
disable-model-invocation: true
---

# Jira — підключення

Після підключення робочий skill — jira.

## Чекліст

- [ ] `cp workspace.example/keys/jira-onprem.example workspace/keys/jira-onprem`
- [ ] Вписати `JIRA_URL` свого інстансу і PAT
- [ ] `cd tools/jira/mcp-atlassian && python3 scripts/sync_jira_onprem_keys.py`
- [ ] `python3 scripts/check_jira_pat.py`
- [ ] Сервер `mcp-atlassian-on-prem` у `~/.cursor/mcp.json` (див. `mcp.json.example`)

PAT створюється в профілі Jira (Personal Access Tokens). У репозиторій його не класти.
