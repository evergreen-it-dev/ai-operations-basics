# Google (Gmail, Calendar, Drive)

Спільний OAuth-профіль: `workspace/keys/google` (шаблон `workspace.example/keys/google.example`).

```bash
cd tools/google
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python oauth_login.py
./.venv/bin/python check_oauth_identity.py --gmail-readonly
./.venv/bin/python gmail_tool.py messages --preset unread --max 20
./.venv/bin/python calendar_tool.py events --preset week --max 100
./.venv/bin/python drive_tool.py list-folder --id <FOLDER_ID>
```

Токен і client secret лишаються лише в `workspace/keys/`. У git їх немає.
