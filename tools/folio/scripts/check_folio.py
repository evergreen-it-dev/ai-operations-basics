#!/usr/bin/env python3
"""Перевірка токена Folio: REST /api/spaces + наявність у ~/.cursor/mcp.json."""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "folio"))

from _auth import folio_base_url, read_token, token_path  # noqa: E402

MCP_PATH = Path.home() / ".cursor" / "mcp.json"
REST_SPACES = f"{folio_base_url()}/api/spaces"
SERVER_NAME = "folio"


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def mcp_has_server() -> bool:
    if not MCP_PATH.is_file():
        return False
    try:
        data = json.loads(MCP_PATH.read_text(encoding="utf-8"))
        servers = data.get("mcpServers") or {}
        return SERVER_NAME in servers
    except (json.JSONDecodeError, OSError):
        return False


def call_spaces(token: str) -> dict:
    req = urllib.request.Request(
        REST_SPACES,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(payload["error"])
    if not isinstance(payload, dict):
        raise RuntimeError(f"Несподівана відповідь REST: {payload!r}")
    return payload


def main() -> int:
    try:
        token = read_token()
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ Токен: {exc}")
        print("   Шаблон: workspace.example/keys/folio.example")
        return 1

    print(f"✓ Файл токена: {token_path()}")

    try:
        data = call_spaces(token)
        spaces = data.get("spaces") or []
        slugs = [s.get("slug") for s in spaces if isinstance(s, dict) and s.get("slug")]
        print(f"✓ REST /api/spaces: {len(spaces)} спейс(ів)" + (f" ({', '.join(slugs[:8])})" if slugs else ""))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"❌ REST API: {exc}")
        return 1

    if mcp_has_server():
        print(f"✓ MCP: сервер {SERVER_NAME} у {MCP_PATH}")
    else:
        print(f"— MCP: немає {SERVER_NAME} у {MCP_PATH}")
        print("  Запусти: python3 tools/folio/scripts/sync_folio_mcp.py")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
