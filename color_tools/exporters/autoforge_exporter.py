"""
AutoForge filament library CSV exporter.

AutoForge is a companion tool for HueForge (3D printing lithophane software).
It manages filament libraries with transmission distance (TD) values for
multi-layer transparency planning.

This exporter converts color_tools filament data to AutoForge's CSV import format.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class AutoForgeExporter(PaletteExporter):
    """
    AutoForge filament library CSV exporter.
    
    Exports filaments in the format expected by AutoForge:
        Brand,Name,TD,Color,Owned
        Bambu Lab PLA Basic,Jet Black,0.1,#000000,TRUE
    
    The Brand column combines maker + type + finish.
    All exported filaments are marked as Owned=TRUE.
    
    AutoForge is used with HueForge for lithophane printing workflows.
    TD (Transmission Distance) values indicate light transmission through
    each filament for multi-layer transparency effects.
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('autoforge')
        >>> from color_tools.palette import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> bambu = [f for f in palette.filaments if f.maker == 'Bambu Lab']
        >>> path = exporter.export_filaments(bambu)
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='autoforge',
            description='AutoForge filament library CSV format',
            file_extension='csv',
            supports_colors=False,
            supports_filaments=True,
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - AutoForge is filaments-only."""
        # This won't be called due to supports_colors=False
        # But we need to implement the abstract method
        raise NotImplementedError("AutoForge exporter does not support colors")
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Export filaments to AutoForge CSV format."""
        if output_path is None:
            output_path = self.generate_filename('filaments')
        
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
