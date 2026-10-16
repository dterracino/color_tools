"""Structured results from loading and merging color data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


_ColorLoadAction = Literal["added", "overridden"]


@dataclass(frozen=True, slots=True)
class ColorLoadEvent:
    """Describe one user-color addition or name-based replacement."""

    action: _ColorLoadAction
    record: ColorRecord
    replaced_record: ColorRecord | None = None


@dataclass(frozen=True, slots=True)
class ColorLoadReport:
    """Summarize a completed core and user color load."""

    system_colors_loaded: int
    user_colors_loaded: int
    total_colors_available: int
    events: tuple[ColorLoadEvent, ...] = ()

    @property
    def colors_overridden_by_name(self) -> int:
        """Return the number of user colors that replaced colors by name."""
        return sum(event.action == "overridden" for event in self.events)

    @property
    def unique_user_colors_loaded(self) -> int:
        """Return the number of user colors appended as new names."""
        return sum(event.action == "added" for event in self.events)
