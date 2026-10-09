"""Профіль Google Cloud з workspace/keys/google (шляхи, project_id)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_KEYS = _ROOT / "workspace" / "keys"
USER_MD = _ROOT / "workspace" / "user.md"
PROFILE_PATH = _KEYS / "google"
PROFILE_EXAMPLE = _ROOT / "workspace.example" / "keys" / "google.example"


def parse_key_value_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if key:
            data[key] = val
    return data


def load_google_profile() -> dict[str, str]:
    if not PROFILE_PATH.is_file():
        raise FileNotFoundError(
            f"Профіль Google не знайдено: {PROFILE_PATH}\n"
            f"Скопіюйте шаблон: cp workspace.example/keys/google.example workspace/keys/google\n"
            "Вкажіть project_id і oauth_client_secret для потрібного GCP-проєкту."
        )
    return parse_key_value_file(PROFILE_PATH)


def resolve_keys_path(value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = _KEYS / p
    return p.resolve()


def _resolve_existing_path(path: Path) -> Path:
    """Розв'язати шлях до файла (cwd, корінь репо, workspace/keys)."""
    candidates: list[Path] = [path]
    if not path.is_absolute():
        candidates.extend([_ROOT / path, _KEYS / path.name])
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return path.resolve()


def _fallback_client_secret_path() -> Path | None:
    """Якщо профіль google вказує на відсутній файл — client_secret з Secret config."""
    matches = sorted(_KEYS.glob("client_secret*.json"))
    if not matches:
        return None
    tok = oauth_token_path()
    if tok.is_file():
        try:
            token_data = json.loads(tok.read_text(encoding="utf-8"))
            token_client = token_data.get("client_id")
            if token_client:
                for candidate in matches:
                    if client_id_from_secret(candidate) == token_client:
                        return candidate.resolve()
        except (OSError, json.JSONDecodeError):
            pass
    if len(matches) == 1:
        return matches[0].resolve()
    return None


def profile_path(key: str, *, env_name: str | None = None) -> Path | None:
    env = os.environ.get(env_name, "").strip() if env_name else ""
    if env:
        return _resolve_existing_path(Path(env).expanduser())
    try:
        profile = load_google_profile()
    except FileNotFoundError:
        profile = {}
    return resolve_keys_path(profile.get(key))


def oauth_client_secret_path(explicit: str | None = None) -> Path:
    if explicit:
        return _resolve_existing_path(Path(explicit).expanduser())
    path = profile_path("oauth_client_secret", env_name="GOOGLE_OAUTH_CLIENT_SECRET")
    if path and path.is_file():
        return path
    fallback = _fallback_client_secret_path()
    if fallback:
        return fallback
    if path:
        raise FileNotFoundError(
            f"OAuth client secret не знайдено: {path}. "
            "Оновіть workspace/keys/google або GOOGLE_OAUTH_CLIENT_SECRET."
        )
    raise FileNotFoundError(
        "У workspace/keys/google не задано oauth_client_secret. "
        f"Див. {PROFILE_EXAMPLE}"
    )


def oauth_token_path(explicit: str | None = None) -> Path:
    if explicit:
        return _resolve_existing_path(Path(explicit).expanduser())
    path = profile_path("oauth_token", env_name="GOOGLE_OAUTH_TOKEN")
    if not path:
        path = _KEYS / "google_oauth_token.json"
    return _resolve_existing_path(path)


def service_account_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    path = profile_path("service_account")
    if not path:
        raise FileNotFoundError(
            "У workspace/keys/google не задано service_account. "
            f"Див. {PROFILE_EXAMPLE}"
        )
    return path


def impersonate_user(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit.strip() or None
    env = os.environ.get("GOOGLE_IMPERSONATE_USER", "").strip()
    if env:
        return env
    profile = load_google_profile()
    val = profile.get("impersonate_user", "").strip()
    return val or None


def client_id_from_secret(path: Path) -> str | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    block = data.get("installed") or data.get("web") or {}
    return block.get("client_id")


def project_id_from_secret(path: Path) -> str | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    block = data.get("installed") or data.get("web") or {}
    return block.get("project_id")


def assert_oauth_client_matches_token(client_secret: Path, token: Path) -> None:
    if not token.is_file():
        return
    expected = client_id_from_secret(client_secret)
    token_data = json.loads(token.read_text(encoding="utf-8"))
    actual = token_data.get("client_id")
    if expected and actual and expected != actual:
        profile = load_google_profile()
        project = profile.get("project_id") or project_id_from_secret(client_secret) or "?"
        raise ValueError(
            "OAuth token виданий іншим GCP OAuth client, ніж у workspace/keys/google.\n"
            f"  Профіль project_id: {project}\n"
            f"  Client secret client_id: {expected}\n"
            f"  Token client_id:        {actual}\n"
            "Перелогіньтесь під активним профілем:\n"
            "  cd tools/google && ./.venv/bin/python oauth_login.py"
        )


def is_placeholder_google_email(value: str) -> bool:
    """True для шаблону user.md (`[email@company.com]` тощо), не для реальної адреси."""
    v = (value or "").strip().lower().strip("*")
    if not v:
        return True
    if "[" in v or "]" in v:
        return True
    markers = (
        "email@company.com",
        "email@example.com",
        "your@",
        "example.com",
        " або ",
        " or ",
    )
    if any(m in v for m in markers):
        return True
    return re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", v) is None


def expected_google_email() -> str:
    """Основний робочий Google email з workspace/user.md."""
    if not USER_MD.is_file():
        raise FileNotFoundError(
            f"Немає {USER_MD}. Скопіюй workspace.example/user.md.example → workspace/user.md "
            "і вкажи основний робочий Google email."
        )
    for line in USER_MD.read_text(encoding="utf-8").splitlines():
        low = line.lower()
        if "основний робочий email" in low or "google (календар" in low:
            m = re.search(r"\*\*([^*]+@[^*]+)\*\*", line)
            if m:
                email = m.group(1).strip().lower()
                if is_placeholder_google_email(email):
                    raise ValueError(
                        "У workspace/user.md email ще шаблон (плейсхолдер), не реальна адреса."
                    )
                return email
    raise ValueError(
        "У workspace/user.md не знайдено рядок з основним робочим Google email "
        "(Accounts → **email@…** — основний робочий email / Google …)."
    )


def describe_active_profile() -> str:
    profile = load_google_profile()
    csecret = oauth_client_secret_path()
    tok = oauth_token_path()
    lines = [
        f"profile: {PROFILE_PATH}",
        f"project_id: {profile.get('project_id') or project_id_from_secret(csecret) or '?'}",
        f"oauth_client_secret: {csecret.name}",
        f"oauth_token: {tok.name}",
    ]
    sa = profile.get("service_account")
    if sa:
        lines.append(f"service_account: {sa}")
    imp = profile.get("impersonate_user")
    if imp:
        lines.append(f"impersonate_user: {imp}")
    return "\n".join(lines)
