#!/usr/bin/env python3
"""Спільні інструкції .cursor для Codex, Claude Code і Cursor.

Джерело лишається в `.cursor/`. Codex бачить skills через `.agents/skills`,
Claude Code — через `.claude/`. Індекс rules генерується в AGENTS.md і CLAUDE.md.
Звичайні файли й теки на місці очікуваних symlinks не перезаписуються.

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

LINKS = {
    ".agents/skills": "../.cursor/skills",
    ".claude/skills": "../.cursor/skills",
    ".claude/commands": "../.cursor/commands",
    ".claude/agents": "../.cursor/agents",
}
INDEX_FILES = ("AGENTS.md", "CLAUDE.md")

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
    for name, target in LINKS.items():
        link = ROOT / name
        if not (link.parent / target).resolve().is_dir():
            problems.append(f"{name}: тека-джерело {target} відсутня")
            continue
        if link.exists() and not link.is_symlink():
            problems.append(f"{name}: звичайний файл або тека; збережено без змін")
            continue
        current = link.readlink().as_posix() if link.is_symlink() else None
        if current == target:
            continue
        if check:
            problems.append(f"symlink {name} → {target} відсутній або хибний (зараз: {current})")
            continue
        link.parent.mkdir(exist_ok=True)
        if link.is_symlink():
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


def sync_index(filename: str, check: bool) -> list[str]:
    path = ROOT / filename
    if not path.is_file():
        return [f"{path.name} відсутній — створи його з маркерами {BEGIN}"]
    text = path.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        return [f"{path.name}: потрібна одна пара маркерів {BEGIN} … {END}"]
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
    """Перевірити спільний формат skills: name, description і kebab-case."""
    problems: list[str] = []
    skills = ROOT / ".cursor" / "skills"
    if not skills.is_dir():
        return [".cursor/skills: тека-джерело відсутня"]
    for directory in sorted(skills.iterdir()):
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

    problems = validate_skills()
    if not (ROOT / ".cursor" / "rules").is_dir():
        problems.append(".cursor/rules: тека-джерело відсутня")
    if not problems:
        problems.extend(ensure_links(args.check))
        for filename in INDEX_FILES:
            problems.extend(sync_index(filename, args.check))
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
        f"✓ {verb}: {skills} skills → .agents/skills і .claude/skills; "
        f"{commands} commands, {agents} agents → .claude/; "
        f"rules {len(always)} always-on + {len(on_demand)} за темою → AGENTS.md і CLAUDE.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
