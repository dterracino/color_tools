"""Caller decisions applied to filament reconciliation plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class UseExisting:
    """Resolve a source filament to an existing Color Tools filament ID."""

    filament_id: str


@dataclass(frozen=True, slots=True)
class ImportNew:
    """Import a source filament using the plan's reserved generated ID."""


@dataclass(frozen=True, slots=True)
class Skip:
    """Exclude a source filament from catalog and ownership output."""


FilamentResolution: TypeAlias = UseExisting | ImportNew | Skip


__all__ = ["FilamentResolution", "ImportNew", "Skip", "UseExisting"]
