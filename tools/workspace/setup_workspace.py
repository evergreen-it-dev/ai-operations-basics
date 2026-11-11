#!/usr/bin/env python3
"""Створює workspace/ із шаблонів workspace.example/ і записує ОС у workspace/user.md.

Працює однаково на macOS, Linux і Windows. Наявні файли не перезаписує.

Використання:
    python3 tools/workspace/setup_workspace.py      # macOS, Linux
    py -3 tools/workspace/setup_workspace.py        # Windows
"""
from __future__ import annotations

import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "workspace.example"
WORKSPACE = ROOT / "workspace"

# шаблон у workspace.example/ → файл у workspace/
FILES = {
    "user.md.example": "user.md",
    "personas.md.example": "personas.md",
    "my_voice.md.example": "my_voice.md",
    "teams-access.yaml": "teams-access.yaml",
    "teams-chats.yaml": "teams-chats.yaml",
    "telegram-access.yaml": "telegram-access.yaml",
    "TASKS.md.example": "TASKS.md",
    "operations.md.example": "operations.md",
    "keys/google.example": "keys/google",
    "keys/jira-onprem.example": "keys/jira-onprem",
    "keys/folio.example": "keys/folio",
    "keys/telegram.example": "keys/telegram",
    "keys/confluence.example": "keys/confluence",
    "keys/figma.example": "keys/figma",
}
DIRS = ("keys", "memory")

OS_LINE = re.compile(r"^- \*\*OS:\*\*.*$", re.M)
TZ_LINE = re.compile(r"^- \*\*Timezone:\*\*.*$", re.M)


def detect_os() -> str:
    system = platform.system()
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(system, system.lower())


def write_os(user_md: Path, os_name: str) -> None:
    text = user_md.read_text(encoding="utf-8")
    line = f"- **OS:** {os_name}"
    if OS_LINE.search(text):
        updated = OS_LINE.sub(line, text, count=1)
    elif TZ_LINE.search(text):
        updated = TZ_LINE.sub(lambda m: f"{m.group(0)}\n{line}", text, count=1)
    else:
        updated = text.rstrip("\n") + f"\n{line}\n"
    if updated != text:
        user_md.write_text(updated, encoding="utf-8", newline="\n")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for name in DIRS:
        (WORKSPACE / name).mkdir(parents=True, exist_ok=True)

    created, kept = [], []
    for src, dst in FILES.items():
        source, target = EXAMPLE / src, WORKSPACE / dst
        if not source.is_file():
            print(f"! шаблону немає: workspace.example/{src}")
            continue
        if target.exists():
            kept.append(dst)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        created.append(dst)

    os_name = detect_os()
    user_md = WORKSPACE / "user.md"
    if user_md.is_file():
        write_os(user_md, os_name)

    print(f"ОС: {os_name} (записано в workspace/user.md)")
    if created:
        print("Створено: " + ", ".join(created))
    if kept:
        print("Вже були, не чіпав: " + ", ".join(kept))
    print("Далі заміни плейсхолдери у workspace/. Секрети в git не класти.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
