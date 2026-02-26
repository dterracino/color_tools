"""
Generic CSV exporter for colors and filaments.

Exports data to standard CSV format with all fields and column headers.
Automatically registered and available via the exporter registry.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class CSVExporter(PaletteExporter):
    """
    Generic CSV exporter with all fields.
    
    Exports colors or filaments to a standard CSV format with column headers.
    Colors: name, hex, rgb, hsl, lab, lch
    Filaments: id, maker, type, finish, color, hex, td_value
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('csv')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.colors)
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='csv',
            description='Generic CSV with all fields',
            file_extension='csv',
            supports_colors=True,
            supports_filaments=True,
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to generic CSV format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
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
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Export filaments to generic CSV format."""
        if output_path is None:
            output_path = self.generate_filename('filaments')
        
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
