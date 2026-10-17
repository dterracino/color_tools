"""Planning and result models for additive owned-filament updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


OwnedFilamentExportAction = Literal["added", "already_owned", "unknown"]


@dataclass(frozen=True, slots=True)
class OwnedFilamentExportChange:
    """One ownership-selection decision for a final Color Tools ID."""

    action: OwnedFilamentExportAction
    filament_id: str
    record: FilamentRecord | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class OwnedFilamentExportPlan:
    """Read-only additive plan for one ``owned-filaments.json`` update."""

    destination: Path
    input_count: int
    owned_filament_ids: tuple[str, ...]
    changes: tuple[OwnedFilamentExportChange, ...]
    expected_destination_hash: str | None
    destination_existed: bool

    @property
    def unmatched(self) -> tuple[OwnedFilamentExportChange, ...]:
        """Return unknown IDs that prevent application."""
        return tuple(change for change in self.changes if change.action == "unknown")

    @property
    def can_apply(self) -> bool:
        """Return whether every selected ID exists in the effective catalog."""
        return not self.unmatched

    @property
    def would_write(self) -> bool:
        """Return whether applying would add at least one ownership ID."""
        return any(change.action == "added" for change in self.changes)

    def count(self, action: OwnedFilamentExportAction) -> int:
        """Count planned decisions having the requested action."""
        return sum(change.action == action for change in self.changes)

    @property
    def accepted_count(self) -> int:
        """Return selected IDs that are new or already owned."""
        return self.count("added") + self.count("already_owned")

    @property
    def rejected_count(self) -> int:
        """Return selected IDs absent from the effective catalog."""
        return self.count("unknown")


@dataclass(frozen=True, slots=True)
class OwnedFilamentExportResult:
    """Outcome of explicitly applying an owned-filament export plan."""

    plan: OwnedFilamentExportPlan
    applied: bool
    data_written: bool


__all__ = [
    "OwnedFilamentExportAction",
    "OwnedFilamentExportChange",
    "OwnedFilamentExportPlan",
    "OwnedFilamentExportResult",
]
