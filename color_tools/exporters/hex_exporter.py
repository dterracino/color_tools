"""
Hex format exporter.

Exports colors as uppercase hex codes without # prefix, one per line.
Simple text format compatible with many tools and color libraries.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class HexExporter(PaletteExporter):
    """
    Hex format exporter.
    
    Exports colors as uppercase hex codes without # prefix.
    One hex code per line.
    
    Example output:
        000000
        1D2B53
        7E2553
        FF0000
    
    This format is compatible with many color tools and libraries.
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('hex')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.records[:10], 'colors.hex')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='hex',
            description='Hex color codes (one per line)',
            file_extension='hex',
            supports_colors=True,
            supports_filaments=False,  # Loses filament metadata (maker, type, finish)
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to hex format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for color in colors:
                # Remove # prefix and write uppercase
                hex_code = color.hex.lstrip('#').upper()
                f.write(f'{hex_code}\n')
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - hex format loses filament metadata."""
        # This won't be called due to supports_filaments=False
        # But we need to implement the abstract method
        raise NotImplementedError("Hex format does not support filaments (loses metadata)")
