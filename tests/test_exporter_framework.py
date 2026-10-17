"""Contract tests for the exporter base classes."""

from __future__ import annotations

import re
import tempfile
import unittest
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import cast
from unittest.mock import patch

from color_tools.exporters.base import (
    ExporterDependency,
    ExporterMetadata,
    MissingExporterDependencyError,
    PaletteExporter,
)
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.filament_palette import FilamentRecord
from color_tools.palette import ColorRecord


@dataclass(slots=True)
class _ExampleOptions(ExportOptionsBase):
    """Options used to exercise configurable exporter dispatch."""

    marker: str = "configured"


@dataclass(slots=True)
class _OtherOptions(ExportOptionsBase):
    """An incompatible options type used by validation tests."""


class _ContractExporter(PaletteExporter):
    """Small exporter whose capabilities and hooks are test-controlled."""

    def __init__(
        self,
        *,
        supports_colors: bool = True,
        supports_filaments: bool = False,
        options_type: type[ExportOptionsBase] | None = None,
        dependencies: tuple[ExporterDependency, ...] = (),
    ) -> None:
        self._metadata = ExporterMetadata(
            name="contract",
            description="Contract test exporter",
            file_extension="test",
            supports_colors=supports_colors,
            supports_filaments=supports_filaments,
            dependencies=dependencies,
            options_type=options_type,
        )
        self.calls: list[tuple[str, object, Path | str | None, object]] = []

    @property
    def metadata(self) -> ExporterMetadata:
        return self._metadata

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        self.calls.append(("colors", colors, output_path, None))
        return str(output_path)

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        self.calls.append(("colors-options", colors, output_path, options))
        return str(output_path)

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        self.calls.append(("filaments", filaments, output_path, None))
        return str(output_path)

    def _export_filaments_with_options_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        self.calls.append(("filaments-options", filaments, output_path, options))
        return str(output_path)


class _MissingHooksExporter(PaletteExporter):
    """Exporter that deliberately declares capabilities without hooks."""

    def __init__(
        self,
        *,
        supports_colors: bool = True,
        supports_filaments: bool = True,
        options_type: type[ExportOptionsBase] | None = None,
    ) -> None:
        self._metadata = ExporterMetadata(
            name="missing_hooks",
            description="Missing hooks test exporter",
            file_extension="test",
            supports_colors=supports_colors,
            supports_filaments=supports_filaments,
            options_type=options_type,
        )

    @property
    def metadata(self) -> ExporterMetadata:
        return self._metadata


class TestExporterMetadata(unittest.TestCase):
    """Validate exporter declarations at construction time."""

    def _metadata(
        self,
        *,
        name: str = "example",
        description: str = "Example exporter",
        file_extension: str = "txt",
        options_type: type[ExportOptionsBase] | None = None,
    ) -> ExporterMetadata:
        return ExporterMetadata(
            name=name,
            description=description,
            file_extension=file_extension,
            supports_colors=True,
            supports_filaments=False,
            options_type=options_type,
        )

    def test_required_text_fields_must_not_be_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "Exporter name"):
            self._metadata(name="")
        with self.assertRaisesRegex(ValueError, "Exporter description"):
            self._metadata(description="")
        with self.assertRaisesRegex(ValueError, "Exporter file_extension"):
            self._metadata(file_extension="")

    def test_extension_must_not_start_with_dot(self) -> None:
        with self.assertRaisesRegex(ValueError, "leading dot"):
            self._metadata(file_extension=".txt")

    def test_options_type_must_inherit_export_options_base(self) -> None:
        with self.assertRaisesRegex(TypeError, "ExportOptionsBase"):
            self._metadata(
                options_type=cast(type[ExportOptionsBase], str),
            )


class TestMissingExporterDependencyError(unittest.TestCase):
    """Verify dependency diagnostics and their public details."""

    def test_dependency_without_extra(self) -> None:
        dependency = ExporterDependency("package-a", "module_a")
        error = MissingExporterDependencyError("example", (dependency,))

        self.assertEqual(error.exporter_name, "example")
        self.assertEqual(error.dependencies, (dependency,))
        self.assertEqual(
            str(error),
            "example exporter requires missing optional dependency: package-a.",
        )

    def test_one_extra_has_singular_install_guidance(self) -> None:
        dependencies = (
            ExporterDependency("package-a", "module_a", "image"),
            ExporterDependency("package-b", "module_b", "image"),
        )
        error = MissingExporterDependencyError("example", dependencies)

        self.assertIn("dependencies: package-a, package-b", str(error))
        self.assertIn("'image' optional extra", str(error))

    def test_multiple_extras_are_sorted_in_install_guidance(self) -> None:
        dependencies = (
            ExporterDependency("package-a", "module_a", "zeta"),
            ExporterDependency("package-b", "module_b", "alpha"),
        )
        error = MissingExporterDependencyError("example", dependencies)

        self.assertIn(
            "required optional extras to enable this exporter: alpha, zeta",
            str(error),
        )


