"""State-aware exporter for Color Tools ``user-filaments.json`` data."""

from __future__ import annotations

from pathlib import Path

from color_tools._filament_data import (
    load_filament_records_file,
    merge_user_filaments,
    parse_filament_records,
    serialize_filament_record,
    serialize_filament_records,
)
from color_tools.constants import ColorConstants
from color_tools.exporters._stateful_user_data import (
    normalized_file_hash,
    write_json_with_sidecar,
)
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.user_filament_export_models import (
    UserFilamentConflictPolicy,
    UserFilamentExportChange,
    UserFilamentExportPlan,
    UserFilamentExportResult,
)
from color_tools.filament_palette import FilamentRecord


class UserFilamentsExporter:
    """Plan and explicitly apply ID-based ``user-filaments.json`` updates.

    Stable filament IDs are the sole replacement key. Equal descriptive fields
    or RGB values under different IDs remain distinct filament products.
    :meth:`plan` never writes; :meth:`apply` validates the prospective catalog,
    rejects stale plans, atomically replaces the user file, and refreshes its
    SHA-256 sidecar.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).parent.parent / "data"
        )

    @property
    def destination(self) -> Path:
        """Return the managed ``user-filaments.json`` path."""
        return self._data_dir / ColorConstants.USER_FILAMENTS_JSON_FILENAME

    def plan(
        self,
        data: FilamentExportData | list[FilamentRecord],
        *,
        conflict_policy: UserFilamentConflictPolicy = "error",
    ) -> UserFilamentExportPlan:
        """Build a read-only, ID-based merge plan for filament records."""
        if conflict_policy not in {"error", "skip", "replace"}:
            raise ValueError("conflict_policy must be 'error', 'skip', or 'replace'")

        incoming = data.filaments if isinstance(data, FilamentExportData) else data
        destination = self.destination
        system_records = load_filament_records_file(
            self._data_dir / ColorConstants.FILAMENTS_JSON_FILENAME
        )
        existing_user = (
            load_filament_records_file(destination) if destination.exists() else []
        )
        effective, _ = merge_user_filaments(system_records, existing_user)
        prospective_user = list(existing_user)
        changes: list[UserFilamentExportChange] = []
        warnings: list[str] = []
        seen_ids: set[str] = set()

        for input_record in incoming:
            record = self._canonical_record(input_record, destination.name)
            if record.id in seen_ids:
                raise ValueError(
                    f"Duplicate input filament ID {record.id!r} in export data"
                )
            seen_ids.add(record.id)
            existing = next(
                (item for item in effective if item.id == record.id),
                None,
            )

            if existing is not None and self._records_equal(existing, record):
                changes.append(
                    UserFilamentExportChange("unchanged", record, existing)
                )
                continue

            if existing is not None and conflict_policy != "replace":
                action = "skipped" if conflict_policy == "skip" else "conflict"
                changes.append(
                    UserFilamentExportChange(
                        action,
                        record,
                        existing,
                        "Filament ID already exists with different field values",
                    )
                )
                continue

            if existing is None:
                similar = next(
                    (
                        item
                        for item in effective
                        if self._descriptive_identity(item)
                        == self._descriptive_identity(record)
                    ),
                    None,
                )
                if similar is not None:
                    warnings.append(
                        f"Filament {record.id!r} has the same maker, type, finish, "
                        f"and color as existing ID {similar.id!r}; both IDs are kept"
                    )
                prospective_user.append(record)
                action = "added"
            else:
                user_index = next(
                    (
                        index
                        for index, item in enumerate(prospective_user)
                        if item.id == record.id
                    ),
                    None,
                )
                if user_index is None:
                    prospective_user.append(record)
                else:
                    prospective_user[user_index] = record
                action = "updated"

            effective, _ = merge_user_filaments(system_records, prospective_user)
            changes.append(UserFilamentExportChange(action, record, existing))

        merge_user_filaments(system_records, prospective_user)
        return UserFilamentExportPlan(
            destination=destination,
            sidecar=destination.with_suffix(destination.suffix + ".sha256"),
            conflict_policy=conflict_policy,
            input_count=len(incoming),
            user_records=tuple(prospective_user),
            changes=tuple(changes),
            warnings=tuple(warnings),
            expected_destination_hash=normalized_file_hash(destination),
            destination_existed=destination.exists(),
        )

    def apply(self, plan: UserFilamentExportPlan) -> UserFilamentExportResult:
        """Apply a reviewed plan after stale-state and catalog validation."""
        if plan.destination != self.destination:
            raise ValueError("Plan destination does not belong to this exporter")
        if not plan.can_apply:
            raise ValueError(
                "Cannot apply a user-filament plan with unresolved conflicts"
            )
        if normalized_file_hash(plan.destination) != plan.expected_destination_hash:
            raise RuntimeError(
                "user-filaments.json changed after planning; create a new plan "
                "before applying"
            )
        if not plan.would_write:
            return UserFilamentExportResult(plan, True, False, False)

        document = serialize_filament_records(plan.user_records)
        prospective = parse_filament_records(document, plan.destination)
        system_records = load_filament_records_file(
            self._data_dir / ColorConstants.FILAMENTS_JSON_FILENAME
        )
        merge_user_filaments(system_records, prospective)
        write_json_with_sidecar(plan.destination, document)
        return UserFilamentExportResult(plan, True, True, True)

    @staticmethod
    def _canonical_record(record: FilamentRecord, source: str) -> FilamentRecord:
        """Rebuild and validate a record from authoritative source fields."""
        document = [serialize_filament_record(record)]
        return parse_filament_records(document, source)[0]

    @staticmethod
    def _records_equal(left: FilamentRecord, right: FilamentRecord) -> bool:
        """Compare the authoritative serialized fields of two records."""
        return serialize_filament_record(left) == serialize_filament_record(right)

    @staticmethod
    def _descriptive_identity(
        record: FilamentRecord,
    ) -> tuple[str, str, str | None, str]:
        """Return a case-insensitive product description used for warnings."""
        return (
            record.maker.casefold(),
            record.type.casefold(),
            record.finish.casefold() if record.finish is not None else None,
            record.color.casefold(),
        )


__all__ = ["UserFilamentsExporter"]
