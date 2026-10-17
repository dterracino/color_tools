"""Tests for independent additive owned-filament persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import cast

from color_tools._filament_data import serialize_filament_records
from color_tools.exporters import (
    FilamentExportData,
    FilamentMetadata,
    OwnedFilamentsExporter,
    UserFilamentsExporter,
)
from color_tools.filament_palette import FilamentRecord, load_owned_filaments


def _record(
    filament_id: str,
    *,
    maker: str = "Maker",
    color: str = "Red",
) -> FilamentRecord:
    """Build one valid catalog fixture record."""
    return FilamentRecord(
        id=filament_id,
        maker=maker,
        type="PLA",
        finish=None,
        color=color,
        hex="#FF0000",
        td_value=5.0,
        source="fixture.json",
    )


class TestOwnedFilamentsExporter(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name)
        self.user_dir = self.data_dir / "user"
        self.user_dir.mkdir()
        self.red = _record("maker-pla-red")
        self.blue = _record("maker-pla-blue", color="Blue")
        (self.data_dir / "filaments.json").write_text(
            json.dumps(serialize_filament_records([self.red, self.blue])),
            encoding="utf-8",
        )
        self.exporter = OwnedFilamentsExporter(self.data_dir)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_owned(self, filament_ids: list[str]) -> Path:
        path = self.user_dir / "owned-filaments.json"
        path.write_text(
            json.dumps({"owned_filaments": filament_ids}),
            encoding="utf-8",
        )
        return path

    def test_plan_is_read_only_and_uses_transfer_metadata(self) -> None:
        data = FilamentExportData(
            [],
            FilamentMetadata(owned_filament_ids=(self.red.id,)),
        )

        plan = self.exporter.plan(data)

        self.assertEqual(plan.count("added"), 1)
        self.assertEqual(plan.accepted_count, 1)
        self.assertEqual(plan.rejected_count, 0)
        self.assertTrue(plan.can_apply)
        self.assertTrue(plan.would_write)
        self.assertFalse(plan.destination.exists())

    def test_apply_adds_ids_without_removing_existing_ownership(self) -> None:
        self._write_owned([self.red.id])

        plan = self.exporter.plan([self.blue.id])
        result = self.exporter.apply(plan)

        self.assertTrue(result.applied)
        self.assertTrue(result.data_written)
        self.assertEqual(
            load_owned_filaments(plan.destination),
            {self.red.id, self.blue.id},
        )
        self.assertFalse(
            plan.destination.with_suffix(plan.destination.suffix + ".sha256").exists()
        )

    def test_already_owned_selection_is_idempotent(self) -> None:
        path = self._write_owned([self.red.id])
        original = path.read_bytes()

        plan = self.exporter.plan([self.red.id])
        result = self.exporter.apply(plan)

        self.assertEqual(plan.count("already_owned"), 1)
        self.assertFalse(plan.would_write)
        self.assertFalse(result.data_written)
        self.assertEqual(path.read_bytes(), original)

    def test_unknown_id_is_reported_and_blocks_apply(self) -> None:
        plan = self.exporter.plan(["unknown-pla-red"])

        self.assertFalse(plan.can_apply)
        self.assertEqual(plan.rejected_count, 1)
        self.assertEqual(plan.unmatched[0].filament_id, "unknown-pla-red")
        with self.assertRaisesRegex(ValueError, "unmatched IDs"):
            self.exporter.apply(plan)

    def test_new_user_filament_must_be_imported_before_ownership(self) -> None:
        custom = _record("custom-pla-ocean", maker="Custom", color="Ocean")
        data = FilamentExportData(
            [custom],
            FilamentMetadata(owned_filament_ids=(custom.id,)),
        )

        before = self.exporter.plan(data)
        self.assertFalse(before.can_apply)

        catalog_exporter = UserFilamentsExporter(self.data_dir)
        catalog_exporter.apply(catalog_exporter.plan(data))
        after = self.exporter.plan(data)
        result = self.exporter.apply(after)

        self.assertTrue(after.can_apply)
        self.assertTrue(result.data_written)
        self.assertEqual(load_owned_filaments(self.data_dir), {custom.id})

    def test_stale_destination_is_rejected(self) -> None:
        path = self._write_owned([self.red.id])
        plan = self.exporter.plan([self.blue.id])
        path.write_text(
            json.dumps({"owned_filaments": [self.blue.id]}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(RuntimeError, "changed after planning"):
            self.exporter.apply(plan)

    def test_catalog_removal_after_planning_is_rejected(self) -> None:
        plan = self.exporter.plan([self.blue.id])
        (self.data_dir / "filaments.json").write_text(
            json.dumps(serialize_filament_records([self.red])),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(RuntimeError, "catalog changed"):
            self.exporter.apply(plan)

    def test_plan_destination_must_belong_to_exporter(self) -> None:
        plan = self.exporter.plan([self.red.id])
        foreign = replace(plan, destination=self.data_dir / "other.json")

        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.exporter.apply(foreign)

    def test_rejects_invalid_duplicate_and_non_string_input_ids(self) -> None:
        invalid_inputs: tuple[tuple[object, type[Exception], str], ...] = (
            (self.red.id, TypeError, "iterable of strings"),
            (["Invalid ID"], ValueError, "invalid owned filament ID"),
            ([self.red.id, self.red.id], ValueError, "duplicate owned filament"),
            ([42], TypeError, "must be a string"),
        )
        for values, error_type, message in invalid_inputs:
            with self.subTest(values=values):
                with self.assertRaisesRegex(error_type, message):
                    self.exporter.plan(cast(list[str], values))

    def test_existing_unknown_ownership_is_rejected_before_merge(self) -> None:
        self._write_owned(["unknown-pla-red"])

        with self.assertRaisesRegex(ValueError, "absent from the effective catalog"):
            self.exporter.plan([self.red.id])

    def test_existing_unknown_ownership_preview_is_bounded(self) -> None:
        self._write_owned(
            [
                "unknown-pla-one",
                "unknown-pla-two",
                "unknown-pla-three",
                "unknown-pla-four",
            ]
        )

        with self.assertRaisesRegex(ValueError, r"unknown-pla-three, \.\.\."):
            self.exporter.plan([])

    def test_empty_selection_does_not_create_an_empty_file(self) -> None:
        plan = self.exporter.plan([])
        result = self.exporter.apply(plan)

        self.assertFalse(plan.would_write)
        self.assertFalse(result.data_written)
        self.assertFalse(plan.destination.exists())


if __name__ == "__main__":
    unittest.main()
