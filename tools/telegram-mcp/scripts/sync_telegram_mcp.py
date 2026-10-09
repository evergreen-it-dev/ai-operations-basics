#!/usr/bin/env python3
"""Додає/оновлює сервер telegram у ~/.cursor/mcp.json (HTTP MCP на localhost:3000)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT / "tools" / "telegram-mcp" / ".env"
MCP_PATH = Path.home() / ".cursor" / "mcp.json"
SERVER_NAME = "telegram"
DEFAULT_PORT = 3000


def load_port() -> int:
    if not ENV_PATH.is_file():
        return DEFAULT_PORT
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("PORT="):
            val = s.split("=", 1)[1].strip()
            if val.isdigit():
                return int(val)
    return DEFAULT_PORT


def telegram_entry(port: int) -> dict:
    return {
        "url": f"http://localhost:{port}/mcp",
    }


def load_mcp() -> dict:
    if not MCP_PATH.is_file():
        return {"mcpServers": {}}
    data = json.loads(MCP_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Некоректний JSON у {MCP_PATH}")
    data.setdefault("mcpServers", {})
    return data


def main() -> int:
    print_only = "--print" in sys.argv
    port = load_port()
    entry = telegram_entry(port)
    snippet = {SERVER_NAME: entry}

    if print_only:
        print(json.dumps(snippet, indent=2, ensure_ascii=False))
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
    print(f"OK: оновлено {MCP_PATH} -> mcpServers.{SERVER_NAME}")
    print(f"  url: http://localhost:{port}/mcp")
    print("  Запусти сервер: cd tools/telegram-mcp && bun start")
    print("  Перезавантаж MCP у Cursor: Settings -> MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
