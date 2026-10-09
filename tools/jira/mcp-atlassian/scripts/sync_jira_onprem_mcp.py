#!/usr/bin/env python3
"""Синхронізує tools/jira/mcp-atlassian/.env → ~/.cursor/mcp.json (mcp-atlassian-on-prem)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MCP_ATLASSIAN_DIR = SCRIPT_DIR.parent
MCP_PATH = Path.home() / ".cursor" / "mcp.json"
SERVER_NAME = "mcp-atlassian-on-prem"


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

    sync = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "sync_jira_onprem_keys.py")],
        check=False,
    )
    if sync.returncode != 0:
        return sync.returncode

    snippet_proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "print_mcp_snippet.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    if snippet_proc.returncode != 0:
        print(snippet_proc.stderr, file=sys.stderr)
        return snippet_proc.returncode

    snippet = json.loads(snippet_proc.stdout)
    if not isinstance(snippet, dict) or SERVER_NAME not in snippet:
        print(f"❌ Некоректний snippet від print_mcp_snippet.py", file=sys.stderr)
        return 1

    entry = snippet[SERVER_NAME]
    if print_only:
        print(json.dumps(snippet, indent=2, ensure_ascii=False))
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
