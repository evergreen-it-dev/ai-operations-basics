---
name: google-drive-tools
description: >-
  Google Drive: OAuth, список папки, копія, переміщення, нова папка, метадані.
  Застосовувати при Google Drive, drive_tool, «файли на диску».
---

# Google Drive

Спільний OAuth з Gmail. Профіль `workspace/keys/google`. Перед дією — rule google-oauth-identity.

```bash
cd tools/google
./.venv/bin/python oauth_login.py
./.venv/bin/python drive_tool.py list-folder --id <FOLDER_ID>
./.venv/bin/python drive_tool.py get-meta --id <FILE_ID>
./.venv/bin/python drive_tool.py create-folder --name "Назва" --parent <FOLDER_ID>
./.venv/bin/python drive_tool.py copy-file --id <FILE_ID> --name "Копія"
./.venv/bin/python drive_tool.py move-to-folder --id <FILE_ID> --folder <FOLDER_ID>
```

Папки команди (офери, клієнти, шаблони) описати в `context/company/`, коли вони з’являться. У цьому наборі конкретних folder id немає.

Запис, шаринг і видалення — лише після явного підтвердження.
