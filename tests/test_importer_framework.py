"""Tests for palette importer base and registry contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers import registry
from color_tools.importers.base import (
    ImporterDependency,
    ImporterMetadata,
    MissingImporterDependencyError,
    PaletteImporter,
)


class _BasicImporter(PaletteImporter):
    """Minimal available importer used to exercise the base contract."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata("basic", "Basic palette", ("test",))

    def _import_palette_impl(self, input_path: Path) -> PaletteExportData:
        return PaletteExportData([], PaletteMetadata(name=input_path.stem))


class _RejectingImporter(_BasicImporter):
    """Importer that shares an extension but rejects candidate contents."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata("rejecting", "Rejecting palette", ("test",))

    def _can_import_impl(self, input_path: Path) -> bool:
        return False


class _SecondAcceptingImporter(_BasicImporter):
    """Second matching importer used to verify ambiguity reporting."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata("second", "Second palette", ("test",))


class _UnavailableImporter(_BasicImporter):
    """Importer with a deliberately absent optional dependency."""

    @property
    def metadata(self) -> ImporterMetadata:
        return ImporterMetadata(
            "unavailable",
            "Unavailable palette",
            ("test", "missing"),
            dependencies=(ImporterDependency("missing-package", "missing_module"),),
        )


class TestImporterMetadata(unittest.TestCase):
    """Validate importer metadata at construction time."""

    def test_rejects_empty_required_metadata(self) -> None:
        cases = (
            (("", "Description", ("test",)), "name"),
            (("name", "", ("test",)), "description"),
            (("name", "Description", ()), "file_extensions"),
            (("name", "Description", ("test", "")), "extensions"),
            (("name", "Description", (".test",)), "leading dot"),
        )

        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ValueError, message):
                    ImporterMetadata(*arguments)


class TestMissingImporterDependencies(unittest.TestCase):
    """Verify dependency diagnostics and public exception attributes."""

    def test_message_without_an_optional_extra(self) -> None:
        dependency = ImporterDependency("package-one", "module_one")
        error = MissingImporterDependencyError("demo", (dependency,))

        self.assertEqual(error.importer_name, "demo")
        self.assertEqual(error.dependencies, (dependency,))
        self.assertEqual(
            str(error),
            "demo importer requires missing optional dependency: package-one.",
        )

    def test_message_with_one_optional_extra(self) -> None:
        dependency = ImporterDependency("package-one", "module_one", "images")
        error = MissingImporterDependencyError("demo", (dependency,))

        self.assertIn("missing optional dependency: package-one", str(error))
        self.assertIn("Install the 'images' optional extra", str(error))

    def test_message_with_multiple_optional_extras(self) -> None:
        dependencies = (
            ImporterDependency("package-one", "module_one", "zeta"),
            ImporterDependency("package-two", "module_two", "alpha"),
        )
        error = MissingImporterDependencyError("demo", dependencies)

        self.assertIn("missing optional dependencies: package-one, package-two", str(error))
        self.assertIn("required optional extras", str(error))
        self.assertIn("alpha, zeta", str(error))


