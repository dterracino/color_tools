"""
Export system for filaments and colors.

Provides export functionality to various formats (CSV, JSON, GPL, etc.) for integration
with external tools like AutoForge, HueForge, GIMP, and other color management systems.

ARCHITECTURE NOTE (v6.0.0):
This module now serves as a backward-compatibility facade over the new plugin-based
exporter system located in color_tools/exporters/. All export logic has been moved
to individual exporter classes in the exporters/ folder.

The functions in this file (export_filaments_csv, export_colors_json, etc.) are
now STUBS that delegate to the new exporter implementations. This preserves
backward compatibility while allowing new exporters to be added as plugins
without modifying this file.

New exporters can be added by:
    1. Creating a new file in exporters/ (e.g., exporters/ase_exporter.py)
    2. Subclassing PaletteExporter from exporters/base.py
    3. Using @register_exporter decorator
    4. The exporter automatically appears in list_export_formats()

For the new plugin architecture, see color_tools/exporters/
For adding new exporters, see color_tools/exporters/base.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

# Import the new exporter system
from color_tools.exporters import (
    get_exporter,
    list_export_formats as _list_export_formats,
    EXPORT_FORMATS,
)

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


def list_export_formats(data_type: str = 'both') -> dict[str, str]:
    """
    List available export formats.
    
    DELEGATION NOTE: This function delegates to the exporter registry.
    
    Args:
        data_type: Filter by 'filaments', 'colors', or 'both'
    
    Returns:
        Dictionary mapping format name to description
    
    Example:
        >>> formats = list_export_formats('filaments')
        >>> print(formats['autoforge'])
        AutoForge filament library CSV format
    """
    # Delegate to new exporter registry
    return _list_export_formats(data_type)


def generate_filename(data_type: str, format_name: str) -> str:
    """
    Generate timestamped filename for export.
    
    DELEGATION NOTE: This function delegates to the exporter's generate_filename method.
    
    Args:
        data_type: 'filaments' or 'colors'
        format_name: Export format name (e.g., 'autoforge', 'csv', 'json')
    
    Returns:
        Filename in format: {type}_{format}_{YYYYMMDD}_{HHMMSS}.{ext}
    
    Example:
        >>> generate_filename('filaments', 'autoforge')
        'filaments_autoforge_20251223_143022.csv'
    """
    # Delegate to exporter's generate_filename method
    exporter = get_exporter(format_name)
    return exporter.generate_filename(data_type)


def export_filaments_autoforge(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to AutoForge CSV format.
    
    DELEGATION NOTE: This function is a stub that delegates to AutoForgeExporter
    in exporters/csv_exporter.py. Kept for backward compatibility.
    
    Format:
        Brand,Name,TD,Color,Owned
        Bambu Lab PLA Basic,Jet Black,0.1,#000000,TRUE
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.filament_palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> bambu = [f for f in palette.filaments if f.maker == 'Bambu Lab']
        >>> path = export_filaments_autoforge(bambu)
        >>> print(f"Exported {len(bambu)} filaments to {path}")
    """
    # Delegate to AutoForgeExporter in exporters/csv_exporter.py
    exporter = get_exporter('autoforge')
    return exporter.export_filaments(filaments, output_path)


def export_filaments_csv(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to generic CSV format with all fields.
    
    DELEGATION NOTE: This function is a stub that delegates to CSVExporter
    in exporters/csv_exporter.py. Kept for backward compatibility.
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.filament_palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> path = export_filaments_csv(palette.filaments)
    """
    # Delegate to CSVExporter in exporters/csv_exporter.py
    exporter = get_exporter('csv')
    return exporter.export_filaments(filaments, output_path)


def export_filaments_json(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to JSON format.
    
    DELEGATION NOTE: This function is a stub that delegates to JSONExporter
    in exporters/json_exporter.py. Kept for backward compatibility.
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.filament_palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> path = export_filaments_json(palette.filaments, 'backup.json')
    """
    # Delegate to JSONExporter in exporters/json_exporter.py
    exporter = get_exporter('json')
    return exporter.export_filaments(filaments, output_path)


def export_colors_csv(
    colors: list[ColorRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to generic CSV format with all fields.
    
    DELEGATION NOTE: This function is a stub that delegates to CSVExporter
    in exporters/csv_exporter.py. Kept for backward compatibility.
    
    Args:
        colors: List of ColorRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = export_colors_csv(palette.colors)
    """
    # Delegate to CSVExporter in exporters/csv_exporter.py
    exporter = get_exporter('csv')
    return exporter.export_colors(colors, output_path)


def export_colors_json(
    colors: list[ColorRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to JSON format.
    
    DELEGATION NOTE: This function is a stub that delegates to JSONExporter
    in exporters/json_exporter.py. Kept for backward compatibility.
    
    Args:
        colors: List of ColorRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = export_colors_json(palette.colors, 'my_colors.json')
    """
    # Delegate to JSONExporter in exporters/json_exporter.py
    exporter = get_exporter('json')
    return exporter.export_colors(colors, output_path)


def export_filaments(
    filaments: list[FilamentRecord],
    format_name: str,
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to specified format.
    
    DELEGATION NOTE: This function delegates to the exporter registry.
    Now supports any format registered in the exporters/ folder.
    
    Args:
        filaments: List of FilamentRecord objects to export
        format_name: Export format ('autoforge', 'csv', 'json', etc.)
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Raises:
        ValueError: If format is not supported for filaments
    
    Example:
        >>> from color_tools.filament_palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> bambu = [f for f in palette.filaments if f.maker == 'Bambu Lab']
        >>> path = export_filaments(bambu, 'autoforge')
    """
    format_name = format_name.lower()
    
    # Use new exporter system
    try:
        exporter = get_exporter(format_name)
    except ValueError as e:
        raise ValueError(f"Unknown export format: {format_name}") from e
    
    # Check if this exporter supports filaments
    if not exporter.metadata.supports_filaments:
        raise ValueError(f"Format '{format_name}' does not support filaments")
    
    # Delegate to exporter
    return exporter.export_filaments(filaments, output_path)


def export_colors(
    colors: list[ColorRecord],
    format_name: str,
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to specified format.
    
    DELEGATION NOTE: This function delegates to the exporter registry.
    Now supports any format registered in the exporters/ folder.
    
    Args:
        colors: List of ColorRecord objects to export
        format_name: Export format ('csv', 'json', 'gpl', etc.)
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Raises:
        ValueError: If format is not supported for colors
    
    Example:
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> blues = [c for c in palette.colors if 'blue' in c.name.lower()]
        >>> path = export_colors(blues, 'json', 'blue_colors.json')
    """
    format_name = format_name.lower()
    
    # Use new exporter system
    try:
        exporter = get_exporter(format_name)
    except ValueError as e:
        raise ValueError(f"Unknown export format: {format_name}") from e
    
    # Check if this exporter supports colors
    if not exporter.metadata.supports_colors:
        raise ValueError(f"Format '{format_name}' does not support colors")
    
    # Delegate to exporter
    return exporter.export_colors(colors, output_path)

