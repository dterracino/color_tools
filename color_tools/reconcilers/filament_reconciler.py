"""Base contract for reusable external-filament reconciliation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Literal

from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.filament_id import generate_filament_id, next_available_filament_id
from color_tools.filament_palette import FilamentRecord
from color_tools.reconcilers.filament_reconciliation_models import (
    FilamentMatchCandidate,
    FilamentReconciliationEntry,
    FilamentReconciliationPlan,
    FilamentReconciliationPolicy,
    FilamentReconciliationResult,
    FilamentReconciliationStatus,
    FilamentResolutionMapping,
)
from color_tools.reconcilers.resolutions import (
    FilamentResolution,
    ImportNew,
    Skip,
    UseExisting,
)


class FilamentReconciler(ABC):
    """Plan and resolve imported filaments against an existing catalog.

    Subclasses rank format-specific candidates. This base class owns source
    ordering, deterministic ID reservation, ambiguity enforcement, resolution
    validation, and remapping of imported ownership to final catalog IDs.
    """

    def __init__(
        self,
        catalog: Sequence[FilamentRecord],
        *,
        policy: FilamentReconciliationPolicy | None = None,
    ) -> None:
        self._catalog = tuple(catalog)
        self._catalog_by_id = {record.id: record for record in self._catalog}
        if len(self._catalog_by_id) != len(self._catalog):
            raise ValueError("catalog contains duplicate filament IDs")
        self._policy = policy or FilamentReconciliationPolicy()

    @property
    def fuzzy_matching_available(self) -> bool:
        """Return whether the reconciler is using its optional fuzzy engine."""
        return False

    def plan(self, source: FilamentExportData) -> FilamentReconciliationPlan:
        """Create an immutable reconciliation plan without modifying files."""
        reserved_ids = set(self._catalog_by_id)
        owned_ids = set(source.metadata.owned_filament_ids)
        entries: list[FilamentReconciliationEntry] = []
        for source_index, record in enumerate(source.filaments):
            proposed_base = generate_filament_id(
                record.maker,
                record.type,
                record.finish,
                record.color,
            )
            proposed_id = next_available_filament_id(proposed_base, reserved_ids)
            reserved_ids.add(proposed_id)
            candidates = tuple(
                candidate
                for candidate in self._rank_candidates(record)
                if candidate.score >= self._policy.candidate_score
            )
            candidates = tuple(
                sorted(candidates, key=lambda item: (-item.score, item.filament_id))
            )
            status, automatic_id = self._classify(candidates)
            entries.append(
                FilamentReconciliationEntry(
                    source_index=source_index,
                    provisional_record=record,
                    owned=record.id in owned_ids,
                    status=status,
                    candidates=candidates,
                    automatic_filament_id=automatic_id,
                    proposed_filament_id=proposed_id,
                )
            )
        return FilamentReconciliationPlan(
            source=source,
            catalog=self._catalog,
            entries=tuple(entries),
            fuzzy_matching_available=self.fuzzy_matching_available,
        )

    def resolve(
        self,
        plan: FilamentReconciliationPlan,
        resolutions: Mapping[int, FilamentResolution] | None = None,
    ) -> FilamentReconciliationResult:
        """Apply caller choices and return only records that must be imported.

        Ambiguous entries require an explicit choice. Matched entries default
        to :class:`UseExisting`, new entries default to :class:`ImportNew`, and
        skipped entries default to :class:`Skip`.
        """
        if plan.catalog != self._catalog:
            raise ValueError("plan was created for a different catalog")
        choices = dict(resolutions or {})
        valid_indices = {entry.source_index for entry in plan.entries}
        unknown_indices = choices.keys() - valid_indices
        if unknown_indices:
            raise ValueError(
                "resolution supplied for unknown source index(es): "
                + ", ".join(str(index) for index in sorted(unknown_indices))
            )

        imported: list[FilamentRecord] = []
        final_owned_ids: list[str] = []
        mappings: list[FilamentResolutionMapping] = []
        for entry in plan.entries:
            resolution = choices.get(entry.source_index) or self._default_resolution(entry)
            final_id, action = self._apply_resolution(entry, resolution, imported)
            mappings.append(
                FilamentResolutionMapping(
                    source_index=entry.source_index,
                    source_filament_id=entry.provisional_record.id,
                    final_filament_id=final_id,
                    action=action,
                )
            )
            if entry.owned and final_id is not None and final_id not in final_owned_ids:
                final_owned_ids.append(final_id)

        metadata = plan.source.metadata
        return FilamentReconciliationResult(
            data=FilamentExportData(
                filaments=imported,
                metadata=FilamentMetadata(
                    name=metadata.name,
                    author=metadata.author,
                    description=metadata.description,
                    tags=metadata.tags,
                    owned_filament_ids=tuple(final_owned_ids),
                    properties=dict(metadata.properties),
                ),
            ),
            mappings=tuple(mappings),
        )

    def _classify(
        self,
        candidates: tuple[FilamentMatchCandidate, ...],
    ) -> tuple[FilamentReconciliationStatus, str | None]:
        """Classify ranked candidates using the configured thresholds."""
        if not candidates:
            return "new", None
        top = candidates[0]
        runner_up_score = candidates[1].score if len(candidates) > 1 else 0.0
        margin = top.score - runner_up_score
        exact_enough = top.kind in {"exact", "normalized", "synonym"}
        automatic = (
            (exact_enough and margin > 0.0)
            or (
                top.score >= self._policy.automatic_score
                and margin >= self._policy.automatic_margin
            )
        )
        if automatic:
            return "matched", top.filament_id
        return "ambiguous", None

    def _default_resolution(
        self,
        entry: FilamentReconciliationEntry,
    ) -> FilamentResolution:
        """Return the default choice for a non-ambiguous planned entry."""
        if entry.status == "matched" and entry.automatic_filament_id is not None:
            return UseExisting(entry.automatic_filament_id)
        if entry.status == "new":
            return ImportNew()
        if entry.status == "skipped":
            return Skip()
        raise ValueError(
            f"source index {entry.source_index} is ambiguous and requires a resolution"
        )

    def _apply_resolution(
        self,
        entry: FilamentReconciliationEntry,
        resolution: FilamentResolution,
        imported: list[FilamentRecord],
    ) -> tuple[
        str | None,
        Literal["use_existing", "import_new", "skip"],
    ]:
        """Validate and apply one resolution to result state."""
        if isinstance(resolution, UseExisting):
            if resolution.filament_id not in self._catalog_by_id:
                raise ValueError(
                    f"unknown existing filament ID {resolution.filament_id!r} "
                    f"for source index {entry.source_index}"
                )
            return resolution.filament_id, "use_existing"
        if isinstance(resolution, ImportNew):
            source = entry.provisional_record
            imported.append(
                FilamentRecord(
                    id=entry.proposed_filament_id,
                    maker=source.maker,
                    type=source.type,
                    finish=source.finish,
                    color=source.color,
                    hex=source.hex,
                    td_value=source.td_value,
                    other_names=(
                        list(source.other_names) if source.other_names is not None else None
                    ),
                    source=source.source,
                )
            )
            return entry.proposed_filament_id, "import_new"
        return None, "skip"

    @abstractmethod
    def _rank_candidates(
        self,
        record: FilamentRecord,
    ) -> Sequence[FilamentMatchCandidate]:
        """Return format-specific candidate matches for one imported record."""
        raise NotImplementedError


__all__ = ["FilamentReconciler"]
