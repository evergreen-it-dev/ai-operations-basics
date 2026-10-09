#!/usr/bin/env python3
"""Друкує фрагмент для ~/.cursor/mcp.json (mcp-atlassian-on-prem)."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
SERVER_NAME = "mcp-atlassian-on-prem"


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve_mcp_command() -> tuple[str, list[str]]:
    """Повертає (command, args) для mcp-atlassian у Cursor MCP."""
    direct = Path.home() / ".local" / "bin" / "mcp-atlassian"
    if direct.is_file():
        return str(direct), []
    for uvx in (
        shutil.which("uvx"),
        "/opt/homebrew/bin/uvx",
        str(Path.home() / ".local" / "bin" / "uvx"),
    ):
        if uvx and Path(uvx).is_file():
            return uvx, ["mcp-atlassian"]
    return "uvx", ["mcp-atlassian"]


def main() -> int:
    env = load_dotenv(ENV)
    token = env.get("JIRA_PERSONAL_TOKEN", "").strip()
    if not token:
        print(
            "❌ Немає JIRA_PERSONAL_TOKEN у .env. Запусти: python3 scripts/sync_jira_onprem_keys.py",
            file=sys.stderr,
        )
        return 1

    mcp_env: dict[str, str] = {
        "JIRA_URL": env.get("JIRA_URL", "https://jira.example.com"),
        "JIRA_PERSONAL_TOKEN": token,
    }
    if env.get("CONFLUENCE_URL"):
        mcp_env["CONFLUENCE_URL"] = env["CONFLUENCE_URL"]
        mcp_env["CONFLUENCE_PERSONAL_TOKEN"] = env.get(
            "CONFLUENCE_PERSONAL_TOKEN", token
        )

    command, args = resolve_mcp_command()
    snippet = {
        SERVER_NAME: {
            "command": command,
            "args": args,
            "env": mcp_env,
        }
    }
    print(json.dumps(snippet, indent=2, ensure_ascii=False))
    print(
        f"\n# Встав у ~/.cursor/mcp.json → mcpServers (сервер: {SERVER_NAME})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
