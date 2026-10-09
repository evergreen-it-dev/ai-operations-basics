#!/usr/bin/env python3
"""Перевірка PAT для on-prem Jira: GET /rest/api/2/myself."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_JIRA_URL = "https://jira.example.com"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_dotenv(ENV)
    base = os.environ.get("JIRA_URL", DEFAULT_JIRA_URL).rstrip("/")
    token = os.environ.get("JIRA_PERSONAL_TOKEN", "").strip()
    if not token:
        print("❌ JIRA_PERSONAL_TOKEN не задано (.env або sync_jira_onprem_keys.py)", file=sys.stderr)
        return 1

    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "-H",
                f"Authorization: Bearer {token}",
                "-H",
                "Accept: application/json",
                f"{base}/rest/api/2/myself",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if proc.returncode != 0:
        print(
            f"❌ curl exit {proc.returncode} {base}/rest/api/2/myself\n{proc.stderr[:500]}",
            file=sys.stderr,
        )
        return 1

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"❌ Не JSON: {proc.stdout[:300]}", file=sys.stderr)
        return 1

    print(f"✅ Jira PAT OK — {data.get('displayName')} <{data.get('emailAddress')}>")
    print(f"   {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
