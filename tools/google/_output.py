"""Збереження JSON у каталозі output поруч із скриптами."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_DIR = Path(__file__).resolve().parent / "output"


def resolve_output_dir(explicit: Path | None) -> Path:
    return explicit.expanduser().resolve() if explicit else _DEFAULT_DIR


def write_json_output(
    data: Any,
    stem: str,
    *,
    output_dir: Path | None = None,
) -> Path:
    out_dir = resolve_output_dir(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{stem}_{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
