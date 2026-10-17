"""Shared persistence primitives for stateful user-data exporters."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from color_tools.constants import ColorConstants


def normalized_file_hash(path: Path) -> str | None:
    """Return a normalized SHA-256 hash, or None when the file is absent."""
    if not path.exists():
        return None
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file from its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json_with_sidecar(path: Path, document: object) -> Path:
    """Atomically write formatted JSON and refresh its integrity sidecar."""
    payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    atomic_write_text(path, payload)
    digest = ColorConstants.generate_user_data_hash(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    atomic_write_text(sidecar, f"{digest}  {path.name}\n")
    return sidecar


__all__ = ["atomic_write_text", "normalized_file_hash", "write_json_with_sidecar"]
