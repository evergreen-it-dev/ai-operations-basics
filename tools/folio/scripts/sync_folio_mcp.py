#!/usr/bin/env python3
"""Синхронізує workspace/keys/folio → ~/.cursor/mcp.json (сервер folio)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "folio"))

from _auth import folio_base_url, read_token, token_path  # noqa: E402

MCP_PATH = Path.home() / ".cursor" / "mcp.json"
SERVER_NAME = "folio"
MCP_URL = f"{folio_base_url()}/mcp"


def load_mcp() -> dict:
    if not MCP_PATH.is_file():
        return {"mcpServers": {}}
    data = json.loads(MCP_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Некоректний JSON у {MCP_PATH}")
    data.setdefault("mcpServers", {})
    return data


def folio_entry(token: str) -> dict:
    return {
        "type": "streamable-http",
        "url": MCP_URL,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def main() -> int:
    print_only = "--print" in sys.argv

    try:
        token = read_token()
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        print(
            f"Створіть токен на {folio_base_url()} "
            f"→ меню користувача → API-токени\n"
            f"Збережіть у {token_path()} "
            f"(шаблон: workspace.example/keys/folio.example)",
            file=sys.stderr,
        )
        return 1

    entry = folio_entry(token)

    if print_only:
        redacted = {
            SERVER_NAME: {
                **entry,
                "headers": {"Authorization": "Bearer <TOKEN_FROM_workspace/keys/folio>"},
            }
        }
        print(json.dumps(redacted, indent=2, ensure_ascii=False))
        print(f"\n# mcpServers → {SERVER_NAME}", file=sys.stderr)
        return 0

    cfg = load_mcp()
    servers = cfg["mcpServers"]
    if not isinstance(servers, dict):
        raise ValueError("mcpServers має бути об'єктом")

    servers[SERVER_NAME] = entry
    MCP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MCP_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"✓ Оновлено {MCP_PATH} → mcpServers.{SERVER_NAME}")
    print("  Перезавантаж MCP у Cursor: Settings → MCP (зелений індикатор).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
