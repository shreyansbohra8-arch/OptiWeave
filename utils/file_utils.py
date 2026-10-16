"""File helpers: atomic writes, safe reads, output-directory confinement."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from utils.exceptions import OptiWeaveError
from utils.validation import validate_source_text


def read_source(path: str | Path) -> str:
    """Read a UTF-8 source file and validate it."""
    with open(path, "r", encoding="utf-8") as fh:
        return validate_source_text(fh.read())


def atomic_write_text(path: str | Path, text: str) -> Path:
    """Write ``text`` to ``path`` atomically (temp file + replace)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp_", suffix=target.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, target)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return target


def write_inside(base: str | Path, name: str, text: str, overwrite: bool = True) -> Path:
    """Write ``text`` into ``base/name``; refuses paths that escape ``base``."""
    base_p = Path(base).resolve()
    target = (base_p / name).resolve()
    if base_p not in target.parents:
        raise OptiWeaveError(f"Refusing to write outside {base_p}: {name}")
    if target.exists() and not overwrite:
        raise OptiWeaveError(f"File already exists: {target}")
    return atomic_write_text(target, text)
