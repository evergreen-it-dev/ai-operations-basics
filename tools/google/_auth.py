"""Облікові дані Google: OAuth (користувач) та service account (Workspace/delegation)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from _google_config import (
    assert_oauth_client_matches_token,
    expected_google_email,
    impersonate_user,
    oauth_client_secret_path,
    oauth_token_path,
    service_account_path,
)

# Усі scope для одного токена; після зміни перезапустіть oauth_login.py.
ALL_OAUTH_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/forms.body",
]

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class OAuthBrowserRequiredError(RuntimeError):
    """Немає валідного токена / refresh, а браузерний consent недоступний (headless)."""


def resolve_credentials_path(explicit: str | None) -> Path:
    return service_account_path(explicit)


def resolve_oauth_client_secret(explicit: str | None) -> Path:
    return oauth_client_secret_path(explicit)


def resolve_oauth_token(explicit: str | None) -> Path:
    return oauth_token_path(explicit)


def oauth_browser_allowed() -> bool:
    """False у CI, GOOGLE_OAUTH_HEADLESS=1 або коли немає runnable browser."""
    if os.environ.get("GOOGLE_OAUTH_HEADLESS", "").strip().lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("CI", "").strip().lower() in ("1", "true", "yes"):
        return False
    try:
        import webbrowser

        webbrowser.get()
    except Exception:
        return False
    return True


def _persist_token(tok: Path, creds: Credentials) -> None:
    tok.parent.mkdir(parents=True, exist_ok=True)
    with open(tok, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def _consent_kwargs() -> dict:
    oauth_kwargs: dict = {"prompt": "select_account consent"}
    try:
        oauth_kwargs["login_hint"] = expected_google_email()
    except (FileNotFoundError, ValueError):
        pass
    return oauth_kwargs


def _run_browser_consent(csecret: Path, scopes: list[str], tok: Path) -> Credentials:
    """Інтерактивний consent. У headless завжди помилка, без run_local_server."""
    if not oauth_browser_allowed():
        raise OAuthBrowserRequiredError(
            "OAuth потребує браузерний consent, але середовище headless "
            "(немає браузера, CI або GOOGLE_OAUTH_HEADLESS). "
            "На машині з браузером: cd tools/google && python oauth_login.py"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(csecret), scopes)
    try:
        creds = flow.run_local_server(port=0, open_browser=True, **_consent_kwargs())
    except Exception as e:
        raise OAuthBrowserRequiredError(
            f"Не вдалося відкрити браузер для OAuth consent: {e}"
        ) from e
    _persist_token(tok, creds)
    return creds


def get_oauth_credentials(
    scopes: list[str],
    *,
    client_secret_path: str | Path | None = None,
    token_path: str | Path | None = None,
    allow_browser: bool | None = None,
    require_requested_scopes: bool = False,
) -> Credentials:
    """
    OAuth Desktop: токен на диску.

    За замовчуванням (headless-safe):
    - якщо токен є і refresh працює — використовуємо **збережені** scope;
    - відсутні з `scopes` (наприклад forms.body у ALL_OAUTH_SCOPES) **не**
      відкривають браузер, а пропускаються;
    - браузер лише коли токена немає / refresh неможливий **і** є runnable browser.

    `oauth_login.py` передає require_requested_scopes=True, щоб добрати всі scope.
    Identity check передає allow_browser=False — ніколи не consent.
    """
    csecret = resolve_oauth_client_secret(str(client_secret_path) if client_secret_path else None)
    tok = resolve_oauth_token(str(token_path) if token_path else None)

    if not csecret.is_file():
        raise FileNotFoundError(
            f"OAuth client secret не знайдено: {csecret}. "
            "Оновіть workspace/keys/google або GOOGLE_OAUTH_CLIENT_SECRET."
        )

    assert_oauth_client_matches_token(csecret, tok)

    can_browser = False if allow_browser is False else oauth_browser_allowed()

    creds: Credentials | None = None
    stored_scopes: set[str] = set()
    if tok.is_file():
        token_data = json.loads(tok.read_text(encoding="utf-8"))
        file_scopes = token_data.get("scopes")
        stored_scopes = set(file_scopes or [])
        # Refresh fails with invalid_scope if we force newer scopes than the token was issued for.
        load_scopes = file_scopes if file_scopes else scopes
        creds = Credentials.from_authorized_user_file(str(tok), load_scopes)

    needed = set(scopes)
    missing_scopes = (needed - stored_scopes) if stored_scopes else (needed if not creds else set())

    if creds is not None:
        if not creds.valid:
            if creds.refresh_token:
                creds.refresh(Request())
                _persist_token(tok, creds)
            elif can_browser:
                return _run_browser_consent(csecret, scopes, tok)
            else:
                raise OAuthBrowserRequiredError(
                    "OAuth-токен невалідний і немає refresh_token. "
                    "У headless браузер не відкриваємо. "
                    "На машині з браузером: cd tools/google && python oauth_login.py"
                )
        if missing_scopes and require_requested_scopes:
            if can_browser:
                return _run_browser_consent(csecret, scopes, tok)
            raise OAuthBrowserRequiredError(
                "OAuth-токену не вистачає scope: "
                + ", ".join(sorted(missing_scopes))
                + ". Headless не робить re-consent. "
                "Інтерактивно: cd tools/google && python oauth_login.py"
            )
        if missing_scopes:
            print(
                "OAuth: пропускаю відсутні scope (без браузера): "
                + ", ".join(sorted(missing_scopes)),
                file=sys.stderr,
            )
        return creds

    if can_browser:
        return _run_browser_consent(csecret, scopes, tok)
    raise OAuthBrowserRequiredError(
        "Немає OAuth-токена. У headless браузер не відкриваємо. "
        "На машині з браузером: cd tools/google && python oauth_login.py"
    )


def get_delegated_credentials(
    scopes: list[str],
    *,
    credentials_path: Path | None = None,
    subject: str | None = None,
):
    """
    Service account. Із subject — domain-wide delegation (Workspace).
    """
    path = resolve_credentials_path(str(credentials_path) if credentials_path else None)
    if not path.is_file():
        raise FileNotFoundError(
            f"Файл ключів не знайдено: {path}. "
            "Оновіть workspace/keys/google або GOOGLE_APPLICATION_CREDENTIALS."
        )

    subj = impersonate_user(subject)

    base = service_account.Credentials.from_service_account_file(
        str(path), scopes=scopes
    )
    if subj:
        return base.with_subject(subj)
    return base


def get_credentials_for_tool(
    scopes: list[str],
    *,
    auth: str,
    oauth_client_secret: str | None,
    oauth_token: str | None,
    sa_credentials: str | None,
    impersonate: str | None,
    allow_browser: bool | None = None,
    require_requested_scopes: bool = False,
):
    """auth: 'oauth' | 'service-account'."""
    if auth == "oauth":
        return get_oauth_credentials(
            scopes,
            client_secret_path=oauth_client_secret,
            token_path=oauth_token,
            allow_browser=allow_browser,
            require_requested_scopes=require_requested_scopes,
        )
    return get_delegated_credentials(
        scopes,
        credentials_path=Path(sa_credentials).expanduser().resolve() if sa_credentials else None,
        subject=impersonate,
    )
