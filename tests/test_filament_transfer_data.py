"""Tests for format-neutral filament transfer models and importer contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from color_tools import export_filament_data
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.filament_palette import FilamentRecord
from color_tools.importers import FilamentImporter
from color_tools.importers.base import (
    ImporterDependency,
    ImporterMetadata,
    MissingImporterDependencyError,
)


class _BasicFilamentImporter(FilamentImporter):
    """Minimal filament importer used to exercise the public contract."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata("filaments", "Test filaments", ("test",))

    def _import_filaments_impl(self, input_path: Path) -> FilamentExportData:
        record = FilamentRecord(
            id="maker-pla-red",
            maker="Maker",
            type="PLA",
            finish=None,
            color="Red",
            hex="#ff0000",
        )
        return FilamentExportData(
            [record],
            FilamentMetadata(name=input_path.stem),
        )


class _UnavailableFilamentImporter(_BasicFilamentImporter):
    """Importer with an intentionally unavailable dependency."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata(
            "unavailable_filaments",
            "Unavailable test filaments",
            ("test",),
            dependencies=(ImporterDependency("missing", "missing_module"),),
        )


class TestFilamentMetadata(unittest.TestCase):
    """Validate normalization and independent default state."""

    def test_normalizes_collection_text_tags_and_owned_ids(self) -> None:
        metadata = FilamentMetadata(
            name=" Collection ",
            author=" Author ",
            description=" Description ",
            tags=(" owned ", "", " pla "),
            owned_filament_ids=(" maker-pla-red ", ""),
        )

        self.assertEqual(metadata.name, "Collection")
        self.assertEqual(metadata.author, "Author")
        self.assertEqual(metadata.description, "Description")
        self.assertEqual(metadata.tags, ("owned", "pla"))
        self.assertEqual(metadata.owned_filament_ids, ("maker-pla-red",))
        self.assertTrue(metadata.has_metadata)

    def test_defaults_are_empty_and_properties_are_not_shared(self) -> None:
        first = FilamentMetadata()
        second = FilamentMetadata()

        self.assertFalse(first.has_metadata)
        first.properties["external_ids"] = {"maker-pla-red": "uuid"}
        self.assertNotIn("external_ids", second.properties)


class TestFilamentExportData(unittest.TestCase):
    """Validate the metadata-bearing filament transfer container."""

    def test_default_metadata_is_independent(self) -> None:
        first = FilamentExportData([])
        second = FilamentExportData([])

        first.metadata.name = "First"
        self.assertEqual(second.metadata.name, "")

    def test_public_export_facade_uses_existing_filament_exporters(self) -> None:
        record = FilamentRecord(
            id="maker-pla-red",
            maker="Maker",
            type="PLA",
            finish=None,
            color="Red",
            hex="#ff0000",
        )
        data = FilamentExportData([record])

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "filaments.json"
            result = export_filament_data(data, "json", output_path)

            self.assertEqual(result, str(output_path))
            self.assertTrue(output_path.is_file())


class TestFilamentImporter(unittest.TestCase):
    """Exercise shared validation and filament-specific dispatch."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.path = self.directory / "collection.test"
        self.path.write_text("content", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_import_returns_filament_transfer_data(self) -> None:
        result = _BasicFilamentImporter().import_filaments(self.path)

        self.assertEqual(result.metadata.name, "collection")
        self.assertEqual(result.filaments[0].id, "maker-pla-red")

    def test_rejects_missing_path_and_directory(self) -> None:
        importer = _BasicFilamentImporter()

        with self.assertRaisesRegex(FileNotFoundError, "Filament file does not exist"):
            importer.import_filaments(self.directory / "missing.test")
        with self.assertRaisesRegex(IsADirectoryError, "not a file"):
            importer.import_filaments(self.directory)

    def test_detection_reuses_shared_extension_and_content_contract(self) -> None:
        importer = _BasicFilamentImporter()

        self.assertTrue(importer.can_import(self.path))
        self.assertFalse(importer.can_import(self.directory / "collection.other"))

    def test_dependency_failure_precedes_format_parsing(self) -> None:
        importer = _UnavailableFilamentImporter()

        with patch("color_tools.importers.base.find_spec", return_value=None):
            with self.assertRaises(MissingImporterDependencyError):
                importer.import_filaments(self.path)


if __name__ == "__main__":
    unittest.main()
