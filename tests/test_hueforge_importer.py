"""Tests for HueForge filament parsing and format detection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from color_tools.importers import (
    detect_filament_importer,
    get_filament_importer,
    import_filaments,
)


def _filament(**changes: object) -> dict[str, object]:
    """Return a complete representative HueForge filament object."""
    record: dict[str, object] = {
        "Brand": "BambuLab Matte",
        "Color": "#f7f7f7",
        "Name": "Ivory White",
        "Owned": True,
        "Transmissivity": 3,
        "Type": "PLA",
        "uuid": "{c4e33b80-6178-471a-bf00-6e21374ea6b4}",
    }
    record.update(changes)
    return record


class TestHueForgeImporter(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write(self, document: object) -> Path:
        path = self.directory / "library.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_detects_standard_library_and_preserves_owned_transfer_state(self) -> None:
        path = self._write({"Filaments": [_filament()]})

        importer = detect_filament_importer(path)
        data = import_filaments(path)

        self.assertEqual(importer.metadata.name, "hueforge")
        self.assertEqual(data.filaments[0].maker, "BambuLab Matte")
        self.assertEqual(data.filaments[0].hex, "#F7F7F7")
        self.assertEqual(data.filaments[0].td_value, 3.0)
        self.assertEqual(data.metadata.owned_filament_ids, (data.filaments[0].id,))
        self.assertEqual(data.metadata.properties["hueforge_format"], "filament_library")

    def test_personal_library_metadata_and_float_td_are_validated(self) -> None:
        path = self._write(
            {
                "Filaments": [_filament(Owned=False, Transmissivity=0.5)],
                "exported_at": "2026-10-16T23:34:13",
                "format": "hueforge_personal_library",
                "version": 1,
            }
        )

        data = get_filament_importer("hueforge").import_filaments(path)

        self.assertEqual(data.filaments[0].td_value, 0.5)
        self.assertEqual(data.metadata.owned_filament_ids, ())
        self.assertEqual(
            data.metadata.properties["hueforge_format"],
            "hueforge_personal_library",
        )

    def test_secondary_fields_and_tags_are_intentionally_ignored(self) -> None:
        path = self._write(
            {
                "Filaments": [
                    _filament(
                        Secondary_Color="#ff55ff",
                        Secondary_Strength=3.5,
                        Secondary_Type=1,
                        Tags=["test2", "test"],
                    )
                ]
            }
        )

        data = import_filaments(path)

        self.assertEqual(len(data.filaments[0].rgb_components), 1)
        self.assertNotIn("uuid", data.metadata.properties)

    def test_error_image_filament_is_skipped_and_reported(self) -> None:
        path = self._write(
            {
                "Filaments": [
                    _filament(Brand="", Type="IMAGE"),
                    _filament(Owned=False),
                ]
            }
        )

        data = import_filaments(path)

        self.assertEqual(len(data.filaments), 1)
        self.assertEqual(
            data.metadata.properties["skipped_error_filament_indices"],
            (0,),
        )

    def test_duplicate_generated_ids_receive_stable_suffixes(self) -> None:
        path = self._write(
            {
                "Filaments": [
                    _filament(),
                    _filament(uuid="{00000000-0000-0000-0000-000000000001}"),
                ]
            }
        )

        data = import_filaments(path)

        self.assertEqual(data.filaments[1].id, f"{data.filaments[0].id}-2")

    def test_rejects_duplicate_hueforge_uuid(self) -> None:
        path = self._write({"Filaments": [_filament(), _filament()]})

        with self.assertRaisesRegex(ValueError, "duplicate uuid"):
            import_filaments(path)

    def test_rejects_missing_transmissivity(self) -> None:
        record = _filament()
        del record["Transmissivity"]
        path = self._write({"Filaments": [record]})

        with self.assertRaisesRegex(ValueError, "missing required.*Transmissivity"):
            get_filament_importer("hueforge").import_filaments(path)

    def test_rejects_invalid_field_types_and_uuid(self) -> None:
        invalid_values: tuple[tuple[str, object, str], ...] = (
            ("Brand", "", "Brand must be a non-empty string"),
            ("Owned", 1, "Owned must be a boolean"),
            ("Transmissivity", True, "Transmissivity must"),
            ("Transmissivity", float("inf"), "Transmissivity must"),
            ("Color", "#000000-#FFFFFF", "exactly one hex color"),
            ("uuid", str(UUID(int=0)), "braced UUID"),
            ("uuid", 1, "braced UUID"),
            ("uuid", "{not-a-uuid}", "valid braced UUID"),
        )
        for field_name, value, message in invalid_values:
            with self.subTest(field_name=field_name, value=value):
                path = self._write({"Filaments": [_filament(**{field_name: value})]})
                with self.assertRaisesRegex(ValueError, message):
                    get_filament_importer("hueforge").import_filaments(path)

    def test_rejects_partial_or_invalid_personal_envelope(self) -> None:
        for extra, message in (
            ({"format": "hueforge_personal_library"}, "missing top-level"),
            (
                {
                    "format": "wrong",
                    "version": 1,
                    "exported_at": "2026-10-16T23:34:13",
                },
                "Unsupported.*format",
            ),
            (
                {
                    "format": "hueforge_personal_library",
                    "version": 2,
                    "exported_at": "2026-10-16T23:34:13",
                },
                "Unsupported.*version",
            ),
            (
                {
                    "format": "hueforge_personal_library",
                    "version": 1,
                    "exported_at": 1,
                },
                "exported_at must",
            ),
            (
                {
                    "format": "hueforge_personal_library",
                    "version": 1,
                    "exported_at": "not-a-date",
                },
                "exported_at must",
            ),
        ):
            with self.subTest(extra=extra):
                path = self._write({"Filaments": [], **extra})
                with self.assertRaisesRegex(ValueError, message):
                    get_filament_importer("hueforge").import_filaments(path)

    def test_detection_and_document_shape_failures_are_reported(self) -> None:
        importer = get_filament_importer("hueforge")
        invalid_json = self.directory / "invalid.json"
        invalid_json.write_text("{", encoding="utf-8")
        self.assertFalse(importer.can_import(invalid_json))
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            importer.import_filaments(invalid_json)

        invalid_documents: tuple[tuple[object, str], ...] = (
            ([], "Expected HueForge object"),
            ({"Filaments": [], "extra": True}, "Unknown HueForge top-level"),
            ({"Filaments": {}}, "Filaments must be an array"),
            ({"Filaments": [1]}, "record must be an object"),
            ({"Filaments": [_filament(extra=True)]}, "unknown field.*extra"),
        )
        for document, message in invalid_documents:
            with self.subTest(document=document):
                path = self._write(document)
                with self.assertRaisesRegex(ValueError, message):
                    importer.import_filaments(path)


if __name__ == "__main__":
    unittest.main()
