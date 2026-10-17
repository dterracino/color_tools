"""
Palette exporter package.

This package exposes the public palette-exporter API and imports concrete
exporter modules so they can register themselves with the exporter registry.

Architecture:
    1. Exporters subclass PaletteExporter.
    2. Exporters register themselves with @register_exporter.
    3. registry.py owns exporter discovery and lookup.
    4. This module exposes the public package API.
"""

from __future__ import annotations

from color_tools.exporters.base import (
    ExporterDependency,
    ExporterMetadata,
    MissingExporterDependencyError,
    PaletteExporter,
)
from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.exporters.filament_metadata import FilamentMetadata
from color_tools.exporters.registry import (
    get_export_formats_dict,
    get_exporter,
    list_export_formats,
    register_exporter,
)


# ---------------------------------------------------------------------------
# Concrete exporters
#
# Importing exporter modules triggers @register_exporter.
#
# Exporters with optional dependencies must not import those dependencies at
# module scope. Dependencies should be imported lazily inside the export
# implementation so this package remains importable without optional extras.
# ---------------------------------------------------------------------------

from color_tools.exporters.autoforge_exporter import AutoForgeExporter
from color_tools.exporters.csv_exporter import CSVExporter
from color_tools.exporters.gpl_exporter import GPLExporter
from color_tools.exporters.hex_exporter import HexExporter, HexExportOptions
from color_tools.exporters.hueforge_exporter import (
    HueForgeExporter,
    HueForgeExportOptions,
)
from color_tools.exporters.jascpal_exporter import JascPalExporter
from color_tools.exporters.json_exporter import JSONExporter
from color_tools.exporters.lospec_exporter import LospecExporter
from color_tools.exporters.paintnet_exporter import (
    PaintNetExporter,
    PaintNetExportOptions,
)
from color_tools.exporters.palette_lut_exporter import PaletteLutExporter
from color_tools.exporters.ase_exporter import ASEExporter
from color_tools.exporters.aseprite_exporter import AsepriteExporter, AsepriteExportOptions
from color_tools.exporters.riffpal_exporter import RiffPalExporter
from color_tools.exporters.css_exporter import CSSExporter
from color_tools.exporters.sketchpalette_exporter import SketchPaletteExporter
from color_tools.exporters.soc_exporter import SOCExporter
from color_tools.exporters.scribus_exporter import ScribusExporter
from color_tools.exporters.kpl_exporter import KPLExporter
from color_tools.exporters.swatch_image_exporter import SwatchImageExporter
from color_tools.exporters.python_exporter import (
    PythonExporter,
    PythonExportOptions,
)
from color_tools.exporters.glsl_exporter import (
    GLSLExporter,
    GLSLExportOptions,
)
from color_tools.exporters.user_colors_exporter import UserColorsExporter
from color_tools.exporters.user_color_export_models import (
    UserColorConflictPolicy,
    UserColorExportAction,
    UserColorExportChange,
    UserColorExportPlan,
    UserColorExportResult,
)
from color_tools.exporters.user_filaments_exporter import UserFilamentsExporter
from color_tools.exporters.user_filament_export_models import (
    UserFilamentConflictPolicy,
    UserFilamentExportAction,
    UserFilamentExportChange,
    UserFilamentExportPlan,
    UserFilamentExportResult,
)
from color_tools.exporters.owned_filaments_exporter import OwnedFilamentsExporter
from color_tools.exporters.owned_filament_export_models import (
    OwnedFilamentExportAction,
    OwnedFilamentExportChange,
    OwnedFilamentExportPlan,
    OwnedFilamentExportResult,
)


# Legacy EXPORT_FORMATS compatibility.
#
# This is generated after all concrete exporter modules have been imported and
# registered.
EXPORT_FORMATS = get_export_formats_dict()


__all__ = [
    "AutoForgeExporter",
    "ASEExporter",
    "AsepriteExporter",
    "AsepriteExportOptions",
    "CSVExporter",
    "ExporterDependency",
    "ExporterMetadata",
    "FilamentExportData",
    "FilamentMetadata",
    "GPLExporter",
    "GLSLExporter",
    "GLSLExportOptions",
    "HexExporter",
    "HexExportOptions",
    "HueForgeExporter",
    "HueForgeExportOptions",
    "JascPalExporter",
    "JSONExporter",
    "LospecExporter",
    "MissingExporterDependencyError",
    "PaintNetExporter",
    "PaintNetExportOptions",
    "PaletteExporter",
    "PaletteLutExporter",
    "RiffPalExporter",
    "CSSExporter",
    "SketchPaletteExporter",
    "SOCExporter",
    "ScribusExporter",
    "KPLExporter",
    "SwatchImageExporter",
    "PythonExporter",
    "PythonExportOptions",
    "EXPORT_FORMATS",
    "get_exporter",
    "list_export_formats",
    "register_exporter",
    "UserColorsExporter",
    "UserColorConflictPolicy",
    "UserColorExportAction",
    "UserColorExportChange",
    "UserColorExportPlan",
    "UserColorExportResult",
    "UserFilamentsExporter",
    "UserFilamentConflictPolicy",
    "UserFilamentExportAction",
    "UserFilamentExportChange",
    "UserFilamentExportPlan",
    "UserFilamentExportResult",
    "OwnedFilamentsExporter",
    "OwnedFilamentExportAction",
    "OwnedFilamentExportChange",
    "OwnedFilamentExportPlan",
    "OwnedFilamentExportResult",
]
