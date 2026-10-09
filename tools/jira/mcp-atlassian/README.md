# Jira MCP (on-prem)

MCP-сервер [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) для Jira Data Center / Server.

Хост задається в `workspace/keys/jira-onprem` (шаблон `workspace.example/keys/jira-onprem.example`). У прикладах стоїть `https://jira.example.com` — замініть на свій.

## Ключі

1. PAT Jira → `workspace/keys/jira-onprem` (`JIRA_URL`, `JIRA_PERSONAL_TOKEN`).
2. Якщо Confluence на тому ж хості — `CONFLUENCE_URL` у тому ж файлі або окремий PAT.

## Синк у MCP

```bash
cd tools/jira/mcp-atlassian
python3 scripts/sync_jira_onprem_keys.py
python3 scripts/check_jira_pat.py
python3 scripts/print_mcp_snippet.py
```

Фрагмент для `~/.cursor/mcp.json` — `mcp.json.example`. Сервер: `mcp-atlassian-on-prem`.

Один тікет, JQL, коментар, перехід статусу — через MCP. Масові звіти під конкретні проєкти в цей набір не входять: їх пишуть окремим скриптом під свої ключі проєктів.
