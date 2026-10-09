#!/usr/bin/env python3
"""
Перший вхід OAuth: запитує всі scope (Gmail, Calendar, Sheets, Docs, Drive, Forms) і зберігає токен.

Активний GCP-профіль — workspace/keys/google (шаблон google.example).
Після зміни scope у `_auth.py` можливо знадобиться повторний вхід (новий consent).

  python oauth_login.py
  python oauth_login.py --show-profile
  python oauth_login.py --client-secret ... --token ...

Перевага над env: GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_TOKEN.
"""

from __future__ import annotations

import argparse
import sys

from _auth import ALL_OAUTH_SCOPES, OAuthBrowserRequiredError, get_oauth_credentials
from _google_config import describe_active_profile


def main() -> int:
    p = argparse.ArgumentParser(description="Зберегти OAuth-токен для tools/google")
    p.add_argument(
        "--show-profile",
        action="store_true",
        help="Показати активний профіль workspace/keys/google і вийти",
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="JSON OAuth client (Desktop); інакше з workspace/keys/google",
    )
    p.add_argument(
        "--token",
        default=None,
        help="Куди зберегти токен; інакше oauth_token з workspace/keys/google",
    )
    args = p.parse_args()
    if args.show_profile:
        try:
            print(describe_active_profile())
            return 0
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 1
    try:
        get_oauth_credentials(
            ALL_OAUTH_SCOPES,
            client_secret_path=args.client_secret,
            token_path=args.token,
            allow_browser=True,
            require_requested_scopes=True,
        )
        print("Готово: токен збережено, можна викликати gmail_tool.py та calendar_tool.py.")
        print(describe_active_profile())
        return 0
    except (FileNotFoundError, ValueError, OAuthBrowserRequiredError) as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
