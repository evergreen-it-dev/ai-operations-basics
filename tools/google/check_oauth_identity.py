#!/usr/bin/env python3
"""
Перевірка: OAuth Google (Gmail) = основний email з workspace/user.md.

За замовчуванням — лише gmail.readonly зі збереженого токена, без браузера
і без re-consent на зайві scope (forms.body тощо).

  cd tools/google
  python check_oauth_identity.py
  python check_oauth_identity.py --gmail-readonly
  python check_oauth_identity.py --json
  python check_oauth_identity.py --full-scopes   # ALL_OAUTH_SCOPES; headless не відкриє браузер

Exit 0 — Gmail читається; акаунт збігається АБО user.md шаблон/відсутній.
Exit 1 — Gmail читається, але реальний email у user.md інший, ніж OAuth.
Exit 2 — немає токена / refresh не вдався / Gmail API недоступний.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).parent))
from _auth import (
    ALL_OAUTH_SCOPES,
    GMAIL_READONLY_SCOPE,
    OAuthBrowserRequiredError,
    get_credentials_for_tool,
)
from _google_config import USER_MD, expected_google_email, is_placeholder_google_email


def actual_google_email(scopes: list[str]) -> tuple[str, str]:
    creds = get_credentials_for_tool(
        scopes,
        auth="oauth",
        oauth_client_secret=None,
        oauth_token=None,
        sa_credentials=None,
        impersonate=None,
        allow_browser=False,
        require_requested_scopes=False,
    )
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    prof = gmail.users().getProfile(userId="me").execute()
    email = (prof.get("emailAddress") or "").strip().lower()
    name = prof.get("name") or email
    return email, name


def main() -> int:
    p = argparse.ArgumentParser(description="OAuth Google = workspace/user.md?")
    p.add_argument("--json", action="store_true")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--gmail-readonly",
        action="store_true",
        help="Перевірити Gmail зі збереженого токена (gmail.readonly). Типово.",
    )
    mode.add_argument(
        "--full-scopes",
        action="store_true",
        help="Просити ALL_OAUTH_SCOPES без браузера (зайві scope пропускаються).",
    )
    args = p.parse_args()

    scopes = ALL_OAUTH_SCOPES if args.full_scopes else [GMAIL_READONLY_SCOPE]

    expected: str | None = None
    expected_error: str | None = None
    try:
        expected = expected_google_email()
        if is_placeholder_google_email(expected):
            expected_error = "user.md email is a placeholder template"
            expected = None
    except (FileNotFoundError, ValueError) as e:
        expected_error = str(e)

    try:
        actual, display = actual_google_email(scopes)
    except OAuthBrowserRequiredError as e:
        msg = f"Не вдалося прочитати OAuth-профіль (без браузера): {e}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg, "expected": expected}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        return 2
    except Exception as e:
        msg = f"Не вдалося прочитати OAuth-профіль: {e}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg, "expected": expected}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        return 2

    placeholder = expected is None
    matched = (not placeholder) and actual == expected
    # Шаблон / відсутній user.md не є MISMATCH, якщо Gmail читається.
    ok = matched or placeholder
    payload = {
        "ok": ok,
        "gmail_ok": True,
        "expected": expected,
        "actual": actual,
        "display_name": display,
        "user_md": str(USER_MD),
        "placeholder_user_md": placeholder,
        "scopes_mode": "full" if args.full_scopes else "gmail-readonly",
        "scopes_used": scopes,
    }
    if expected_error:
        payload["expected_error"] = expected_error

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if matched:
            print(f"OK: OAuth = {actual} (збігається з workspace/user.md)")
        elif placeholder:
            print(
                f"OK: Gmail читається як {actual}; "
                "workspace/user.md шаблон або без email — не блокер для readonly."
            )
            if expected_error:
                print(f"Примітка: {expected_error}")
        else:
            print(f"MISMATCH: OAuth = {actual}, очікується {expected} (workspace/user.md)")
            print("Для інтерактивних write-операцій потрібне підтвердження користувача.")
            print("gmail.readonly при цьому працює; scan-mail / читання пошти не блокуй.")
            print("Виправлення (інтерактивно): cd tools/google && python oauth_login.py")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
