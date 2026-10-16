"""Structured results from loading and merging maker synonyms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


_SynonymLoadAction = Literal["added", "unchanged", "replaced", "extended"]


@dataclass(frozen=True, slots=True)
class SynonymLoadEvent:
    """Describe how one user maker-synonym entry affected loaded data."""

    action: _SynonymLoadAction
    maker: str
    user_synonyms: tuple[str, ...]
    previous_synonyms: tuple[str, ...] = ()
    effective_synonyms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SynonymLoadReport:
    """Summarize a completed system and user maker-synonym load."""

    system_makers_loaded: int
    user_makers_loaded: int
    total_makers_available: int
    events: tuple[SynonymLoadEvent, ...] = ()

    def _count(self, action: _SynonymLoadAction) -> int:
        return sum(event.action == action for event in self.events)

    @property
    def makers_added(self) -> int:
        """Return the number of new maker entries added by the user file."""
        return self._count("added")

    @property
    def makers_unchanged(self) -> int:
        """Return the number of user entries equal to the system entry."""
        return self._count("unchanged")

    @property
    def makers_replaced(self) -> int:
        """Return the number of disjoint system synonym lists replaced."""
        return self._count("replaced")

    @property
    def makers_extended(self) -> int:
        """Return the number of overlapping system synonym lists extended."""
        return self._count("extended")
