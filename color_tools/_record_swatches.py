"""Shared dependency-free rendering for record swatch conveniences."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from .png_writer import RGB, SimplePNGWriter

type _SwatchMode = Literal["solid", "blocks", "gradient"]


def _create_swatch_writer(
    resolved_rgb: RGB,
    components: Sequence[RGB],
    *,
    width: int,
    height: int,
    mode: _SwatchMode,
) -> SimplePNGWriter:
    """Create the writer for one validated record swatch request."""
    if mode == "solid":
        return SimplePNGWriter.from_solid(resolved_rgb, width, height)
    if mode == "blocks":
        return SimplePNGWriter.from_blocks(components, width, height)
    if mode == "gradient":
        return SimplePNGWriter.from_gradient(components, width, height)
    raise ValueError("mode must be 'solid', 'blocks', or 'gradient'")


def render_record_swatch(
    resolved_rgb: RGB,
    components: Sequence[RGB],
    *,
    width: int,
    height: int,
    mode: _SwatchMode,
) -> bytes:
    """Render a complete PNG for one record without optional dependencies."""
    return _create_swatch_writer(
        resolved_rgb,
        components,
        width=width,
        height=height,
        mode=mode,
    ).to_bytes()


def save_record_swatch(
    resolved_rgb: RGB,
    components: Sequence[RGB],
    path: str | Path,
    *,
    width: int,
    height: int,
    mode: _SwatchMode,
) -> Path:
    """Save one record swatch and return the destination Path."""
    destination = Path(path)
    _create_swatch_writer(
        resolved_rgb,
        components,
        width=width,
        height=height,
        mode=mode,
    ).save(destination)
    return destination
