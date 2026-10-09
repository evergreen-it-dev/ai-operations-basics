# Jira

- Один тікет, пошук, коментар, статус — MCP `mcp-atlassian-on-prem`. Див. `mcp-atlassian/README.md`.
- Перевірка логіну скриптом: `python3 tools/jira/jira-agent/scripts/jira_check.py` (потрібен `requests` і `python-dotenv`).
- URL інстансу — тільки з `workspace/keys/jira-onprem` або змінної `JIRA_URL`. Дефолт у коді `https://jira.example.com` навмисно не робочий.
