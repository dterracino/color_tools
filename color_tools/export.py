"""
Export system for filaments and colors.

Provides export functionality to various formats (CSV, JSON) for integration
with external tools like AutoForge, HueForge, and other color management systems.

Version 1.0 - Simple hardcoded formats, extensible architecture for future enhancements.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


# Export format definitions
EXPORT_FORMATS = {
    'autoforge': {
        'description': 'AutoForge filament library CSV format',
        'file_extension': 'csv',
        'applies_to': 'filaments',
    },
    'csv': {
        'description': 'Generic CSV with all fields',
        'file_extension': 'csv',
        'applies_to': 'both',
    },
    'json': {
        'description': 'JSON format (raw data, backup/restore)',
        'file_extension': 'json',
        'applies_to': 'both',
    },
}


def list_export_formats(data_type: str = 'both') -> dict[str, str]:
    """
    List available export formats.
    
    Args:
        data_type: Filter by 'filaments', 'colors', or 'both'
    
    Returns:
        Dictionary mapping format name to description
    
    Example:
        >>> formats = list_export_formats('filaments')
        >>> print(formats['autoforge'])
        AutoForge filament library CSV format
    """
    result = {}
    for name, info in EXPORT_FORMATS.items():
        applies_to = info['applies_to']
        # Include format if data_type is 'both', or if format applies to requested type
        if data_type == 'both' or applies_to == 'both' or applies_to == data_type:
            result[name] = info['description']
    return result


def generate_filename(data_type: str, format_name: str) -> str:
    """
    Generate timestamped filename for export.
    
    Args:
        data_type: 'filaments' or 'colors'
        format_name: Export format name (e.g., 'autoforge', 'csv', 'json')
    
    Returns:
        Filename in format: {type}_{format}_{YYYYMMDD}_{HHMMSS}.{ext}
    
    Example:
        >>> generate_filename('filaments', 'autoforge')
        'filaments_autoforge_20251223_143022.csv'
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = EXPORT_FORMATS[format_name]['file_extension']
    return f"{data_type}_{format_name}_{timestamp}.{ext}"


def export_filaments_autoforge(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to AutoForge CSV format.
    
    Format:
        Brand,Name,TD,Color,Owned
        Bambu Lab PLA Basic,Jet Black,0.1,#000000,TRUE
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> bambu = [f for f in palette.filaments if f.maker == 'Bambu Lab']
        >>> path = export_filaments_autoforge(bambu)
        >>> print(f"Exported {len(bambu)} filaments to {path}")
    """
    if output_path is None:
        output_path = generate_filename('filaments', 'autoforge')
    
    output_path = Path(output_path)
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Brand', 'Name', 'TD', 'Color', 'Owned'])
        
        # Write data rows
        for filament in filaments:
            # Combine maker, type, and finish for Brand column
            brand_parts = [filament.maker]
            if filament.type:
                brand_parts.append(filament.type)
            if filament.finish:
                brand_parts.append(filament.finish)
            brand = ' '.join(brand_parts)
            
            name = filament.color
            td = filament.td_value if filament.td_value is not None else ''
            color = filament.hex
            owned = 'TRUE'
            
            writer.writerow([brand, name, td, color, owned])
    
    return str(output_path)


def export_filaments_csv(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to generic CSV format with all fields.
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> path = export_filaments_csv(palette.filaments)
    """
    if output_path is None:
        output_path = generate_filename('filaments', 'csv')
    
    output_path = Path(output_path)
    
    if not filaments:
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'maker', 'type', 'finish', 'color', 'hex', 'td_value'])
        return str(output_path)
    
    # Get all field names from first filament (dataclass)
    fieldnames = list(asdict(filaments[0]).keys())
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for filament in filaments:
            writer.writerow(asdict(filament))
    
    return str(output_path)


def export_filaments_json(
    filaments: list[FilamentRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to JSON format.
    
    Args:
        filaments: List of FilamentRecord objects to export
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Example:
        >>> from color_tools.palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> path = export_filaments_json(palette.filaments, 'backup.json')
    """
    if output_path is None:
        output_path = generate_filename('filaments', 'json')
    
    output_path = Path(output_path)
    
    data = [asdict(f) for f in filaments]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(output_path)


def export_colors_csv(
    colors: list[ColorRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to generic CSV format with all fields.
    
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
    if output_path is None:
        output_path = generate_filename('colors', 'csv')
    
    output_path = Path(output_path)
    
    if not colors:
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'hex', 'rgb', 'hsl', 'lab', 'lch'])
        return str(output_path)
    
    # Colors have tuples, need custom handling
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['name', 'hex', 'rgb', 'hsl', 'lab', 'lch'])
        
        # Write data rows
        for color in colors:
            # Convert tuples to comma-separated strings
            rgb_str = ','.join(map(str, color.rgb))
            hsl_str = ','.join(f'{v:.1f}' for v in color.hsl)
            lab_str = ','.join(f'{v:.1f}' for v in color.lab)
            lch_str = ','.join(f'{v:.1f}' for v in color.lch)
            
            writer.writerow([
                color.name,
                color.hex,
                rgb_str,
                hsl_str,
                lab_str,
                lch_str
            ])
    
    return str(output_path)


def export_colors_json(
    colors: list[ColorRecord],
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to JSON format.
    
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
    if output_path is None:
        output_path = generate_filename('colors', 'json')
    
    output_path = Path(output_path)
    
    data = [asdict(c) for c in colors]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(output_path)


def export_filaments(
    filaments: list[FilamentRecord],
    format_name: str,
    output_path: Path | str | None = None
) -> str:
    """
    Export filaments to specified format.
    
    Args:
        filaments: List of FilamentRecord objects to export
        format_name: Export format ('autoforge', 'csv', 'json')
        output_path: Output file path (auto-generated if None)
    
    Returns:
        Path to the exported file
    
    Raises:
        ValueError: If format is not supported for filaments
    
    Example:
        >>> from color_tools.palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> bambu = [f for f in palette.filaments if f.maker == 'Bambu Lab']
        >>> path = export_filaments(bambu, 'autoforge')
    """
    format_name = format_name.lower()
    
    if format_name not in EXPORT_FORMATS:
        raise ValueError(f"Unknown export format: {format_name}")
    
    format_info = EXPORT_FORMATS[format_name]
    applies_to = format_info['applies_to']
    
    if applies_to != 'filaments' and applies_to != 'both':
        raise ValueError(f"Format '{format_name}' does not support filaments")
    
    if format_name == 'autoforge':
        return export_filaments_autoforge(filaments, output_path)
    elif format_name == 'csv':
        return export_filaments_csv(filaments, output_path)
    elif format_name == 'json':
        return export_filaments_json(filaments, output_path)
    else:
        raise ValueError(f"Format '{format_name}' not implemented yet")


def export_colors(
    colors: list[ColorRecord],
    format_name: str,
    output_path: Path | str | None = None
) -> str:
    """
    Export colors to specified format.
    
    Args:
        colors: List of ColorRecord objects to export
        format_name: Export format ('csv', 'json')
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
    
    if format_name not in EXPORT_FORMATS:
        raise ValueError(f"Unknown export format: {format_name}")
    
    format_info = EXPORT_FORMATS[format_name]
    applies_to = format_info['applies_to']
    
    if applies_to != 'colors' and applies_to != 'both':
        raise ValueError(f"Format '{format_name}' does not support colors")
    
    if format_name == 'csv':
        return export_colors_csv(colors, output_path)
    elif format_name == 'json':
        return export_colors_json(colors, output_path)
    else:
        raise ValueError(f"Format '{format_name}' not implemented yet")
