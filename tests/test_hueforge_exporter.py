"""Tests for HueForge filament-library export."""

from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import cast

from color_tools.export import export_filaments
from color_tools.exporters import (
    HueForgeExporter,
    HueForgeExportOptions,
    get_exporter,
    list_export_formats,
)
from color_tools.filament_palette import FilamentRecord


class TestHueForgeExporter(unittest.TestCase):
    """Exercise HueForge mapping, options, and validation."""

    def setUp(self) -> None:
        """Create a representative filament with a TD value."""
        self.filament = FilamentRecord(
            id="test-co_pla_tealie",
            maker="Test Co",
            type="PLA",
            finish="Basic",
            color="Tealie",
            hex="#2a6680",
            td_value=5.0,
            source="test.json",
        )

    def test_registered_as_filament_only_json_exporter(self) -> None:
        """Registry metadata exposes the HueForge format correctly."""
        exporter = get_exporter("hueforge")
        self.assertIsInstance(exporter, HueForgeExporter)
        self.assertEqual(exporter.metadata.file_extension, "json")
        self.assertFalse(exporter.metadata.supports_colors)
        self.assertTrue(exporter.metadata.supports_filaments)
        self.assertIn("hueforge", list_export_formats("filaments"))
        self.assertNotIn("hueforge", list_export_formats("colors"))

    def test_exports_expected_fields_and_deterministic_uuid(self) -> None:
        """Every HueForge field maps from the corresponding filament data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "personal_library.json"
            result = export_filaments(
                [self.filament],
                "hueforge",
                output_path,
            )
            data = cast(
                dict[str, list[dict[str, object]]],
                json.loads(output_path.read_text(encoding="utf-8")),
            )

        expected_uuid = uuid.uuid5(
            uuid.NAMESPACE_URL,
            "color-tools:filament:test-co_pla_tealie",
        )
        self.assertEqual(result, str(output_path))
        self.assertEqual(
            data,
            {
                "Filaments": [
                    {
                        "Brand": "Test Co",
                        "Color": "#2A6680",
                        "Name": "Tealie",
                        "Owned": True,
                        "Transmissivity": 5.0,
                        "Type": "PLA",
                        "uuid": f"{{{expected_uuid}}}",
                    }
                ]
            },
        )

    def test_owned_option_can_create_unowned_catalog_entries(self) -> None:
        """The typed option applies one owned state to the export operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "catalog.json"
            export_filaments(
                [self.filament],
                "hueforge",
                output_path,
                options=HueForgeExportOptions(owned=False),
            )
            data = cast(
                dict[str, list[dict[str, object]]],
                json.loads(output_path.read_text(encoding="utf-8")),
            )

        self.assertIs(data["Filaments"][0]["Owned"], False)

    def test_owned_option_rejects_non_boolean_values(self) -> None:
        """Truthy integers are not accepted as owned states."""
        with self.assertRaisesRegex(TypeError, "owned"):
            HueForgeExportOptions(owned=cast(bool, 1))

    def test_missing_td_rejects_entire_export_before_writing(self) -> None:
        """HueForge export is all-or-nothing when any TD value is absent."""
        missing_td = FilamentRecord(
            id="test-co_pla_unknown",
            maker="Test Co",
            type="PLA",
            finish=None,
            color="Unknown",
            hex="#123456",
            source="test.json",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "not-written.json"
            with self.assertRaisesRegex(
                ValueError,
                "1 selected filament.*test-co_pla_unknown",
            ):
                export_filaments(
                    [self.filament, missing_td],
                    "hueforge",
                    output_path,
                )
            self.assertFalse(output_path.exists())

    def test_missing_id_rejects_export_before_writing(self) -> None:
        """HueForge UUID generation requires a stable, non-empty source ID."""
        missing_id = FilamentRecord(
            id="",
            maker="Test Co",
            type="PLA",
            finish=None,
            color="Unidentified",
            hex="#123456",
            td_value=4.0,
            source="test.json",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "not-written.json"
            with self.assertRaisesRegex(ValueError, "non-empty ID"):
                export_filaments([missing_id], "hueforge", output_path)
            self.assertFalse(output_path.exists())

    def test_duplicate_ids_reject_export_before_writing(self) -> None:
        """Distinct records cannot share the UUID input identity."""
        duplicate_id = FilamentRecord(
            id=self.filament.id,
            maker="Other Co",
            type="PETG",
            finish=None,
            color="Also Tealie",
            hex="#336699",
            td_value=6.0,
            source="test.json",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "not-written.json"
            with self.assertRaisesRegex(ValueError, "duplicate ID"):
                export_filaments(
                    [self.filament, duplicate_id],
                    "hueforge",
                    output_path,
                )
            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
