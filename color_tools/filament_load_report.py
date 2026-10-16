"""Structured results from loading and merging filament data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


_FilamentLoadAction = Literal["added", "overridden"]


@dataclass(frozen=True, slots=True)
class FilamentLoadEvent:
    """Describe one user-filament addition or ID-based replacement."""

    action: _FilamentLoadAction
    record: FilamentRecord
    replaced_record: FilamentRecord | None = None


@dataclass(frozen=True, slots=True)
class FilamentLoadReport:
    """Summarize a completed system and user filament load."""

    system_filaments_loaded: int
    user_filaments_loaded: int
    total_filaments_available: int
    events: tuple[FilamentLoadEvent, ...] = ()

    @property
    def filaments_overridden_by_id(self) -> int:
        """Return the number of user records that replaced a system record."""
        return sum(event.action == "overridden" for event in self.events)

    @property
    def unique_user_filaments_loaded(self) -> int:
        """Return the number of user records appended under new IDs."""
        return sum(event.action == "added" for event in self.events)
