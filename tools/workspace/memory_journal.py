#!/usr/bin/env python3
"""Append-only YAML operation journal shared by Cursor hooks and Workspace UI."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 2
MAX_TEXT_CHARS = 50_000

_SECRET_PATTERNS = (
    re.compile(r"\b(?:api[_-]?key|secret|token|password|passwd)\s*[:=]\s*\S+", re.I),
    re.compile(r"\bcursor_[a-z0-9_-]{10,}\b", re.I),
    re.compile(r"\bsk-[a-z0-9]{10,}\b", re.I),
    re.compile(r"workspace/keys/[^\s\"'`]+", re.I),
    re.compile(r"\bSECRET_KEY\b"),
)
_FRUSTRATION_RE = re.compile(
    r"\b(?:не\s*нрав|не\s*подоба|бессмыс|безглузд|слабо|нелогич|"
    r"жахлив|ужас|уебищ|лайно|злю|злит|дратує|раздраж|почему-то\s+ничего|"
    r"нічого\s+не|не\s+работ|не\s+працю)\w*",
    re.I,
)
_MISTAKE_RE = re.compile(
    r"\b(?:ошиб|помил|неправил|не\s+прочитал|не\s+прочитав|"
    r"пропустил|пропустив|сломал|зламав|потерял|втратив)\w*",
    re.I,
)
_CORRECTION_RE = re.compile(
    r"\b(?:исправ|виправ|передел|перероб|сделай\s+лучше|зроби\s+краще|"
    r"давай\s+заново|ще\s+раз)\w*",
    re.I,
)
_STATE_LOSS_RE = re.compile(
    r"\b(?:пропада|теря|втрача|не\s+сохраня|не\s+зберіга|localstorage|state)\w*",
    re.I,
)
_UI_RE = re.compile(r"\b(?:ui|ux|интерфейс|інтерфейс|кнопк|activity|екран|экран)\w*", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_operation_id(prefix: str = "op") -> str:
    return f"{prefix}_{uuid4().hex}"


def redact_text(value: str) -> str:
    text = value
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    if len(text) > MAX_TEXT_CHARS:
        text = text[: MAX_TEXT_CHARS - 20] + "\n[TRUNCATED]"
    return text


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_value(item) for key, item in value.items()}
    return value


def _sentences(text: str) -> list[str]:
    compact = " ".join(text.split())
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?…])\s+|\n+", compact)
        if part.strip()
    ]


def analyze_user_feedback(prompt: str) -> dict[str, Any]:
    signals: list[str] = []
    if _FRUSTRATION_RE.search(prompt):
        signals.append("explicit_dissatisfaction")
    if _MISTAKE_RE.search(prompt):
        signals.append("agent_mistake_reported")
    if _CORRECTION_RE.search(prompt):
        signals.append("correction_requested")
    if _STATE_LOSS_RE.search(prompt):
        signals.append("state_loss_reported")
    if _UI_RE.search(prompt) and signals:
        signals.append("ui_friction")

    complaints = [
        redact_text(sentence[:500])
        for sentence in _sentences(prompt)
        if _FRUSTRATION_RE.search(sentence)
        or _MISTAKE_RE.search(sentence)
        or _STATE_LOSS_RE.search(sentence)
    ][:5]
    corrections = [
        redact_text(sentence[:500])
        for sentence in _sentences(prompt)
        if _CORRECTION_RE.search(sentence)
    ][:5]

    return {
        "sentiment": "frustrated" if "explicit_dissatisfaction" in signals else "unknown",
        "about_previous_agent_output": bool(signals),
        "signals": signals,
        "complaints": complaints,
        "corrections_requested": corrections,
        "observation": "deterministic_from_user_prompt",
    }


def _workspace_owner(root: Path) -> str | None:
    user_file = root / "workspace" / "user.md"
    try:
        text = user_file.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^\s*-\s+\*\*Name:\*\*\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip() if match else None


def _enrich_operation(root: Path, operation: dict[str, Any]) -> dict[str, Any]:
    enriched = redact_value(operation)
    enriched.setdefault("id", new_operation_id())
    enriched.setdefault("schema_version", SCHEMA_VERSION)
    enriched.setdefault("started_at", now_iso())
    enriched.setdefault("completed_at", enriched["started_at"])

    actor = enriched.setdefault("actor", {})
    initiator = actor.setdefault("initiator", {"type": "user"})
    if not initiator.get("display_name"):
        owner = _workspace_owner(root)
        if owner:
            initiator["display_name"] = owner
    actor.setdefault(
        "executor",
        {
            "type": "cursor_agent",
            "interface": "unknown",
        },
    )

    enriched.setdefault("source", {"surface": "unknown"})
    enriched.setdefault("request", {"prompt": "", "summary": ""})
    enriched.setdefault(
        "execution",
        {
            "iterations": {"count": 1, "observation": "unavailable"},
            "tools": {"calls": 0, "failures": 0, "by_name": {}},
            "subagents": {"count": 0, "failures": 0},
            "errors": [],
        },
    )
    enriched.setdefault("outcome", {"status": "unknown", "summary": ""})
    enriched.setdefault("feedback", analyze_user_feedback(enriched["request"].get("prompt", "")))
    enriched.setdefault("capabilities", [])
    enriched.setdefault("artifacts", [])
    enriched.setdefault("tags", [])
    return enriched


def _scalar(value: Any, indent: int) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if "\n" in text or len(text) > 140:
        pad = " " * (indent + 2)
        lines = text.splitlines() or [""]
        return "|-\n" + "\n".join(f"{pad}{line}" for line in lines)
    return json.dumps(text, ensure_ascii=False)


def _dump_mapping(value: dict[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    pad = " " * indent
    for key, item in value.items():
        if isinstance(item, dict):
            if item:
                lines.append(f"{pad}{key}:")
                lines.extend(_dump_mapping(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {{}}")
        elif isinstance(item, list):
            if item:
                lines.append(f"{pad}{key}:")
                lines.extend(_dump_list(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: []")
        else:
            lines.append(f"{pad}{key}: {_scalar(item, indent)}")
    return lines


def _dump_list(value: list[Any], indent: int) -> list[str]:
    lines: list[str] = []
    pad = " " * indent
    for item in value:
        if isinstance(item, dict):
            items = list(item.items())
            if not items:
                lines.append(f"{pad}- {{}}")
                continue
            first_key, first_value = items[0]
            if isinstance(first_value, (dict, list)):
                lines.append(f"{pad}- {first_key}:")
                nested = (
                    _dump_mapping(first_value, indent + 4)
                    if isinstance(first_value, dict)
                    else _dump_list(first_value, indent + 4)
                )
                lines.extend(nested)
            else:
                lines.append(f"{pad}- {first_key}: {_scalar(first_value, indent)}")
            lines.extend(_dump_mapping(dict(items[1:]), indent + 2))
        elif isinstance(item, list):
            lines.append(f"{pad}-")
            lines.extend(_dump_list(item, indent + 2))
        else:
            lines.append(f"{pad}- {_scalar(item, indent)}")
    return lines


def dump_operation(operation: dict[str, Any]) -> str:
    lines = _dump_list([operation], 2)
    return "\n".join(lines) + "\n"


def append_operation(root: Path, operation: dict[str, Any]) -> Path:
    root = root.resolve()
    operation = _enrich_operation(root, operation)
    started = str(operation.get("started_at") or now_iso())
    day = started[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", started) else date.today().isoformat()
    memory_dir = root / "workspace" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    target = memory_dir / f"{day}.yaml"
    lock_path = memory_dir / ".journal.lock"

    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not target.exists():
            target.write_text(
                f"schema_version: {SCHEMA_VERSION}\ndate: {json.dumps(day)}\noperations:\n",
                encoding="utf-8",
            )
        with target.open("a", encoding="utf-8") as stream:
            stream.write(dump_operation(operation))
            stream.flush()
            os.fsync(stream.fileno())
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return target


_LEGACY_BLOCK_RE = re.compile(
    r"### (\d{2}:\d{2})\s*\n\s*\n- \*\*Задача:\*\* (.+?)\n"
    r"- \*\*(?:Сделано|Зроблено):\*\* (.+?)(?=\n\n### |\Z)",
    re.S,
)


def migrate_legacy_markdown(root: Path, day: str) -> Path | None:
    source = root / "workspace" / "memory" / f"{day}.md"
    if not source.is_file():
        return None
    raw = source.read_text(encoding="utf-8")
    for time_value, task, done in _LEGACY_BLOCK_RE.findall(raw):
        append_operation(
            root,
            {
                "id": new_operation_id("legacy"),
                "started_at": f"{day}T{time_value}:00",
                "completed_at": f"{day}T{time_value}:00",
                "actor": {
                    "initiator": {"type": "user"},
                    "executor": {
                        "type": "cursor_agent",
                        "interface": "legacy_cursor_hook",
                    },
                },
                "source": {
                    "surface": "cursor_ide",
                    "channel": "agent_chat",
                    "format": "legacy_markdown_import",
                },
                "request": {
                    "prompt": " ".join(task.split()),
                    "summary": " ".join(task.split()),
                    "prompt_observation": "legacy_summary_only",
                },
                "execution": {
                    "iterations": {"count": None, "observation": "unavailable"},
                    "tools": {"calls": None, "failures": None, "by_name": {}},
                    "subagents": {"count": None, "failures": None},
                    "errors": [],
                },
                "outcome": {
                    "status": "unknown",
                    "summary": " ".join(done.split()),
                    "response_observation": "legacy_summary_only",
                },
                "feedback": analyze_user_feedback(task),
                "capabilities": [],
                "artifacts": [],
                "tags": ["legacy-import"],
            },
        )
    legacy = source.with_suffix(".md.legacy")
    source.rename(legacy)
    return legacy


def extract_search_events(path: Path) -> list[tuple[str, str]]:
    """Cheap backfill input for onboarding; the TypeScript extractor parses full YAML."""
    day = path.stem[:10]
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    chunks = re.split(r"(?m)^  - id: ", raw)[1:]
    return [(day, chunk) for chunk in chunks]


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace operation memory journal")
    sub = parser.add_subparsers(dest="command", required=True)
    append_parser = sub.add_parser("append")
    append_parser.add_argument("--root", type=Path, required=True)
    migrate_parser = sub.add_parser("migrate-md")
    migrate_parser.add_argument("--root", type=Path, required=True)
    migrate_parser.add_argument("--date", required=True)
    args = parser.parse_args()

    if args.command == "append":
        try:
            payload = json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            return 1
        append_operation(args.root, payload)
        return 0
    if args.command == "migrate-md":
        migrated = migrate_legacy_markdown(args.root, args.date)
        return 0 if migrated else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
