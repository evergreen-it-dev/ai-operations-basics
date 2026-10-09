#!/usr/bin/env python3
"""
Перевірка Jira Cloud: .env + GET /rest/api/3/myself (без змін у Jira).

  python3 scripts/jira_check.py

Еквівалент: `python3 scripts/fetch_jira_status_data.py --check-env`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from jira_env import check_jira_myself, get_jira_base_url  # noqa: E402


def main() -> None:
    me = check_jira_myself()
    # ASCII-only: Windows consoles often use cp1251 and choke on emoji in print().
    print(
        f"OK Jira: {me.get('displayName', '?')} "
        f"<{me.get('emailAddress', '?')}>"
    )
    print(f"   Base URL: {get_jira_base_url()}")


if __name__ == "__main__":
    main()