class TestPaletteImporterBase(unittest.TestCase):
    """Exercise validation and detection owned by PaletteImporter."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.path = self.directory / "palette.test"
        self.path.write_text("content", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_import_palette_rejects_missing_path_and_directory(self) -> None:
        importer = _BasicImporter()

        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            importer.import_palette(self.directory / "missing.test")
        with self.assertRaisesRegex(IsADirectoryError, "not a file"):
            importer.import_palette(self.directory)

    def test_can_import_rejects_wrong_extension_missing_directory_and_unavailable(self) -> None:
        importer = _BasicImporter()

        self.assertFalse(importer.can_import(self.directory / "palette.other"))
        self.assertFalse(importer.can_import(self.directory / "missing.test"))
        self.assertFalse(importer.can_import(self.directory))
        with patch("color_tools.importers.base.find_spec", return_value=None):
            self.assertFalse(_UnavailableImporter().can_import(self.path))

    def test_default_detector_accepts_valid_matching_file_case_insensitively(self) -> None:
        uppercase_path = self.directory / "palette.TEST"
        uppercase_path.write_text("content", encoding="utf-8")

        self.assertTrue(_BasicImporter().can_import(uppercase_path))

    def test_ensure_dependencies_raises_documented_exception(self) -> None:
        importer = _UnavailableImporter()

        with patch("color_tools.importers.base.find_spec", return_value=None):
            with self.assertRaises(MissingImporterDependencyError) as context:
                importer.import_palette(self.path)

        self.assertEqual(context.exception.importer_name, "unavailable")
        self.assertEqual(
            context.exception.dependencies,
            importer.metadata.dependencies,
        )


class TestImporterRegistryContracts(unittest.TestCase):
    """Exercise registry selection with isolated temporary state."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.path = self.directory / "palette.test"
        self.path.write_text("content", encoding="utf-8")
        empty_registry: dict[str, type[PaletteImporter]] = {}
        registry_patch = patch.object(registry, "_IMPORTERS", empty_registry)
        registry_patch.start()
        self.addCleanup(registry_patch.stop)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_duplicate_registration_is_rejected(self) -> None:
        registry.register_importer(_BasicImporter)

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register_importer(_BasicImporter)

    def test_unknown_explicit_format_lists_available_formats(self) -> None:
        registry.register_importer(_BasicImporter)
        registry.register_importer(_RejectingImporter)

        with self.assertRaisesRegex(
            ValueError,
            r"Unknown import format: 'unknown'.*Available formats: basic, rejecting",
        ):
            registry.get_importer("unknown")

    def test_available_only_listings_exclude_unavailable_importers(self) -> None:
        registry.register_importer(_BasicImporter)
        registry.register_importer(_UnavailableImporter)

        with patch("color_tools.importers.base.find_spec", return_value=None):
            self.assertEqual(registry.list_import_formats(), {"basic": "Basic palette"})
            self.assertEqual(
                set(registry.list_import_formats(available_only=False)),
                {"basic", "unavailable"},
            )
            self.assertEqual(
                [item.metadata.name for item in registry.get_importers_for_extension("test")],
                ["basic"],
            )
            self.assertEqual(
                {
                    item.metadata.name
                    for item in registry.get_importers_for_extension(
                        ".test", available_only=False
                    )
                },
                {"basic", "unavailable"},
            )

    def test_detection_rejects_missing_file_and_unregistered_extension(self) -> None:
        registry.register_importer(_BasicImporter)

        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            registry.detect_importer(self.directory / "missing.test")
        unknown = self.directory / "palette.unknown"
        unknown.write_text("content", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "extension '.unknown'"):
            registry.detect_importer(unknown)

    def test_detection_reports_no_recognizing_candidate(self) -> None:
        registry.register_importer(_RejectingImporter)

        with self.assertRaisesRegex(
            ValueError,
            r"Unable to determine palette format.*Candidate importers: rejecting",
        ):
            registry.detect_importer(self.path)

    def test_detection_reports_ambiguous_candidates(self) -> None:
        registry.register_importer(_BasicImporter)
        registry.register_importer(_SecondAcceptingImporter)

        with self.assertRaisesRegex(
            ValueError,
            r"ambiguous.*Matching importers: basic, second",
        ):
            registry.detect_importer(self.path)

    def test_explicit_and_automatic_import_delegate_to_selected_importer(self) -> None:
        registry.register_importer(_BasicImporter)

        explicit = registry.import_palette(self.path, format_name="basic")
        automatic = registry.import_palette(self.path)

        self.assertEqual(explicit.metadata.name, "palette")
        self.assertEqual(automatic.metadata.name, "palette")


if __name__ == "__main__":
    unittest.main()
