"""Typed planning and result models for user-color persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


UserColorConflictPolicy = Literal["error", "skip", "replace"]
UserColorExportAction = Literal[
    "added",
    "updated",
    "unchanged",
    "skipped",
    "conflict",
]


@dataclass(frozen=True, slots=True)
class UserColorExportChange:
    """One decision made while planning a user-color update."""

    action: UserColorExportAction
    incoming: ColorRecord
    existing: ColorRecord | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class UserColorExportPlan:
    """Immutable dry-run plan for one ``user-colors.json`` update."""

    destination: Path
    sidecar: Path
    conflict_policy: UserColorConflictPolicy
    input_count: int
    user_records: tuple[ColorRecord, ...]
    changes: tuple[UserColorExportChange, ...]
    expected_destination_hash: str | None
    destination_existed: bool

    @property
    def conflicts(self) -> tuple[UserColorExportChange, ...]:
        """Return unresolved conflicts that prevent applying this plan."""
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

    def count(self, action: UserColorExportAction) -> int:
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
        """Return conflicts intentionally retained under the skip policy."""
        return self.count("skipped")

    @property
    def rejected_count(self) -> int:
        """Return unresolved conflicts that prevent application."""
        return self.count("conflict")


@dataclass(frozen=True, slots=True)
class UserColorExportResult:
    """Outcome of explicitly applying a user-color export plan."""

    plan: UserColorExportPlan
    applied: bool
    data_written: bool
    sidecar_written: bool


__all__ = [
    "UserColorConflictPolicy",
    "UserColorExportAction",
    "UserColorExportChange",
    "UserColorExportPlan",
    "UserColorExportResult",
]
