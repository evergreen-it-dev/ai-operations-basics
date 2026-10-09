#!/usr/bin/env python3
"""Agent hook telemetry → unified workspace/memory/YYYY-MM-DD.yaml.

Дефолти — Cursor IDE. Інший клієнт (напр. Claude Code через
`.claude/hooks/claude_memory_turn.py`) нормалізує свій payload під ці ж
handler-и та перевизначає ідентичність середовища через env
`AGENT_MEMORY_SURFACE` / `AGENT_MEMORY_EXECUTOR` / `AGENT_MEMORY_TAG`.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

STATE_REL = Path(".cursor/hooks/state")
RUN_STATE_DIR = "memory-runs"
LEGACY_LAST_PROMPT = "last_user_prompt.json"

# Ідентичність середовища — перевизначається клієнтом-адаптером через env
SURFACE_DEFAULTS = {
    "surface": "cursor_ide",
    "executor": "cursor_agent",
    "tag": "cursor-ide",
}

# Ліміти «суті», не довжини дампу
MAX_TASK_CHARS = 260
MAX_DONE_CHARS = 520
MAX_STORED_PROMPT_CHARS = 50_000
MAX_STORED_RESPONSE_CHARS = 50_000

# Заголовки секцій з результатом (укр/рус/en)
_SECTION_HEAD = (
    r"(?:Що зроблено|Що змінено|Що вийшло|Результат|Підсумок|Ітог|"
    r"Что сделано|Что изменилось|Итог|Сделано|Резюме|"
    r"Кратко[, ]*(?:что|що)\s+(?:сделано|зроблено|змінено)|"
    r"Summary|Changes|Result|Outcome|Fix|Update)"
)

# Перший абзац відповіді часто — ввідне «Ось що…»; пропускаємо, якщо короткий і шаблонний
_INTRO_HINTS = (
    "ось ", "кратко", "нижче", "below", "here's", "here is",
    "давайте", "спочатку", "коротко", "у двох словах",
)


def project_root(data: dict[str, Any]) -> Optional[Path]:
    roots = data.get("workspace_roots") or []
    if roots:
        return Path(str(roots[0])).resolve()
    env = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return None


def _journal_module(root: Path):
    tools_dir = root / "tools" / "workspace"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from memory_journal import (  # type: ignore[import-not-found]
        analyze_user_feedback,
        append_operation,
        redact_text,
    )

    return analyze_user_feedback, append_operation, redact_text


def _safe_id(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return cleaned[:160] or fallback


def _state_path(root: Path, data: dict[str, Any]) -> Path:
    conversation = _safe_id(str(data.get("conversation_id") or "legacy"), "legacy")
    generation = _safe_id(str(data.get("generation_id") or "latest"), "latest")
    return root / STATE_REL / RUN_STATE_DIR / conversation / f"{generation}.json"


def _latest_state_path(root: Path, data: dict[str, Any]) -> Path:
    direct = _state_path(root, data)
    if direct.is_file():
        return direct
    conversation = _safe_id(str(data.get("conversation_id") or "legacy"), "legacy")
    directory = root / STATE_REL / RUN_STATE_DIR / conversation
    candidates = sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ) if directory.is_dir() else []
    return candidates[0] if candidates else direct


def _previous_operation_id(root: Path, data: dict[str, Any]) -> str | None:
    conversation = _safe_id(str(data.get("conversation_id") or "legacy"), "legacy")
    directory = root / STATE_REL / RUN_STATE_DIR / conversation
    if not directory.is_dir():
        return None
    candidates = sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        state = _read_state(candidate)
        operation_id = state.get("operation_id")
        if operation_id:
            return str(operation_id)
    return None


def _surface(key: str) -> str:
    return os.environ.get(f"AGENT_MEMORY_{key.upper()}") or SURFACE_DEFAULTS[key]


def _read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _hydrate_legacy_state(root: Path, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Bridge turns that started before the structured hook deployment."""
    if state.get("prompt"):
        return state
    legacy = _read_state(root / STATE_REL / LEGACY_LAST_PROMPT)
    prompt = str(legacy.get("prompt") or "")
    if not prompt:
        return state
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "operation_id": f"ide_{uuid4().hex}",
        "prompt": prompt,
        "prompt_summary": _gist_user_task(prompt, MAX_TASK_CHARS),
        "started_at": legacy.get("saved_at") or now,
        "conversation_id": data.get("conversation_id"),
        "generation_id": data.get("generation_id"),
        "previous_operation_id": _previous_operation_id(root, data),
        "model": data.get("model"),
        "cursor_version": data.get("cursor_version"),
        "user_email": data.get("user_email"),
        "transcript_path": data.get("transcript_path"),
        "attachments": [],
        "assistant_response": "",
        "assistant_summary": "",
        "assistant_messages": 0,
        "thinking": {"blocks": 0, "duration_ms": 0},
        "tools": {"calls": 0, "failures": 0, "duration_ms": 0, "by_name": {}},
        "subagents": {"count": 0, "failures": 0, "duration_ms": 0, "types": {}},
        "errors": [],
        **state,
    }


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _update_state(root: Path, data: dict[str, Any], mutator) -> dict[str, Any]:
    path = _latest_state_path(root, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = _hydrate_legacy_state(root, data, _read_state(path))
        mutator(state)
        _write_state(path, state)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return state


def _short(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars].rsplit(" ", 1)[0]
    if len(cut) < max_chars // 3:
        cut = text[: max_chars - 1]
    return cut.rstrip(" ,;—-") + "…"


def _one_line(text: str) -> str:
    """Один рядок для логу: без переносів, зайвих пробілів."""
    return " ".join(text.split())


def _strip_code_fences(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", " ", text)


def _gist_user_task(prompt: str, max_chars: int) -> str:
    """Коротка суть запиту: 1–2 повні речення, без обриву посеред слова."""
    p = _strip_code_fences(prompt).strip()
    p = " ".join(p.split())
    if not p:
        return "—"
    if len(p) <= max_chars:
        return p
    # Розбити на речення (наївно, без складних абревіатур)
    chunks = re.split(r"(?<=[.!?…])\s+", p)
    out: list[str] = []
    n = 0
    for ch in chunks:
        ch = ch.strip()
        if not ch:
            continue
        trial = (" ".join(out + [ch])).strip() if out else ch
        if len(trial) > max_chars and out:
            break
        out.append(ch)
        n += 1
        if n >= 2:
            break
    result = " ".join(out).strip()
    if not result or len(result) < 12:
        return _short(p, max_chars)
    if len(result) > max_chars:
        return _short(result, max_chars)
    return result


def _strip_md_noise(line: str) -> str:
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"#+\s*", "", s)
    return s.strip()


def _bullets_from_block(block: str, max_items: int, budget: int) -> str:
    lines = []
    for ln in block.splitlines():
        t = ln.strip()
        if t.startswith("- ") or t.startswith("* ") or t.startswith("• "):
            lines.append(_strip_md_noise(t[2:].strip()))
        elif re.match(r"^\d+\.\s+", t):
            lines.append(_strip_md_noise(re.sub(r"^\d+\.\s+", "", t)))
    if not lines:
        return ""
    picked: list[str] = []
    total = 0
    for item in lines:
        if len(item) < 4:
            continue
        sep = " · " if picked else ""
        if total + len(sep) + len(item) > budget and picked:
            break
        picked.append(item)
        total += len(sep) + len(item)
        if len(picked) >= max_items:
            break
    return " · ".join(picked)


def _gist_assistant_done(text: str, max_chars: int) -> str:
    """Суть відповіді: секція результату, список змін, або тіло після першого ##."""
    t = text.strip()
    if not t:
        return "—"
    t_clean = _strip_code_fences(t)
    # 1) Явна секція «що зроблено / итог …» (до наступного рядка ^## — без ### у lookahead,
    #    щоб не обрізати тіло на хибних збігах)
    pat = rf"(?ms)^##[ \t]*{_SECTION_HEAD}[^\n]*\n(.*?)(?=^##[ \t]|\Z)"
    m = re.search(pat, t_clean, re.I)
    if m:
        body = m.group(1).strip()
        bullets = _bullets_from_block(body, max_items=6, budget=max_chars - 10)
        if bullets:
            return _one_line(_short(bullets, max_chars))
        flat = " ".join(body.split())
        if len(flat) > 40:
            return _one_line(_short(flat, max_chars))
    # 2) Підзаголовок ### Що зроблено / Итог
    pat3 = rf"(?ms)^###[ \t]*{_SECTION_HEAD}[^\n]*\n(.*?)(?=^(?:##|###)[ \t]|\Z)"
    m3 = re.search(pat3, t_clean, re.I)
    if m3:
        body = m3.group(1).strip()
        bullets = _bullets_from_block(body, max_items=5, budget=max_chars - 10)
        if bullets:
            return _one_line(_short(bullets, max_chars))
        flat = " ".join(body.split())
        if len(flat) > 30:
            return _one_line(_short(flat, max_chars))
    # 3) Перший блок після будь-якого ##
    m2 = re.search(r"(?ms)^##[ \t]+[^\n]+\n(.*?)(?=^##[ \t]|\Z)", t_clean)
    if m2:
        body = m2.group(1).strip()
        bullets = _bullets_from_block(body, max_items=6, budget=max_chars - 10)
        if bullets:
            return _one_line(_short(bullets, max_chars))
        flat = " ".join(body.split())
        if len(flat) > 50:
            return _one_line(_short(flat, max_chars))
    # 4) Абзаци: пропустити коротке вступне
    paras = [p.strip() for p in re.split(r"\n\s*\n", t_clean) if p.strip()]
    body_parts: list[str] = []
    for i, p in enumerate(paras):
        if i == 0 and len(p) < 200 and not p.lstrip().startswith("#"):
            low = p[:100].lower()
            if any(h in low for h in _INTRO_HINTS):
                continue
        body_parts.append(p)
        if len(body_parts) >= 2:
            break
    merged = " ".join(" ".join(x.split()) for x in body_parts[:3])
    merged = " ".join(merged.split())
    if len(merged) < 25 and paras:
        merged = " ".join(" ".join(x.split()) for x in paras[:2])
    return _one_line(_short(merged, max_chars))


def _read_cursor_api_key(root: Path) -> Optional[str]:
    path = root / "workspace" / "keys" / "cursor"
    if path.is_file():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key
    env_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    return env_key or None


def _agent_binary() -> Optional[str]:
    for name in ("agent", "cursor-agent"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _summarize_with_agent(
    root: Path, user_prompt: str, assistant: str
) -> Optional[tuple[str, str]]:
    """Cursor CLI: https://cursor.com/docs/cli/overview — потрібен CURSOR_API_KEY або workspace/keys/cursor."""
    api_key = _read_cursor_api_key(root)
    agent_exe = _agent_binary()
    if not api_key or not agent_exe:
        return None
    up = user_prompt[:8000]
    ar = assistant[:16000]
    instructions = (
        "Ти допомагаєш вести журнал діалогу. За двома фрагментами нижче дай РІВНО два рядки, "
        "без markdown, без преамбули.\n"
        "Задача — суть запиту користувача (що зробити / що зʼясувати).\n"
        "Сделано — суть відповіді асистента (що зроблено, які файли/команди, результат).\n\n"
        "Формат відповіді СТРОГО (одна фраза після двокрапки на рядок):\n"
        "Задача: ...\n"
        "Сделано: ...\n\n"
        "--- Повідомлення користувача ---\n"
        f"{up}\n\n"
        "--- Відповідь асистента ---\n"
        f"{ar}\n"
    )
    env = {**os.environ, "CURSOR_API_KEY": api_key}
    try:
        proc = subprocess.run(
            [
                agent_exe,
                "-p",
                instructions,
                "--print",
                "--output-format",
                "text",
                "--trust",
                "--model",
                "auto",
            ],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    task: Optional[str] = None
    done: Optional[str] = None
    for line in out.splitlines():
        line = line.strip()
        low = line.lower()
        if low.startswith("задача:"):
            task = line.split(":", 1)[1].strip()
        elif low.startswith("сделано:") or low.startswith("зроблено:"):
            done = line.split(":", 1)[1].strip()
    if task and done and len(task) > 2 and len(done) > 2:
        return (_one_line(_short(task, MAX_TASK_CHARS)), _one_line(_short(done, MAX_DONE_CHARS)))
    return None


def _update_onboarding_yaml(root: Path, user_prompt: str, assistant: str, day: str) -> None:
    """Інкремент use_count у workspace/onboarding.yaml (як memory, без секретів)."""
    if (os.environ.get("ONBOARDING_LOG_NO_HOOK") or "").strip().lower() in ("1", "true", "yes"):
        return
    onboarding_yaml = root / "workspace" / "onboarding.yaml"
    if not onboarding_yaml.is_file():
        return
    update_script = root / "tools" / "workspace" / "onboarding_update.py"
    if not update_script.is_file():
        return
    payload = json.dumps(
        {"prompt": user_prompt, "response": assistant, "date": day, "root": str(root)},
        ensure_ascii=False,
    )
    try:
        subprocess.run(
            [sys.executable, str(update_script), "--turn"],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def handle_before_submit(data: dict[str, Any]) -> None:
    root = project_root(data)
    if not root:
        return
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return
    _, _, redact_text = _journal_module(root)
    prompt = redact_text(prompt[:MAX_STORED_PROMPT_CHARS])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "operation_id": f"ide_{uuid4().hex}",
        "prompt": prompt,
        "prompt_summary": _gist_user_task(prompt, MAX_TASK_CHARS),
        "started_at": now,
        "conversation_id": data.get("conversation_id"),
        "generation_id": data.get("generation_id"),
        "previous_operation_id": _previous_operation_id(root, data),
        "model": data.get("model"),
        "cursor_version": data.get("cursor_version") or os.environ.get("CURSOR_VERSION"),
        "user_email": data.get("user_email") or os.environ.get("CURSOR_USER_EMAIL"),
        "transcript_path": data.get("transcript_path") or os.environ.get("CURSOR_TRANSCRIPT_PATH"),
        "attachments": [
            {
                "type": item.get("type"),
                "path": Path(str(item.get("file_path") or "")).name,
            }
            for item in data.get("attachments", [])
            if isinstance(item, dict)
        ],
        "assistant_response": "",
        "assistant_summary": "",
        "assistant_messages": 0,
        "thinking": {"blocks": 0, "duration_ms": 0},
        "tools": {"calls": 0, "failures": 0, "duration_ms": 0, "by_name": {}},
        "subagents": {"count": 0, "failures": 0, "duration_ms": 0, "types": {}},
        "errors": [],
    }
    _write_state(_state_path(root, data), payload)


def handle_after_response(data: dict[str, Any]) -> None:
    root = project_root(data)
    if not root:
        return
    assistant = (data.get("text") or "").strip()
    day = datetime.now().strftime("%Y-%m-%d")
    state_path = _latest_state_path(root, data)
    state = _hydrate_legacy_state(root, data, _read_state(state_path))
    user_prompt = str(state.get("prompt") or "")
    _, _, redact_text = _journal_module(root)
    assistant = redact_text(assistant[:MAX_STORED_RESPONSE_CHARS])

    use_agent = (
        os.environ.get("MEMORY_LOG_NO_AGENT", "").strip().lower()
        not in ("1", "true", "yes")
    )
    pair: Optional[tuple[str, str]] = None
    if use_agent:
        pair = _summarize_with_agent(root, user_prompt, assistant)
    task = pair[0] if pair else _gist_user_task(user_prompt, MAX_TASK_CHARS)
    done = pair[1] if pair else _gist_assistant_done(assistant, MAX_DONE_CHARS)

    state.update(
        {
            "prompt_summary": task,
            "assistant_response": assistant,
            "assistant_summary": done,
            "assistant_messages": int(state.get("assistant_messages") or 0) + 1,
            "model": data.get("model") or state.get("model"),
        }
    )
    _write_state(state_path, state)
    _update_onboarding_yaml(root, user_prompt, assistant, day)


def handle_tool_result(data: dict[str, Any], *, failed: bool) -> None:
    root = project_root(data)
    if not root:
        return

    def mutate(state: dict[str, Any]) -> None:
        tools = state.setdefault(
            "tools",
            {"calls": 0, "failures": 0, "duration_ms": 0, "by_name": {}},
        )
        name = str(data.get("tool_name") or "unknown")
        by_name = tools.setdefault("by_name", {})
        item = by_name.setdefault(name, {"calls": 0, "failures": 0, "duration_ms": 0})
        tools["calls"] = int(tools.get("calls") or 0) + 1
        item["calls"] = int(item.get("calls") or 0) + 1
        duration = int(data.get("duration") or 0)
        tools["duration_ms"] = int(tools.get("duration_ms") or 0) + duration
        item["duration_ms"] = int(item.get("duration_ms") or 0) + duration
        if failed:
            tools["failures"] = int(tools.get("failures") or 0) + 1
            item["failures"] = int(item.get("failures") or 0) + 1
            _, _, redact_text = _journal_module(root)
            state.setdefault("errors", []).append(
                {
                    "stage": "tool",
                    "tool": name,
                    "type": data.get("failure_type") or "error",
                    "message": redact_text(str(data.get("error_message") or "Tool failed")),
                    "duration_ms": duration,
                    "recovered": None,
                }
            )

    _update_state(root, data, mutate)


def handle_subagent_stop(data: dict[str, Any]) -> None:
    root = project_root(data)
    if not root:
        return

    def mutate(state: dict[str, Any]) -> None:
        subagents = state.setdefault(
            "subagents",
            {"count": 0, "failures": 0, "duration_ms": 0, "types": {}},
        )
        agent_type = str(data.get("subagent_type") or "unknown")
        subagents["count"] = int(subagents.get("count") or 0) + 1
        subagents["duration_ms"] = int(subagents.get("duration_ms") or 0) + int(
            data.get("duration_ms") or 0
        )
        types = subagents.setdefault("types", {})
        types[agent_type] = int(types.get(agent_type) or 0) + 1
        if data.get("status") in ("error", "aborted"):
            subagents["failures"] = int(subagents.get("failures") or 0) + 1
            state.setdefault("errors", []).append(
                {
                    "stage": "subagent",
                    "tool": agent_type,
                    "type": data.get("status"),
                    "message": _short(str(data.get("summary") or "Subagent failed"), 500),
                    "duration_ms": int(data.get("duration_ms") or 0),
                    "recovered": None,
                }
            )

    _update_state(root, data, mutate)


def handle_agent_thought(data: dict[str, Any]) -> None:
    root = project_root(data)
    if not root:
        return

    def mutate(state: dict[str, Any]) -> None:
        thinking = state.setdefault("thinking", {"blocks": 0, "duration_ms": 0})
        thinking["blocks"] = int(thinking.get("blocks") or 0) + 1
        thinking["duration_ms"] = int(thinking.get("duration_ms") or 0) + int(
            data.get("duration_ms") or 0
        )

    _update_state(root, data, mutate)


def handle_stop(data: dict[str, Any]) -> None:
    root = project_root(data)
    if not root:
        return
    state_path = _latest_state_path(root, data)
    state = _hydrate_legacy_state(root, data, _read_state(state_path))
    if not state or state.get("journaled"):
        return
    analyze_user_feedback, append_operation, _ = _journal_module(root)
    prompt = str(state.get("prompt") or "")
    status = str(data.get("status") or "unknown")
    loop_count = int(data.get("loop_count") or 0)
    errors = list(state.get("errors") or [])
    if status == "error":
        errors.append(
            {
                "stage": "agent_loop",
                "type": "error",
                "message": f"{_surface('surface')} agent loop ended with error",
                "recovered": None,
            }
        )

    operation = {
        "id": state.get("operation_id"),
        "started_at": state.get("started_at"),
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "actor": {
            "initiator": {
                "type": "user",
                "email": state.get("user_email"),
            },
            "executor": {
                "type": _surface("executor"),
                "interface": _surface("surface"),
                "model": data.get("model") or state.get("model"),
            },
        },
        "source": {
            "surface": _surface("surface"),
            "channel": "agent_chat",
            "conversation_id": state.get("conversation_id"),
            "generation_id": state.get("generation_id"),
            "cursor_version": state.get("cursor_version"),
            "transcript_available": bool(state.get("transcript_path")),
        },
        "request": {
            "prompt": prompt,
            "summary": state.get("prompt_summary") or _gist_user_task(prompt, MAX_TASK_CHARS),
            "attachments": state.get("attachments") or [],
            "prompt_observation": "observed",
        },
        "execution": {
            "iterations": {
                "count": loop_count + 1,
                "loop_count": loop_count,
                "observation": "observed_from_stop_hook",
            },
            "assistant_messages": int(state.get("assistant_messages") or 0),
            "thinking": state.get("thinking") or {},
            "tools": state.get("tools") or {},
            "subagents": state.get("subagents") or {},
            "errors": errors,
        },
        "outcome": {
            "status": status,
            "summary": state.get("assistant_summary") or "—",
            "assistant_response": state.get("assistant_response") or "",
            "response_observation": "observed",
        },
        "feedback": analyze_user_feedback(prompt),
        "capabilities": [],
        "artifacts": [],
        "tags": [_surface("tag")],
    }
    if operation["feedback"]["about_previous_agent_output"]:
        operation["feedback"]["target_operation_id"] = state.get("previous_operation_id")
        operation["feedback"]["attribution"] = (
            "previous_operation"
            if state.get("previous_operation_id")
            else "previous_output_unresolved"
        )
    append_operation(root, operation)
    state["journaled"] = True
    state["journaled_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    _write_state(state_path, state)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print("{}")
        return

    event = str(data.get("hook_event_name") or "")

    if event == "beforeSubmitPrompt":
        handle_before_submit(data)
        print(json.dumps({"continue": True}))
        return

    if event == "afterAgentResponse":
        handle_after_response(data)
        print("{}")
        return

    if event == "postToolUse":
        handle_tool_result(data, failed=False)
        print("{}")
        return

    if event == "postToolUseFailure":
        handle_tool_result(data, failed=True)
        print("{}")
        return

    if event == "subagentStop":
        handle_subagent_stop(data)
        print("{}")
        return

    if event == "afterAgentThought":
        handle_agent_thought(data)
        print("{}")
        return

    if event == "stop":
        handle_stop(data)
        print("{}")
        return

    print("{}")


if __name__ == "__main__":
    main()
