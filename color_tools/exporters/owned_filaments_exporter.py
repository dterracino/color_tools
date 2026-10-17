"""State-aware exporter for additive ``owned-filaments.json`` updates."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from color_tools.constants import ColorConstants
from color_tools.exporters._stateful_user_data import (
    atomic_write_text,
    normalized_file_hash,
)
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.owned_filament_export_models import (
    OwnedFilamentExportChange,
    OwnedFilamentExportPlan,
    OwnedFilamentExportResult,
)
from color_tools.filament_id import validate_filament_id
from color_tools.filament_palette import load_filaments, load_owned_filaments


class OwnedFilamentsExporter:
    """Plan and apply additive ownership changes against the merged catalog.

    This state-aware exporter writes only ``owned-filaments.json``. It never
    creates or changes filament records, never removes existing ownership, and
    never writes a sidecar. :meth:`plan` is read-only; :meth:`apply` must be
    called explicitly after every selected ID resolves in the effective
    system-plus-user catalog.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).parent.parent / "data"
        )

    @property
    def destination(self) -> Path:
        """Return the managed ``owned-filaments.json`` path."""
        return self._data_dir / ColorConstants.OWNED_FILAMENTS_JSON_FILENAME

    def plan(
        self,
        data: FilamentExportData | Iterable[object],
    ) -> OwnedFilamentExportPlan:
        """Build a read-only additive ownership plan.

        ``FilamentExportData`` uses its metadata's final
        ``owned_filament_ids``. A direct iterable supports callers that already
        have Color Tools IDs. External identifiers must be reconciled before
        reaching this operation.
        """
        incoming = self._incoming_ids(data)
        records = load_filaments(self._data_dir)
        catalog_by_id = {record.id: record for record in records}
        destination = self.destination
        existing = load_owned_filaments(destination)
        unknown_existing = sorted(existing - catalog_by_id.keys())
        if unknown_existing:
            preview = ", ".join(unknown_existing[:3])
            if len(unknown_existing) > 3:
                preview += ", ..."
            raise ValueError(
                "owned-filaments.json contains ID(s) absent from the effective "
                f"catalog: {preview}"
            )

        changes: list[OwnedFilamentExportChange] = []
        prospective = set(existing)
        for filament_id in incoming:
            record = catalog_by_id.get(filament_id)
            if record is None:
                changes.append(
                    OwnedFilamentExportChange(
                        "unknown",
                        filament_id,
                        message="Filament ID is absent from the effective catalog",
                    )
                )
            elif filament_id in prospective:
                changes.append(
                    OwnedFilamentExportChange(
                        "already_owned",
                        filament_id,
                        record,
                    )
                )
            else:
                prospective.add(filament_id)
                changes.append(
                    OwnedFilamentExportChange("added", filament_id, record)
                )

        return OwnedFilamentExportPlan(
            destination=destination,
            input_count=len(incoming),
            owned_filament_ids=tuple(sorted(prospective)),
            changes=tuple(changes),
            expected_destination_hash=normalized_file_hash(destination),
            destination_existed=destination.exists(),
        )

    def apply(self, plan: OwnedFilamentExportPlan) -> OwnedFilamentExportResult:
        """Apply a reviewed plan after stale-state and catalog validation."""
        if plan.destination != self.destination:
            raise ValueError("Plan destination does not belong to this exporter")
        if not plan.can_apply:
            raise ValueError(
                "Cannot apply an owned-filament plan with unmatched IDs"
            )
        if normalized_file_hash(plan.destination) != plan.expected_destination_hash:
            raise RuntimeError(
                "owned-filaments.json changed after planning; create a new plan "
                "before applying"
            )

        catalog_ids = {record.id for record in load_filaments(self._data_dir)}
        missing = sorted(set(plan.owned_filament_ids) - catalog_ids)
        if missing:
            raise RuntimeError(
                "effective filament catalog changed after planning; create a new "
                "plan before applying"
            )
        if not plan.would_write:
            return OwnedFilamentExportResult(plan, True, False)

        document = {"owned_filaments": list(plan.owned_filament_ids)}
        payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        atomic_write_text(plan.destination, payload)
        return OwnedFilamentExportResult(plan, True, True)

    @staticmethod
    def _incoming_ids(
        data: FilamentExportData | Iterable[object],
    ) -> tuple[str, ...]:
        """Validate, preserve, and deduplicate the selected final IDs."""
        if isinstance(data, FilamentExportData):
            values: Iterable[object] = data.metadata.owned_filament_ids
        else:
            if isinstance(data, str):
                raise TypeError("owned filament IDs must be an iterable of strings")
            values = data

        result: list[str] = []
        seen: set[str] = set()
        for index, value in enumerate(values):
            if not isinstance(value, str):
                raise TypeError(
                    f"owned filament ID at index {index} must be a string"
                )
            try:
                filament_id = validate_filament_id(value)
            except ValueError as error:
                raise ValueError(
                    f"invalid owned filament ID at index {index}: {error}"
                ) from error
            if filament_id in seen:
                raise ValueError(
                    f"duplicate owned filament ID {filament_id!r} in input"
                )
            seen.add(filament_id)
            result.append(filament_id)
        return tuple(result)


__all__ = ["OwnedFilamentsExporter"]
