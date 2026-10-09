"""Токен Folio API: env FOLIO_TOKEN або workspace/keys/folio."""

from __future__ import annotations

import os
from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def folio_base_url() -> str:
    return os.environ.get("FOLIO_BASE_URL", "https://folio.example.com").rstrip("/")


def token_path() -> Path:
    return workspace_root() / "workspace" / "keys" / "folio"


def read_token(explicit: str | None = None) -> str:
    if explicit:
        token = explicit.strip()
        if token:
            return token
        raise ValueError("Порожній --token")

    env = os.environ.get("FOLIO_TOKEN", "").strip()
    if env:
        return env

    path = token_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Немає токена: {path} (або FOLIO_TOKEN). "
            "Збережіть API token Folio у workspace/keys/folio."
        )
    token = path.read_text(encoding="utf-8").strip()
    for line in token.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    raise ValueError(f"Порожній файл токена: {path}")
