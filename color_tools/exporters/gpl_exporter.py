"""
GIMP Palette (.gpl) format exporter.

Exports colors to GIMP Palette format, which is a simple text format
used by GIMP, Inkscape, Krita, and other graphics applications.

Format specification:
    GIMP Palette
    Name: palette_name
    Columns: 0
    #
    R   G   B   Color Name
    255 127 80  coral
    ...

This exporter demonstrates how to add support for third-party formats
to the color_tools export system.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class GPLExporter(PaletteExporter):
    """
    GIMP Palette (.gpl) format exporter.
    
    Exports colors to the GIMP Palette format, which is supported by:
        - GIMP (GNU Image Manipulation Program)
        - Inkscape
        - Krita
        - MyPaint
        - Other graphics applications
    
    Format features:
        - Plain text format
        - RGB color values (0-255)
        - Optional color names
        - Header with palette name
    
    Note: This exporter only supports colors (not filaments), as the GPL
    format is designed for color palettes used in graphics applications.
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('gpl')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> # Export first 10 colors as a GIMP palette
        >>> path = exporter.export_colors(palette.colors[:10], 'my_palette.gpl')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='gpl',
            description='GIMP Palette format (.gpl) for graphics applications',
            file_extension='gpl',
            supports_colors=True,
            supports_filaments=False,
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to GIMP Palette (.gpl) format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        # Generate palette name from filename
        palette_name = output_path.stem
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("GIMP Palette\n")
            f.write(f"Name: {palette_name}\n")
            f.write("Columns: 0\n")
            f.write("#\n")
            
            # Write colors
            for color in colors:
                r, g, b = color.rgb
                # Format: R G B Name (with padding for alignment)
                f.write(f"{r:3d} {g:3d} {b:3d}\t{color.name}\n")
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - GPL format is for colors only."""
        # This won't be called due to supports_filaments=False
        # But we need to implement the abstract method
        raise NotImplementedError("GIMP Palette format does not support filaments")
