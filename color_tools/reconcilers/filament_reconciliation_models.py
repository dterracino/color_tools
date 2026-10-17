"""Format-neutral models for filament catalog reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.filament_palette import FilamentRecord


FilamentMatchKind: TypeAlias = Literal["exact", "normalized", "synonym", "fuzzy"]
FilamentReconciliationStatus: TypeAlias = Literal[
    "matched", "ambiguous", "new", "skipped"
]


@dataclass(frozen=True, slots=True)
class FilamentReconciliationPolicy:
    """Thresholds controlling automatic and candidate fuzzy matches."""

    candidate_score: float = 75.0
    automatic_score: float = 85.0
    automatic_margin: float = 4.0
    candidate_limit: int = 5
    candidate_score_window: float = 10.0

    def __post_init__(self) -> None:
        """Validate score ranges and ordering."""
        if not 0.0 <= self.candidate_score <= 100.0:
            raise ValueError("candidate_score must be between 0 and 100")
        if not 0.0 <= self.automatic_score <= 100.0:
            raise ValueError("automatic_score must be between 0 and 100")
        if self.automatic_score < self.candidate_score:
            raise ValueError("automatic_score must not be below candidate_score")
        if self.automatic_margin < 0.0:
            raise ValueError("automatic_margin must be non-negative")
        if self.candidate_limit <= 0:
            raise ValueError("candidate_limit must be positive")
        if self.candidate_score_window < 0.0:
            raise ValueError("candidate_score_window must be non-negative")


@dataclass(frozen=True, slots=True)
class FilamentMatchCandidate:
    """One ranked existing-catalog candidate for an imported filament."""

    filament_id: str
    score: float
    kind: FilamentMatchKind
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the bounded similarity score."""
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("candidate score must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class FilamentReconciliationEntry:
    """Planned treatment of one source filament in source order."""

    source_index: int
    provisional_record: FilamentRecord
    owned: bool
    status: FilamentReconciliationStatus
    candidates: tuple[FilamentMatchCandidate, ...]
    automatic_filament_id: str | None
    proposed_filament_id: str


@dataclass(frozen=True, slots=True)
class FilamentReconciliationPlan:
    """Immutable review plan produced before caller decisions are applied."""

    source: FilamentExportData
    catalog: tuple[FilamentRecord, ...]
    entries: tuple[FilamentReconciliationEntry, ...]
    fuzzy_matching_available: bool

    @property
    def unresolved_count(self) -> int:
        """Return the number of entries requiring an explicit resolution."""
        return sum(entry.status == "ambiguous" for entry in self.entries)

    def count(self, status: FilamentReconciliationStatus) -> int:
        """Return the number of entries with one planned status."""
        return sum(entry.status == status for entry in self.entries)


@dataclass(frozen=True, slots=True)
class FilamentResolutionMapping:
    """Map one source entry to its final Color Tools filament ID, if any."""

    source_index: int
    source_filament_id: str
    final_filament_id: str | None
    action: Literal["use_existing", "import_new", "skip"]


@dataclass(frozen=True, slots=True)
class FilamentReconciliationResult:
    """Resolved new-filament data plus source-to-final ID mappings."""

    data: FilamentExportData
    mappings: tuple[FilamentResolutionMapping, ...]

    def count(self, action: Literal["use_existing", "import_new", "skip"]) -> int:
        """Return the number of mappings using one final action."""
        return sum(mapping.action == action for mapping in self.mappings)


__all__ = [
    "FilamentMatchCandidate",
    "FilamentMatchKind",
    "FilamentReconciliationEntry",
    "FilamentReconciliationPlan",
    "FilamentReconciliationPolicy",
    "FilamentReconciliationResult",
    "FilamentReconciliationStatus",
    "FilamentResolutionMapping",
]
