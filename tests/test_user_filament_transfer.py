"""Tests for user-filament import, planning, and persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from color_tools._filament_data import serialize_filament_records
from color_tools.constants import ColorConstants
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.user_filaments_exporter import UserFilamentsExporter
from color_tools.filament_palette import FilamentRecord, load_filaments
from color_tools.importers import (
    detect_filament_importer,
    get_filament_importer,
    import_filaments,
    list_filament_import_formats,
)


class UserFilamentTransferTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name)
        self.user_dir = self.data_dir / "user"
        self.user_dir.mkdir()
        self.system_records = [
            self._record(
                "maker-pla-basic-red",
                maker="Maker",
                type_name="PLA",
                finish="Basic",
                color="Red",
                hex_value="#FF0000",
                source="filaments.json",
            ),
            self._record(
                "maker-petg-blue",
                maker="Maker",
                type_name="PETG",
                finish=None,
                color="Blue",
                hex_value="#0000FF",
                source="filaments.json",
            ),
        ]
        (self.data_dir / "filaments.json").write_text(
            json.dumps(serialize_filament_records(self.system_records), indent=2)
            + "\n",
            encoding="utf-8",
        )
        self.exporter = UserFilamentsExporter(self.data_dir)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def _record(
        filament_id: str,
        *,
        maker: str = "Custom",
        type_name: str = "PLA",
        finish: str | None = None,
        color: str = "Ocean",
        hex_value: str = "#123456",
        td_value: float | None = None,
        other_names: list[str] | None = None,
        source: str = "imported.json",
    ) -> FilamentRecord:
        return FilamentRecord(
            id=filament_id,
            maker=maker,
            type=type_name,
            finish=finish,
            color=color,
            hex=hex_value,
            td_value=td_value,
            other_names=other_names,
            source=source,
        )

    def _write_user_filaments(self, records: list[FilamentRecord]) -> Path:
        path = self.user_dir / "user-filaments.json"
        path.write_text(
            json.dumps(serialize_filament_records(records), indent=2) + "\n",
            encoding="utf-8",
        )
        return path


class TestUserFilamentsImporter(UserFilamentTransferTestCase):
    def test_registry_detects_and_imports_user_filaments(self) -> None:
        path = self._write_user_filaments(
            [
                self._record(
                    "custom-pla-ocean",
                    hex_value="#123456-#ABCDEF",
                    td_value=2.5,
                    other_names=["Deep Ocean"],
                )
            ]
        )

        importer = detect_filament_importer(path)
        imported = import_filaments(path)

        self.assertEqual(importer.metadata.name, "user_filaments")
        self.assertIn("user_filaments", list_filament_import_formats())
        self.assertEqual(imported.filaments[0].rgb_components[1], (171, 205, 239))
        self.assertEqual(imported.filaments[0].source, "user-filaments.json")

    def test_explicit_import_rejects_unknown_fields(self) -> None:
        path = self.user_dir / "incoming.json"
        document = serialize_filament_records(
            [self._record("custom-pla-ocean")]
        )[0]
        document["derived_rgb"] = [18, 52, 86]
        path.write_text(json.dumps([document]), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "unknown field.*derived_rgb"):
            get_filament_importer("user_filaments").import_filaments(path)


class TestUserFilamentsExporter(UserFilamentTransferTestCase):
    def test_plan_is_read_only_and_reports_addition(self) -> None:
        plan = self.exporter.plan([self._record("custom-pla-ocean")])

        self.assertEqual(plan.count("added"), 1)
        self.assertEqual(plan.accepted_count, 1)
        self.assertEqual(plan.skipped_count, 0)
        self.assertEqual(plan.rejected_count, 0)
        self.assertTrue(plan.can_apply)
        self.assertTrue(plan.would_write)
        self.assertFalse(plan.destination.exists())
        self.assertFalse(plan.sidecar.exists())

    def test_apply_writes_source_schema_and_matching_sidecar(self) -> None:
        record = self._record(
            "custom-pla-ocean",
            hex_value="#123456, #abcdef",
            td_value=3,
            other_names=["Deep Ocean"],
        )
        plan = self.exporter.plan(FilamentExportData([record]))

        result = self.exporter.apply(plan)

        self.assertTrue(result.data_written)
        self.assertTrue(result.sidecar_written)
        document = json.loads(plan.destination.read_text(encoding="utf-8"))
        self.assertEqual(
            set(document[0]),
            {"id", "maker", "type", "finish", "color", "hex", "td_value", "other_names"},
        )
        self.assertEqual(document[0]["hex"], "#123456-#ABCDEF")
        valid, error = ColorConstants.verify_user_data_file(plan.destination)
        self.assertTrue(valid, error)
        self.assertEqual(load_filaments(self.data_dir)[-1].id, "custom-pla-ocean")

    def test_exact_existing_id_and_fields_are_unchanged(self) -> None:
        plan = self.exporter.plan([self.system_records[0]])
        result = self.exporter.apply(plan)

        self.assertEqual(plan.count("unchanged"), 1)
        self.assertFalse(plan.would_write)
        self.assertFalse(result.data_written)

    def test_same_id_difference_requires_explicit_replace(self) -> None:
        replacement = self._record(
            "maker-pla-basic-red",
            maker="Maker",
            type_name="PLA",
            finish="Basic",
            color="Crimson",
            hex_value="#AA0000",
        )

        blocked = self.exporter.plan([replacement])
        replacing = self.exporter.plan([replacement], conflict_policy="replace")

        self.assertEqual(blocked.count("conflict"), 1)
        with self.assertRaisesRegex(ValueError, "unresolved conflicts"):
            self.exporter.apply(blocked)
        self.assertEqual(replacing.count("updated"), 1)
        self.exporter.apply(replacing)
        loaded = load_filaments(self.data_dir)
        self.assertEqual(loaded[0].color, "Crimson")
        self.assertEqual(loaded[0].source, "user-filaments.json")

    def test_skip_policy_retains_same_id_record(self) -> None:
        replacement = self._record(
            "maker-pla-basic-red",
            color="Crimson",
            hex_value="#AA0000",
        )
        plan = self.exporter.plan([replacement], conflict_policy="skip")
        result = self.exporter.apply(plan)

        self.assertEqual(plan.count("skipped"), 1)
        self.assertFalse(result.data_written)

    def test_different_id_with_same_description_is_allowed_with_warning(self) -> None:
        duplicate_description = self._record(
            "maker-pla-basic-red-2",
            maker="Maker",
            type_name="PLA",
            finish="Basic",
            color="Red",
            hex_value="#FF0000",
        )

        plan = self.exporter.plan([duplicate_description])

        self.assertEqual(plan.count("added"), 1)
        self.assertTrue(plan.can_apply)
        self.assertEqual(len(plan.warnings), 1)
        self.assertIn("both IDs are kept", plan.warnings[0])

    def test_existing_user_update_preserves_order(self) -> None:
        self._write_user_filaments(
            [
                self._record("custom-pla-first", color="First"),
                self._record("custom-pla-second", color="Second"),
            ]
        )
        update = self._record(
            "custom-pla-first",
            color="Updated First",
            hex_value="#654321",
        )
        plan = self.exporter.plan([update], conflict_policy="replace")

        self.exporter.apply(plan)

        document = json.loads(plan.destination.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["id"] for item in document],
            ["custom-pla-first", "custom-pla-second"],
        )
        self.assertEqual(document[0]["color"], "Updated First")

    def test_apply_rejects_destination_changed_after_planning(self) -> None:
        path = self._write_user_filaments(
            [self._record("custom-pla-first", color="First")]
        )
        plan = self.exporter.plan(
            [self._record("custom-pla-second", color="Second")]
        )
        path.write_text("[]\n", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "changed after planning"):
            self.exporter.apply(plan)

    def test_duplicate_input_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate input filament ID"):
            self.exporter.plan(
                [
                    self._record("custom-pla-ocean"),
                    self._record("custom-pla-ocean", hex_value="#654321"),
                ]
            )

    def test_invalid_input_id_is_rejected_by_canonical_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must contain"):
            self.exporter.plan([self._record("Invalid_ID")])

    def test_import_export_round_trip_is_idempotent(self) -> None:
        source = self._write_user_filaments(
            [self._record("custom-pla-ocean")]
        )
        imported = get_filament_importer("user_filaments").import_filaments(source)
        source.unlink()

        first = self.exporter.plan(imported)
        self.exporter.apply(first)
        second = self.exporter.plan(imported)

        self.assertEqual(second.count("unchanged"), 1)
        self.assertFalse(second.would_write)


if __name__ == "__main__":
    unittest.main()
