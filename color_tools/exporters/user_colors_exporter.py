"""State-aware exporter for Color Tools ``user-colors.json`` data."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import cast

from color_tools._palette_utils import normalize_color_name
from color_tools.constants import ColorConstants
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.user_color_export_models import (
    UserColorConflictPolicy,
    UserColorExportChange,
    UserColorExportPlan,
    UserColorExportResult,
)
from color_tools.palette import ColorRecord, load_system_colors
from color_tools.user_color_data import (
    merge_user_color_records,
    parse_user_color_records,
    serialize_user_color_records,
)


class UserColorsExporter:
    """Plan and explicitly apply safe updates to ``user-colors.json``.

    :meth:`plan` is read-only and is therefore the default operation.
    :meth:`apply` validates that the destination has not changed since planning,
    validates the complete prospective document, atomically replaces the data
    file, and refreshes its SHA-256 sidecar.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).parent.parent / "data"
        )

    @property
    def destination(self) -> Path:
        """Return the managed ``user-colors.json`` path."""
        return self._data_dir / ColorConstants.USER_COLORS_JSON_FILENAME

    def plan(
        self,
        data: PaletteExportData | list[ColorRecord],
        *,
        conflict_policy: UserColorConflictPolicy = "error",
    ) -> UserColorExportPlan:
        """Build a read-only merge plan for imported or selected colors."""
        if conflict_policy not in {"error", "skip", "replace"}:
            raise ValueError("conflict_policy must be 'error', 'skip', or 'replace'")

        incoming = data.colors if isinstance(data, PaletteExportData) else data
        destination = self.destination
        system_records = load_system_colors(
            self._data_dir / ColorConstants.COLORS_JSON_FILENAME
        )
        existing_user = self._read_existing_user_records(destination)
        effective, _ = merge_user_color_records(system_records, existing_user)
        prospective_user = list(existing_user)
        changes: list[UserColorExportChange] = []
        seen_names: set[str] = set()

        for input_record in incoming:
            record = self._canonical_record(input_record, destination.name)
            name_key = normalize_color_name(record.name)
            if name_key in seen_names:
                raise ValueError(
                    f"Duplicate input color name '{record.name}' in export data"
                )
            seen_names.add(name_key)

            existing = next(
                (
                    item
                    for item in effective
                    if normalize_color_name(item.name) == name_key
                ),
                None,
            )
            rgb_conflict = next(
                (
                    item
                    for item in effective
                    if item.rgb == record.rgb
                    and normalize_color_name(item.name) != name_key
                ),
                None,
            )

            if rgb_conflict is not None:
                action = "skipped" if conflict_policy == "skip" else "conflict"
                changes.append(
                    UserColorExportChange(
                        action,
                        record,
                        rgb_conflict,
                        "RGB value already belongs to a different color name",
                    )
                )
                continue

            if existing is not None and existing.rgb == record.rgb:
                changes.append(UserColorExportChange("unchanged", record, existing))
                continue

            if existing is not None and conflict_policy != "replace":
                action = "skipped" if conflict_policy == "skip" else "conflict"
                changes.append(
                    UserColorExportChange(
                        action,
                        record,
                        existing,
                        "Normalized color name already exists with another value",
                    )
                )
                continue

            if existing is None:
                prospective_user.append(record)
                action = "added"
            else:
                user_index = next(
                    (
                        index
                        for index, item in enumerate(prospective_user)
                        if normalize_color_name(item.name) == name_key
                    ),
                    None,
                )
                if user_index is None:
                    prospective_user.append(record)
                else:
                    prospective_user[user_index] = record
                action = "updated"

            effective, _ = merge_user_color_records(system_records, prospective_user)
            changes.append(UserColorExportChange(action, record, existing))

        merge_user_color_records(system_records, prospective_user)
        return UserColorExportPlan(
            destination=destination,
            sidecar=destination.with_suffix(destination.suffix + ".sha256"),
            conflict_policy=conflict_policy,
            input_count=len(incoming),
            user_records=tuple(prospective_user),
            changes=tuple(changes),
            expected_destination_hash=self._file_hash(destination),
            destination_existed=destination.exists(),
        )

    def apply(self, plan: UserColorExportPlan) -> UserColorExportResult:
        """Apply a previously reviewed plan and return its structured result."""
        if plan.destination != self.destination:
            raise ValueError("Plan destination does not belong to this exporter")
        if not plan.can_apply:
            raise ValueError("Cannot apply a user-color plan with unresolved conflicts")
        if self._file_hash(plan.destination) != plan.expected_destination_hash:
            raise RuntimeError(
                "user-colors.json changed after planning; create a new plan before applying"
            )
        if not plan.would_write:
            return UserColorExportResult(plan, True, False, False)

        document = serialize_user_color_records(plan.user_records)
        prospective = parse_user_color_records(document, plan.destination)
        system_records = load_system_colors(
            self._data_dir / ColorConstants.COLORS_JSON_FILENAME
        )
        merge_user_color_records(system_records, prospective)

        payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        self._atomic_write_text(plan.destination, payload)
        digest = ColorConstants.generate_user_data_hash(plan.destination)
        self._atomic_write_text(
            plan.sidecar,
            f"{digest}  {plan.destination.name}\n",
        )
        return UserColorExportResult(plan, True, True, True)

    @staticmethod
    def _canonical_record(record: ColorRecord, source: str) -> ColorRecord:
        """Rebuild a record from authoritative name and RGB values."""
        name = record.name.strip()
        if not name:
            raise ValueError("User color names must not be empty")
        return ColorRecord.from_rgb(record.rgb, name=name, source=source)

    @staticmethod
    def _read_existing_user_records(path: Path) -> list[ColorRecord]:
        """Read the existing destination or return an empty user collection."""
        if not path.exists():
            return []
        try:
            data: object = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON in user color file {path}: {error}") from error
        if not isinstance(data, list):
            raise ValueError(f"Expected array of colors at root level in {path}")
        return parse_user_color_records(cast(list[object], data), path)

    @staticmethod
    def _file_hash(path: Path) -> str | None:
        """Return a normalized content hash, or None when the file is absent."""
        if not path.exists():
            return None
        content = path.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        """Atomically replace a UTF-8 text file from its destination directory."""
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


__all__ = ["UserColorsExporter"]
