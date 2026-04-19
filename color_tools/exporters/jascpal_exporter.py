"""
JASC-PAL format exporter.

Exports colors in JASC-PAL format used by Paint Shop Pro and other image editors.
Simple text format with RGB values as space-separated decimals.
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
class JascPalExporter(PaletteExporter):
    """
    JASC-PAL format exporter.
    
    Exports colors in JASC-PAL format used by Paint Shop Pro and other tools.
    
    Format structure:
        JASC-PAL
        0100
        {color_count}
        R G B
        R G B
        ...
    
    Example output:
        JASC-PAL
        0100
        8
        231 224 228
        239 202 167
        161 213 180
    
    This format is compatible with Paint Shop Pro, Aseprite, and many other
    image editing applications.
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('pal')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.records[:10], 'colors.pal')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='pal',
            description='JASC-PAL format (Paint Shop Pro)',
            file_extension='pal',
            supports_colors=True,
            supports_filaments=False,  # Loses filament metadata (maker, type, finish)
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to JASC-PAL format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write('JASC-PAL\n')
            f.write('0100\n')
            f.write(f'{len(colors)}\n')
            
            # Colors as space-separated RGB decimals
            for color in colors:
                r, g, b = color.rgb
                f.write(f'{r} {g} {b}\n')
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - JASC-PAL format loses filament metadata."""
        # This won't be called due to supports_filaments=False
        # But we need to implement the abstract method
        raise NotImplementedError("JASC-PAL format does not support filaments (loses metadata)")
