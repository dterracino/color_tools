"""Tests for user-color import, planning, and persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from color_tools.constants import ColorConstants
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.user_colors_exporter import UserColorsExporter
from color_tools.importers import detect_importer, get_importer, import_palette
from color_tools.palette import ColorRecord, load_colors


def _system_document(records: list[ColorRecord]) -> list[dict[str, object]]:
    return [
        {
            "name": record.name,
            "hex": record.hex,
            "rgb": list(record.rgb),
            "hsl": list(record.hsl),
            "lab": list(record.lab),
            "lch": list(record.lch),
        }
        for record in records
    ]


class UserColorTransferTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name)
        self.user_dir = self.data_dir / "user"
        self.user_dir.mkdir()
        self.system_records = [
            ColorRecord.from_hex("#ff0000", name="Red", source="colors.json"),
            ColorRecord.from_hex("#0000ff", name="Blue", source="colors.json"),
        ]
        (self.data_dir / "colors.json").write_text(
            json.dumps(_system_document(self.system_records), indent=2) + "\n",
            encoding="utf-8",
        )
        self.exporter = UserColorsExporter(self.data_dir)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _record(self, name: str, value: str) -> ColorRecord:
        return ColorRecord.from_hex(value, name=name, source="imported.json")

    def _write_user_colors(self, values: list[dict[str, str]]) -> Path:
        path = self.user_dir / "user-colors.json"
        path.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
        return path


class TestUserColorsImporter(UserColorTransferTestCase):
    def test_registry_detects_and_imports_minimal_schema(self) -> None:
        path = self._write_user_colors(
            [{"name": " Ocean ", "hex": "#123456"}]
        )

        importer = detect_importer(path)
        imported = import_palette(path)

        self.assertEqual(importer.metadata.name, "user_colors")
        self.assertEqual(imported.colors[0].name, "Ocean")
        self.assertEqual(imported.colors[0].rgb, (18, 52, 86))
        self.assertEqual(imported.colors[0].source, "user-colors.json")

    def test_explicit_import_rejects_derived_fields(self) -> None:
        path = self._write_user_colors(
            [{"name": "Ocean", "hex": "#123456", "rgb": "stale"}]
        )

        with self.assertRaisesRegex(ValueError, "unexpected field.*rgb"):
            get_importer("user_colors").import_palette(path)


class TestUserColorsExporter(UserColorTransferTestCase):
    def test_plan_is_read_only_and_reports_addition(self) -> None:
        record = self._record("Ocean", "#123456")

        plan = self.exporter.plan([record])

        self.assertEqual(plan.count("added"), 1)
        self.assertEqual(plan.accepted_count, 1)
        self.assertEqual(plan.skipped_count, 0)
        self.assertEqual(plan.rejected_count, 0)
        self.assertTrue(plan.can_apply)
        self.assertTrue(plan.would_write)
        self.assertFalse(plan.destination.exists())
        self.assertFalse(plan.sidecar.exists())

    def test_apply_writes_minimal_schema_and_matching_sidecar(self) -> None:
        plan = self.exporter.plan(
            PaletteExportData([self._record("Ocean", "#123456")])
        )

        result = self.exporter.apply(plan)

        self.assertTrue(result.applied)
        self.assertTrue(result.data_written)
        self.assertTrue(result.sidecar_written)
        document = json.loads(plan.destination.read_text(encoding="utf-8"))
        self.assertEqual(document, [{"name": "Ocean", "hex": "#123456"}])
        valid, error = ColorConstants.verify_user_data_file(plan.destination)
        self.assertTrue(valid, error)
        loaded = load_colors(self.data_dir)
        self.assertEqual(loaded[-1].name, "Ocean")

    def test_exact_existing_color_is_unchanged_and_does_not_write(self) -> None:
        plan = self.exporter.plan([self._record(" red ", "#ff0000")])

        result = self.exporter.apply(plan)

        self.assertEqual(plan.count("unchanged"), 1)
        self.assertFalse(plan.would_write)
        self.assertFalse(result.data_written)
        self.assertFalse(plan.destination.exists())

    def test_name_conflict_requires_explicit_replace(self) -> None:
        record = self._record("RED", "#aa0000")

        blocked = self.exporter.plan([record])
        replacing = self.exporter.plan([record], conflict_policy="replace")

        self.assertEqual(blocked.count("conflict"), 1)
        with self.assertRaisesRegex(ValueError, "unresolved conflicts"):
            self.exporter.apply(blocked)
        self.assertEqual(replacing.count("updated"), 1)
        self.exporter.apply(replacing)
        loaded = load_colors(self.data_dir)
        self.assertEqual(loaded[0].rgb, (170, 0, 0))
        self.assertEqual(loaded[0].source, "user-colors.json")

    def test_skip_policy_leaves_name_conflict_unchanged(self) -> None:
        plan = self.exporter.plan(
            [self._record("Red", "#aa0000")],
            conflict_policy="skip",
        )

        result = self.exporter.apply(plan)

        self.assertEqual(plan.count("skipped"), 1)
        self.assertFalse(result.data_written)
        self.assertFalse(plan.destination.exists())

    def test_rgb_conflict_cannot_be_replaced_under_another_name(self) -> None:
        plan = self.exporter.plan(
            [self._record("Scarlet", "#ff0000")],
            conflict_policy="replace",
        )

        self.assertEqual(plan.count("conflict"), 1)
        self.assertIn("different color name", plan.conflicts[0].message)

    def test_existing_user_update_preserves_order(self) -> None:
        self._write_user_colors(
            [
                {"name": "First", "hex": "#010203"},
                {"name": "Second", "hex": "#040506"},
            ]
        )
        plan = self.exporter.plan(
            [self._record("first", "#070809")],
            conflict_policy="replace",
        )

        self.exporter.apply(plan)

        document = json.loads(plan.destination.read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in document], ["first", "Second"])

    def test_apply_rejects_destination_changed_after_planning(self) -> None:
        path = self._write_user_colors([{"name": "First", "hex": "#010203"}])
        plan = self.exporter.plan([self._record("Second", "#040506")])
        path.write_text("[]\n", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "changed after planning"):
            self.exporter.apply(plan)

    def test_duplicate_input_names_are_rejected_cumulatively(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate input color name"):
            self.exporter.plan(
                [
                    self._record("Ocean", "#123456"),
                    self._record(" ocean ", "#654321"),
                ]
            )

    def test_import_export_round_trip_is_idempotent(self) -> None:
        source = self._write_user_colors(
            [{"name": "Ocean", "hex": "#123456"}]
        )
        imported = get_importer("user_colors").import_palette(source)
        source.unlink()

        first = self.exporter.plan(imported)
        self.exporter.apply(first)
        second = self.exporter.plan(imported)

        self.assertEqual(second.count("unchanged"), 1)
        self.assertFalse(second.would_write)


if __name__ == "__main__":
    unittest.main()
