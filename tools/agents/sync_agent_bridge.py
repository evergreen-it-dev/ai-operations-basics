#!/usr/bin/env python3
"""Міст .cursor → .claude: symlinks на skills/commands/agents + індекс rules у CLAUDE.md.

Source of truth лишається в `.cursor/`. Claude Code бачить skills/commands/agents
через symlinks, а rules (`*.mdc`, які Claude Code не читає сам) — через згенерований
індекс у `CLAUDE.md` між маркерами.

Використання:
    python3 tools/agents/sync_agent_bridge.py           # застосувати зміни
    python3 tools/agents/sync_agent_bridge.py --check   # лише перевірити (exit 1 при розбіжності)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LINKS = {"skills": "../.cursor/skills", "commands": "../.cursor/commands", "agents": "../.cursor/agents"}

BEGIN = "<!-- BEGIN GENERATED: rules-index (tools/agents/sync_agent_bridge.py) -->"
END = "<!-- END GENERATED: rules-index -->"


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Мінімальний YAML-frontmatter парсер: скалярні поля + folded (>-) блоки."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    out: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for line in match.group(1).split("\n"):
        head = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if head:
            if key:
                out[key] = " ".join(buf).strip()
            key = head.group(1)
            value = head.group(2).strip()
            # `>-`, `|`, `>+2` тощо — індикатори блоку, а не текст
            value = re.sub(r"^[>|][-+]?\d*\s*", "", value)
            buf = [value] if value else []
        elif key is not None:
            buf.append(line.strip())
    if key:
        out[key] = " ".join(buf).strip()
    return out


def ensure_links(check: bool) -> list[str]:
    problems: list[str] = []
    claude = ROOT / ".claude"
    if not check:
        claude.mkdir(exist_ok=True)
    for name, target in LINKS.items():
        link = claude / name
        current = link.readlink().as_posix() if link.is_symlink() else None
        if current == target:
            continue
        if check:
            problems.append(f"symlink .claude/{name} → {target} відсутній або хибний (зараз: {current})")
            continue
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    return problems


def collect_rules() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(always_on, on_demand); кожен елемент — (slug, description)."""
    always: list[tuple[str, str]] = []
    on_demand: list[tuple[str, str]] = []
    for path in sorted((ROOT / ".cursor" / "rules").rglob("*.mdc")):
        meta = parse_frontmatter(path)
        slug = path.relative_to(ROOT / ".cursor" / "rules").with_suffix("").as_posix()
        desc = " ".join((meta.get("description") or "").split())
        bucket = always if meta.get("alwaysApply", "").lower() == "true" else on_demand
        bucket.append((slug, desc))
    return always, on_demand


def render_index() -> str:
    always, on_demand = collect_rules()
    lines = [BEGIN, ""]
    lines.append("### Завжди застосовувати (`alwaysApply: true`)")
    lines.append("")
    lines.append("Прочитай ці файли на початку сесії — вони задають мову, контекст і поведінку:")
    lines.append("")
    for slug, desc in always:
        lines.append(f"- **[`{slug}`](.cursor/rules/{slug}.mdc)** — {desc}")
    lines.append("")
    lines.append("### За темою (`alwaysApply: false`)")
    lines.append("")
    lines.append("Відкрий правило, коли тема запиту збігається з описом:")
    lines.append("")
    lines.append("| Rule | Коли читати |")
    lines.append("|------|-------------|")
    for slug, desc in on_demand:
        lines.append(f"| [`{slug}`](.cursor/rules/{slug}.mdc) | {desc} |")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def sync_claude_md(check: bool) -> list[str]:
    path = ROOT / "CLAUDE.md"
    if not path.is_file():
        return [f"{path.name} відсутній — створи його з маркерами {BEGIN}"]
    text = path.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return [f"{path.name}: немає маркерів {BEGIN} … {END}"]
    updated = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END),
        lambda _: render_index(),
        text,
        flags=re.S,
    )
    if updated == text:
        return []
    if check:
        return [f"{path.name}: індекс rules застарів"]
    path.write_text(updated, encoding="utf-8")
    return []


def validate_skills() -> list[str]:
    """Claude Code вимагає name == ім'я теки і kebab-case."""
    problems: list[str] = []
    for directory in sorted((ROOT / ".cursor" / "skills").iterdir()):
        if not directory.is_dir():
            continue
        skill = directory / "SKILL.md"
        if not skill.is_file():
            problems.append(f"{directory.name}: немає SKILL.md")
            continue
        meta = parse_frontmatter(skill)
        name = meta.get("name", "")
        if not name:
            problems.append(f"{directory.name}: немає поля name")
        elif name != directory.name:
            problems.append(f"{directory.name}: name '{name}' не збігається з текою")
        elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            problems.append(f"{directory.name}: name не kebab-case")
        if not meta.get("description"):
            problems.append(f"{directory.name}: немає поля description")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="лише перевірити, нічого не писати")
    args = parser.parse_args()

    problems = ensure_links(args.check) + sync_claude_md(args.check) + validate_skills()
    if problems:
        for item in problems:
            print(f"✗ {item}", file=sys.stderr)
        return 1

    always, on_demand = collect_rules()
    skills = sum(1 for item in (ROOT / ".cursor" / "skills").iterdir() if item.is_dir())
    commands = len(list((ROOT / ".cursor" / "commands").glob("*.md")))
    agents = len(list((ROOT / ".cursor" / "agents").glob("*.md")))
    verb = "перевірено" if args.check else "синхронізовано"
    print(
        f"✓ {verb}: {skills} skills, {commands} commands, {agents} agents (symlinks); "
        f"rules {len(always)} always-on + {len(on_demand)} за темою → CLAUDE.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
