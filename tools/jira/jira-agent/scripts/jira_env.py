#!/usr/bin/env python3
"""
Shared Jira .env loading, base URL, and auth for tools/jira-agent/scripts.

Default: on-prem https://jira.example.com (PAT / Bearer). Set JIRA_URL.
Legacy Cloud: https://your-company.atlassian.net (email + ATLASSIAN_TOKEN / Basic).
"""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

DEFAULT_JIRA_BASE_URL = "https://jira.example.com"
LEGACY_CLOUD_JIRA_BASE_URL = "https://your-company.atlassian.net"

_DEFAULT_IMPL_TEMPLATE = "com.pyxis.greenhopper.jira:gh-simplified-agility-kanban"
_DEFAULT_IMPL_CATEGORY = "General"


def scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def task_dir() -> Path:
    """tools/jira/jira-agent (parent of scripts/)."""
    return scripts_dir().parent


def workspace_root() -> Path:
    """Repository root — three levels up from tools/jira/jira-agent."""
    return task_dir().parent.parent.parent


def _parse_key_value_file(path: Path, allowed: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        key = k.strip().upper()
        if key in allowed:
            out[key] = v.strip().strip('"').strip("'")
    return out


def _load_jira_onprem_keys_file() -> bool:
    """workspace/keys/jira-onprem → JIRA_URL, JIRA_PERSONAL_TOKEN (+ optional Confluence)."""
    keys_file = workspace_root() / "workspace" / "keys" / "jira-onprem"
    parsed = _parse_key_value_file(
        keys_file,
        {"JIRA_URL", "JIRA_PERSONAL_TOKEN", "CONFLUENCE_URL", "CONFLUENCE_PERSONAL_TOKEN"},
    )
    if not parsed.get("JIRA_PERSONAL_TOKEN"):
        return False
    os.environ.setdefault("JIRA_URL", parsed.get("JIRA_URL", DEFAULT_JIRA_BASE_URL))
    os.environ.setdefault("JIRA_BASE_URL", os.environ["JIRA_URL"])
    os.environ.setdefault("JIRA_PERSONAL_TOKEN", parsed["JIRA_PERSONAL_TOKEN"])
    return True


def _load_atlassian_keys_file() -> bool:
    """Read workspace/keys/atlassian and inject JIRA_EMAIL / ATLASSIAN_TOKEN.

    File format (two lines):
        user@company.example
        <api-token>

    Only sets env vars that are not already present.
    Returns True if the file was found and parsed.
    """
    keys_file = workspace_root() / "workspace" / "keys" / "atlassian"
    if not keys_file.is_file():
        return False
    try:
        lines = keys_file.read_text(encoding="utf-8").splitlines()
        lines = [ln.strip() for ln in lines if ln.strip()]
        if len(lines) < 2:
            return False
        email, token = lines[0], lines[1]
        os.environ.setdefault("JIRA_EMAIL", email)
        os.environ.setdefault("ATLASSIAN_TOKEN", token)
        return True
    except Exception:
        return False


def load_jira_dotenv() -> None:
    """Load credentials: on-prem PAT → legacy Cloud keys → .env."""
    _load_jira_onprem_keys_file()
    _load_atlassian_keys_file()
    for p in (task_dir() / ".env", scripts_dir() / ".env"):
        if p.is_file():
            load_dotenv(p, override=False)
            return
    load_dotenv()


def uses_personal_access_token() -> bool:
    load_jira_dotenv()
    return bool((os.environ.get("JIRA_PERSONAL_TOKEN") or "").strip())


def jira_rest_api_version() -> str:
    """On-prem / PAT → api/2; legacy Cloud → api/3 (override: JIRA_REST_API_VERSION)."""
    load_jira_dotenv()
    explicit = (os.environ.get("JIRA_REST_API_VERSION") or "").strip()
    if explicit in ("2", "3"):
        return explicit
    base = get_jira_base_url()
    if uses_personal_access_token():
        return "2"
    return "3"


def jira_rest_api_base() -> str:
    return f"{get_jira_base_url()}/rest/api/{jira_rest_api_version()}"


def get_jira_base_url() -> str:
    load_jira_dotenv()
    raw = os.environ.get("JIRA_BASE_URL") or os.environ.get("JIRA_URL") or DEFAULT_JIRA_BASE_URL
    return raw.rstrip("/")


def jira_browse_url(issue_key: str) -> str:
    """https://{host}/browse/KEY from JIRA_BASE_URL."""
    key = (issue_key or "").strip()
    return f"{get_jira_base_url()}/browse/{key}"


def confluence_wiki_api_v2_base() -> str:
    """Confluence REST API v2 base (wiki на тому ж хості, що JIRA_BASE_URL)."""
    return f"{get_jira_base_url()}/wiki/api/v2"


def get_jira_auth_headers(*, for_json_body: bool = True) -> dict[str, str]:
    load_jira_dotenv()
    pat = (os.environ.get("JIRA_PERSONAL_TOKEN") or "").strip()
    if pat:
        h: dict[str, str] = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/json",
        }
    else:
        email = os.environ.get("JIRA_EMAIL")
        token = os.environ.get("ATLASSIAN_TOKEN")
        if not email or not token:
            print(
                "❌ Немає JIRA_PERSONAL_TOKEN (on-prem) або JIRA_EMAIL+ATLASSIAN_TOKEN (legacy Cloud).\n"
                "   On-prem: workspace/keys/jira-onprem\n"
                "   Legacy: workspace/keys/atlassian або tools/jira-agent/.env",
                file=sys.stderr,
            )
            sys.exit(1)
        creds = base64.b64encode(f"{email}:{token}".encode()).decode()
        h = {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
        }
    if for_json_body:
        h["Content-Type"] = "application/json"
    return h