class TestExporterDispatch(unittest.TestCase):
    """Exercise capability, option, fallback, and hook dispatch contracts."""

    def setUp(self) -> None:
        self.colors = [ColorRecord.from_rgb((12, 34, 56), name="Example")]
        self.palette = PaletteExportData(self.colors)
        self.filaments = [
            FilamentRecord(
                id="maker-pla-red",
                maker="Maker",
                type="PLA",
                finish=None,
                color="Red",
                hex="#ff0000",
            )
        ]
        self.filament_data = FilamentExportData(
            self.filaments,
            FilamentMetadata(name="Owned filaments"),
        )

    def test_unsupported_operations_raise_focused_errors(self) -> None:
        exporter = _ContractExporter(
            supports_colors=False,
            supports_filaments=False,
        )

        with self.assertRaisesRegex(NotImplementedError, "color export"):
            exporter.export_colors(self.colors)
        with self.assertRaisesRegex(NotImplementedError, "color export"):
            exporter.export_palette(self.palette)
        with self.assertRaisesRegex(NotImplementedError, "filament export"):
            exporter.export_filaments([])
        with self.assertRaisesRegex(NotImplementedError, "filament export"):
            exporter.export_filament_data(self.filament_data)

    def test_options_are_rejected_when_none_are_accepted(self) -> None:
        exporter = _ContractExporter()
        with self.assertRaisesRegex(TypeError, "does not accept export options"):
            exporter.export_colors(self.colors, options=_ExampleOptions())

    def test_wrong_options_type_names_expected_and_actual_types(self) -> None:
        exporter = _ContractExporter(options_type=_ExampleOptions)
        with self.assertRaisesRegex(
            TypeError,
            "requires _ExampleOptions, got _OtherOptions",
        ):
            exporter.export_colors(self.colors, options=_OtherOptions())

    def test_palette_export_falls_back_to_color_hook(self) -> None:
        exporter = _ContractExporter()
        result = exporter.export_palette(self.palette, "palette.test")

        self.assertEqual(result, "palette.test")
        self.assertEqual(exporter.calls[0][0], "colors")
        self.assertIs(exporter.calls[0][1], self.colors)

    def test_configurable_palette_falls_back_to_configurable_color_hook(
        self,
    ) -> None:
        exporter = _ContractExporter(options_type=_ExampleOptions)
        options = _ExampleOptions()
        exporter.export_palette(self.palette, "palette.test", options)

        self.assertEqual(exporter.calls[0][0], "colors-options")
        self.assertIs(exporter.calls[0][1], self.colors)
        self.assertIs(exporter.calls[0][3], options)

    def test_filament_data_export_falls_back_to_filament_hook(self) -> None:
        exporter = _ContractExporter(supports_filaments=True)
        result = exporter.export_filament_data(
            self.filament_data,
            "filaments.test",
        )

        self.assertEqual(result, "filaments.test")
        self.assertEqual(exporter.calls[0][0], "filaments")
        self.assertIs(exporter.calls[0][1], self.filaments)

    def test_configurable_filament_data_uses_configurable_fallback(self) -> None:
        exporter = _ContractExporter(
            supports_filaments=True,
            options_type=_ExampleOptions,
        )
        options = _ExampleOptions()
        exporter.export_filament_data(
            self.filament_data,
            "filaments.test",
            options,
        )

        self.assertEqual(exporter.calls[0][0], "filaments-options")
        self.assertIs(exporter.calls[0][1], self.filaments)
        self.assertIs(exporter.calls[0][3], options)

    def test_declared_color_support_requires_color_hook(self) -> None:
        exporter = _MissingHooksExporter()
        with self.assertRaisesRegex(
            NotImplementedError,
            "declares color support.*_export_colors_impl",
        ):
            exporter.export_colors(self.colors)

    def test_declared_filament_support_requires_filament_hook(self) -> None:
        exporter = _MissingHooksExporter()
        with self.assertRaisesRegex(
            NotImplementedError,
            "declares filament support.*_export_filaments_impl",
        ):
            exporter.export_filaments([])

    def test_configurable_color_support_requires_options_hook(self) -> None:
        exporter = _MissingHooksExporter(options_type=_ExampleOptions)
        with self.assertRaisesRegex(
            NotImplementedError,
            "accepts export options.*_export_colors_with_options_impl",
        ):
            exporter.export_colors(self.colors, options=_ExampleOptions())

    def test_configurable_filament_support_requires_options_hook(self) -> None:
        exporter = _MissingHooksExporter(options_type=_ExampleOptions)
        with self.assertRaisesRegex(
            NotImplementedError,
            "accepts export options.*_export_filaments_with_options_impl",
        ):
            exporter.export_filaments([], options=_ExampleOptions())

    def test_dependency_check_precedes_hook_and_output(self) -> None:
        dependency = ExporterDependency("missing-package", "missing_module")
        exporter = _ContractExporter(dependencies=(dependency,))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-written.test"
            with patch(
                "color_tools.exporters.base.find_spec",
                return_value=None,
            ):
                with self.assertRaises(MissingExporterDependencyError):
                    exporter.export_colors(self.colors, output)

            self.assertFalse(output.exists())
            self.assertEqual(exporter.calls, [])

    def test_missing_dependencies_and_availability_use_import_names(self) -> None:
        dependencies = (
            ExporterDependency("Present", "present_module"),
            ExporterDependency("Missing", "missing_module"),
        )
        exporter = _ContractExporter(dependencies=dependencies)

        def _find_spec(name: str) -> ModuleSpec | None:
            if name == "present_module":
                return ModuleSpec(name, loader=None)
            return None

        with patch(
            "color_tools.exporters.base.find_spec",
            side_effect=_find_spec,
        ) as find:
            self.assertEqual(exporter.missing_dependencies, (dependencies[1],))
            self.assertFalse(exporter.is_available)

        self.assertEqual(
            [call.args[0] for call in find.call_args_list],
            ["present_module", "missing_module", "present_module", "missing_module"],
        )

    def test_generated_filename_has_all_contract_components(self) -> None:
        filename = _ContractExporter().generate_filename("colors")
        self.assertRegex(
            filename,
            re.compile(r"^colors_contract_\d{8}_\d{6}\.test$"),
        )


if __name__ == "__main__":
    unittest.main()
