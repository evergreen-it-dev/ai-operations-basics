#!/usr/bin/env python3
"""Синхронізує workspace/keys/jira-onprem → tools/jira/mcp-atlassian/.env."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # Personal (…/tools/jira/mcp-atlassian/scripts/)
if str(ROOT / "tools" / "atlassian") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "atlassian"))
from keys import load_confluence_pat  # noqa: E402

KEYS = ROOT / "workspace" / "keys" / "jira-onprem"
ENV = Path(__file__).resolve().parents[1] / ".env"
EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

DEFAULTS = {
    "JIRA_URL": "https://jira.example.com",
    "CONFLUENCE_URL": "https://jira.example.com/wiki",
}


def parse_keys_file(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            if "JIRA_PERSONAL_TOKEN" not in out and s:
                out["JIRA_PERSONAL_TOKEN"] = s
            continue
        key, _, val = s.partition("=")
        k = key.strip().upper()
        v = val.strip().strip('"').strip("'")
        if k in (
            "JIRA_URL",
            "JIRA_PERSONAL_TOKEN",
            "CONFLUENCE_URL",
            "CONFLUENCE_PERSONAL_TOKEN",
        ):
            out[k] = v
    return out


def upsert_env_line(lines: list[str], key: str, value: str) -> list[str]:
    pat = re.compile(rf"^{re.escape(key)}=")
    replaced = False
    new_lines: list[str] = []
    for ln in lines:
        if pat.match(ln):
            new_lines.append(f"{key}={value}")
            replaced = True
        else:
            new_lines.append(ln)
    if not replaced:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{key}={value}")
    return new_lines


def main() -> int:
    if not KEYS.is_file():
        print(f"Немає файлу {KEYS}", file=sys.stderr)
        print("Шаблон: workspace/keys/jira-onprem.example", file=sys.stderr)
        return 1

    parsed = parse_keys_file(KEYS.read_text(encoding="utf-8"))
    if not parsed.get("JIRA_PERSONAL_TOKEN"):
        print(f"У {KEYS} немає JIRA_PERSONAL_TOKEN (або одного рядка з PAT).", file=sys.stderr)
        return 1

    for k, v in DEFAULTS.items():
        parsed.setdefault(k, v)
    cpat = load_confluence_pat()
    if cpat:
        parsed["CONFLUENCE_PERSONAL_TOKEN"] = cpat
    elif not parsed.get("CONFLUENCE_PERSONAL_TOKEN"):
        parsed["CONFLUENCE_PERSONAL_TOKEN"] = parsed["JIRA_PERSONAL_TOKEN"]

    if ENV.is_file():
        lines = ENV.read_text(encoding="utf-8").splitlines()
    elif EXAMPLE.is_file():
        lines = EXAMPLE.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    for key in (
        "JIRA_URL",
        "JIRA_PERSONAL_TOKEN",
        "CONFLUENCE_URL",
        "CONFLUENCE_PERSONAL_TOKEN",
    ):
        if key in parsed:
            lines = upsert_env_line(lines, key, parsed[key])

    ENV.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Оновлено {ENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