_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


def _http_max_attempts() -> int:
    raw = (os.environ.get("JIRA_HTTP_MAX_ATTEMPTS") or "4").strip()
    try:
        n = int(raw)
        return max(1, min(n, 10))
    except ValueError:
        return 4


def _retry_sleep_before_attempt(attempt: int, response: requests.Response | None) -> None:
    if response is not None:
        ra = response.headers.get("Retry-After")
        if ra:
            try:
                wait = min(int(float(ra)), 120)
                if wait > 0:
                    time.sleep(wait)
                    return
            except ValueError:
                pass
    time.sleep(min(1.5**attempt, 30.0))


def jira_http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60,
) -> requests.Response:
    """GET/POST/PUT/DELETE with retries on 429 / 502 / 503 / 504 (Retry-After when numeric)."""
    last: requests.Response | None = None
    max_att = _http_max_attempts()
    for attempt in range(max_att):
        m = method.upper()
        if m == "GET":
            last = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif m == "POST":
            last = requests.post(
                url, headers=headers, json=json_body, timeout=max(timeout, 90.0)
            )
        elif m == "PUT":
            last = requests.put(url, headers=headers, json=json_body, timeout=timeout)
        elif m == "DELETE":
            last = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method {method}")
        if last.status_code not in _RETRYABLE_STATUS or attempt >= max_att - 1:
            return last
        _retry_sleep_before_attempt(attempt, last)
    assert last is not None
    return last


def check_jira_myself() -> dict[str, Any]:
    """GET /rest/api/{2|3}/myself — for --check-env smoke."""
    headers = get_jira_auth_headers(for_json_body=False)
    r = jira_http_request(
        "GET", f"{jira_rest_api_base()}/myself", headers=headers, timeout=60
    )
    if not r.ok:
        print(f"❌ GET /myself failed: {r.status_code}\n{r.text[:400]}", file=sys.stderr)
        sys.exit(1)
    return r.json()


def resolve_project_category_id(headers: dict[str, str], category_name: str) -> str | None:
    """Match GET /rest/api/3/projectCategory by name (case-insensitive)."""
    if not (category_name or "").strip():
        return None
    r = jira_http_request(
        "GET",
        f"{jira_rest_api_base()}/projectCategory",
        headers=headers,
        timeout=60,
    )
    if not r.ok:
        return None
    want = category_name.strip().lower()
    for cat in r.json():
        if (cat.get("name") or "").lower() == want:
            return str(cat["id"])
    return None


def get_impl_project_settings() -> dict[str, str]:
    """Template + category for POST /project (create_jira_project / create_project_and_move_issues)."""
    load_jira_dotenv()
    return {
        "project_template_key": os.environ.get(
            "JIRA_IMPL_PROJECT_TEMPLATE_KEY", _DEFAULT_IMPL_TEMPLATE
        ),
        "project_category_name": os.environ.get(
            "JIRA_IMPL_PROJECT_CATEGORY_NAME", _DEFAULT_IMPL_CATEGORY
        ),
    }


def check_env(mode: str = "basic") -> dict[str, Any]:
    """
    Unified --check-env helper for jira-agent scripts.

    Modes:
      * "basic" — auth + GET /rest/api/3/myself (read-only smoke).
      * "write" — "basic" + note that the token will be used for POST/PUT/DELETE.
        Same auth, no extra API calls (Jira Cloud has no dedicated "can write"
        endpoint; actual write permissions are project-scoped).

    Returns the /myself payload so callers can print account info.
    """
    me = check_jira_myself()
    m = (mode or "basic").strip().lower()
    if m == "write":
        display = me.get("displayName") or me.get("emailAddress") or "?"
        print(
            f"   ℹ️  Будуть виконуватись POST/PUT/DELETE від імені {display}. "
            "Переконайся, що токен має потрібні project-scoped права.",
            file=sys.stderr,
        )
    return me

