"""
PAINT.NET palette format exporter.

Exports colors in PAINT.NET's .txt palette format with AARRGGBB hex codes.
Supports optional comment headers for palette metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord
    from color_tools.filament_palette import FilamentRecord


@register_exporter
class PaintNetExporter(PaletteExporter):
    """
    PAINT.NET palette format exporter.
    
    Exports colors in PAINT.NET's palette format (.txt).
    Uses AARRGGBB hex format (alpha-first, uppercase, no # prefix).
    
    Format structure:
        ;paint.net Palette File
        ;Comments start with semicolon
        AARRGGBB
        AARRGGBB
        ...
    
    Example output:
        ;paint.net Palette File
        ;Palette Name: My Colors
        ;Colors: 16
        FF000000
        FF1D2B53
        FFFF0000
    
    All colors are exported with full opacity (FF alpha channel).
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('paintnet')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.records[:10], 'colors.txt')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='paintnet',
            description='PAINT.NET palette format (.txt)',
            file_extension='txt',
            supports_colors=True,
            supports_filaments=False,  # Loses filament metadata (maker, type, finish)
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to PAINT.NET format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Header comments
            f.write(';paint.net Palette File\n')
            f.write(f';Colors: {len(colors)}\n')
            
            # Colors in AARRGGBB format (alpha-first)
            for color in colors:
                hex_code = color.hex.lstrip('#').upper()
                # Prepend FF for full opacity
                f.write(f'FF{hex_code}\n')
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - PAINT.NET format loses filament metadata."""
        # This won't be called due to supports_filaments=False
        # But we need to implement the abstract method
        raise NotImplementedError("PAINT.NET format does not support filaments (loses metadata)")
