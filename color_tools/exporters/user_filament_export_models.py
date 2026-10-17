"""Typed planning and result models for user-filament persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


UserFilamentConflictPolicy = Literal["error", "skip", "replace"]
UserFilamentExportAction = Literal[
    "added",
    "updated",
    "unchanged",
    "skipped",
    "conflict",
]


@dataclass(frozen=True, slots=True)
class UserFilamentExportChange:
    """One ID-based decision made while planning a filament update."""

    action: UserFilamentExportAction
    incoming: FilamentRecord
    existing: FilamentRecord | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class UserFilamentExportPlan:
    """Immutable dry-run plan for one ``user-filaments.json`` update."""

    destination: Path
    sidecar: Path
    conflict_policy: UserFilamentConflictPolicy
    input_count: int
    user_records: tuple[FilamentRecord, ...]
    changes: tuple[UserFilamentExportChange, ...]
    warnings: tuple[str, ...]
    expected_destination_hash: str | None
    destination_existed: bool

    @property
    def conflicts(self) -> tuple[UserFilamentExportChange, ...]:
        """Return unresolved same-ID conflicts that prevent application."""
        return tuple(change for change in self.changes if change.action == "conflict")

    @property
    def can_apply(self) -> bool:
        """Return whether this plan contains no unresolved conflicts."""
        return not self.conflicts

    @property
    def would_write(self) -> bool:
        """Return whether applying this plan would change or create the file."""
        return (not self.destination_existed and bool(self.user_records)) or any(
            change.action in {"added", "updated"} for change in self.changes
        )

    def count(self, action: UserFilamentExportAction) -> int:
        """Count planned decisions having the requested action."""
        return sum(change.action == action for change in self.changes)

    @property
    def accepted_count(self) -> int:
        """Return additions, updates, and exact unchanged matches."""
        return sum(
            self.count(action)
            for action in ("added", "updated", "unchanged")
        )

    @property
    def skipped_count(self) -> int:
        """Return same-ID conflicts retained under the skip policy."""
        return self.count("skipped")

    @property
    def rejected_count(self) -> int:
        """Return unresolved same-ID conflicts that prevent application."""
        return self.count("conflict")


@dataclass(frozen=True, slots=True)
class UserFilamentExportResult:
    """Outcome of explicitly applying a user-filament export plan."""

    plan: UserFilamentExportPlan
    applied: bool
    data_written: bool
    sidecar_written: bool


__all__ = [
    "UserFilamentConflictPolicy",
    "UserFilamentExportAction",
    "UserFilamentExportChange",
    "UserFilamentExportPlan",
    "UserFilamentExportResult",
]
