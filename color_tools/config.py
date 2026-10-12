"""Immutable execution-context configuration for color processing."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
import math
from typing import Literal

MultiColorMode = Literal["first", "last", "srgb_mean"]


@dataclass(frozen=True, slots=True)
class ColorConfig:
    """Validated settings captured by operations and filament construction.

    ``first`` selects the first component, ``last`` the final component, and
    ``srgb_mean`` averages encoded sRGB channels with equal weights.
    Future modes (not accepted yet): representative, lightest, darkest,
    most_chromatic, least_chromatic, linear_rgb_mean, and lab_mean.

    Tolerance is measured in 0-255 RGB channel units. Iterations limit the
    gamut search; numerical convergence may stop it earlier.
    """

    multi_color_mode: MultiColorMode = "first"
    gamut_tolerance: float = 0.01
    gamut_max_iterations: int = 20

    def __post_init__(self) -> None:
        _validate_settings(
            self.multi_color_mode, self.gamut_tolerance, self.gamut_max_iterations
        )


def _validate_settings(mode: object, tolerance: object, iterations: object) -> None:
    """Validate runtime inputs, including callers that do not use type checking."""
    if not isinstance(mode, str):
        raise TypeError("multi_color_mode must be a string")
    if mode not in ("first", "last", "srgb_mean"):
        raise ValueError("multi_color_mode must be 'first', 'last', or 'srgb_mean'")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise TypeError("gamut_tolerance must be a number, not a boolean")
    if tolerance < 0 or (isinstance(tolerance, float) and not math.isfinite(tolerance)):
        raise ValueError("gamut_tolerance must be finite and >= 0")
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise TypeError("gamut_max_iterations must be an integer, not a boolean")
    if iterations < 1:
        raise ValueError("gamut_max_iterations must be >= 1")


_DEFAULT_CONFIG = ColorConfig()
_config: ContextVar[ColorConfig] = ContextVar("color_tools_config", default=_DEFAULT_CONFIG)


def get_config() -> ColorConfig:
    """Return the current frozen settings instance, without copying it."""
    return _config.get()


def set_config(
    *,
    multi_color_mode: MultiColorMode | None = None,
    gamut_tolerance: float | None = None,
    gamut_max_iterations: int | None = None,
) -> None:
    """Update current-context settings atomically; None leaves a value unchanged.

    New async tasks inherit their creation context. Independent threads do not
    automatically inherit these overrides; callers can explicitly propagate
    context with ``contextvars.copy_context``. Existing records are unchanged.
    Invalid types raise TypeError; invalid values raise ValueError.
    """
    current = get_config()
    updated = replace(
        current,
        multi_color_mode=(
            current.multi_color_mode if multi_color_mode is None else multi_color_mode
        ),
        gamut_tolerance=(
            current.gamut_tolerance if gamut_tolerance is None else gamut_tolerance
        ),
        gamut_max_iterations=(
            current.gamut_max_iterations
            if gamut_max_iterations is None else gamut_max_iterations
        ),
    )
    _config.set(updated)


def reset_config() -> None:
    """Restore built-in defaults in the current execution context only."""
    _config.set(_DEFAULT_CONFIG)


@contextmanager
def config_context(
    *,
    multi_color_mode: MultiColorMode | None = None,
    gamut_tolerance: float | None = None,
    gamut_max_iterations: int | None = None,
) -> Generator[None, None, None]:
    """Temporarily override settings, restoring the exact instance on exit.

    Nested overrides, set_config, and reset_config inside the block are all
    undone on exit, including when an exception is raised.
    """
    token = _config.set(get_config())
    try:
        set_config(
            multi_color_mode=multi_color_mode,
            gamut_tolerance=gamut_tolerance,
            gamut_max_iterations=gamut_max_iterations,
        )
        yield
    finally:
        _config.reset(token)
