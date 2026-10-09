#!/usr/bin/env python3
"""Оновлює TELEGRAM_API_ID / TELEGRAM_API_HASH у tools/telegram-mcp/.env з workspace/keys/telegram."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # Personal (…/tools/telegram-mcp/scripts/this.py)
KEYS = ROOT / "workspace" / "keys" / "telegram"
ENV = Path(__file__).resolve().parents[1] / ".env"


def parse_keys_file(raw: str) -> tuple[str, str] | None:
    """Підтримує:
    - `api_id=123` / `api_hash=...` (регістр ключів неважливий), ігнорує інші поля (`app_title=...`);
    - два рядки: числовий id, потім hash (як раніше).
    """
    props: dict[str, str] = {}
    plain_lines: list[str] = []

    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "=" in s:
            key, _, val = s.partition("=")
            k = key.strip().lower()
            v = val.strip().strip('"').strip("'")
            if k in ("api_id", "telegram_api_id"):
                props["api_id"] = v
            elif k in ("api_hash", "telegram_api_hash"):
                props["api_hash"] = v
            continue
        plain_lines.append(s)

    if "api_id" in props and "api_hash" in props:
        return props["api_id"], props["api_hash"]

    if len(plain_lines) >= 2 and plain_lines[0].isdigit():
        return plain_lines[0], plain_lines[1]

    return None


def main() -> int:
    if not KEYS.is_file():
        print(f"Немає файлу {KEYS}", file=sys.stderr)
        print(
            "Створи його: див. workspace/keys/telegram.example (формат key=value або два рядки).",
            file=sys.stderr,
        )
        return 1
    raw = KEYS.read_text(encoding="utf-8")
    parsed = parse_keys_file(raw)
    if not parsed:
        print(
            f"Не вдалося прочитати api_id/api_hash з {KEYS}. "
            "Очікується `api_id=…` та `api_hash=…` або два рядки (id, hash).",
            file=sys.stderr,
        )
        return 1
    api_id, api_hash = parsed
    if not api_id.isdigit():
        print("api_id має бути числом.", file=sys.stderr)
        return 1
    if not api_hash:
        print("api_hash порожній.", file=sys.stderr)
        return 1
    if not ENV.is_file():
        print(f"Немає {ENV} — спочатку cp .env.example .env у tools/telegram-mcp", file=sys.stderr)
        return 1
    text = ENV.read_text(encoding="utf-8")

    new_text = text
    new_text = re.sub(r"^TELEGRAM_API_ID=.*$", f"TELEGRAM_API_ID={api_id}", new_text, flags=re.MULTILINE)
    new_text = re.sub(r"^TELEGRAM_API_HASH=.*$", f"TELEGRAM_API_HASH={api_hash}", new_text, flags=re.MULTILINE)
    ENV.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"Оновлено {ENV} з {KEYS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
