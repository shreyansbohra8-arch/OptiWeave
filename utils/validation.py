"""Input validation helpers."""
from __future__ import annotations

from pathlib import Path

from config import settings
from utils.exceptions import OptiWeaveError


def validate_source_text(source: str) -> str:
    """Validate raw source text; returns it unchanged or raises."""
    if not isinstance(source, str):
        raise OptiWeaveError("Source must be text.")
    if "\x00" in source:
        raise OptiWeaveError("Source contains NUL bytes.")
    if len(source.encode("utf-8")) > settings.MAX_SOURCE_BYTES:
        raise OptiWeaveError(f"Source exceeds {settings.MAX_SOURCE_BYTES} bytes.")
    return source


def validate_ow_path(path: str | Path) -> Path:
    """Validate that ``path`` is an existing ``.ow`` file."""
    p = Path(path)
    if p.suffix.lower() != ".ow":
        raise OptiWeaveError(f"Expected a .ow file, got: {p.name}")
    if not p.is_file():
        raise OptiWeaveError(f"File not found: {p}")
    return p


def safe_stem(name: str) -> str:
    """Reduce a user-supplied name to a safe file stem."""
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name)
    return cleaned.strip("_") or "program"
