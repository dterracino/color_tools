"""
Lospec JSON palette format exporter.

Exports colors in Lospec.com's JSON palette format for sharing palettes
on the Lospec palette list (https://lospec.com/palette-list).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class LospecExporter(PaletteExporter):
    """
    Lospec JSON palette format exporter.
    
    Exports colors in the JSON format used by Lospec.com palette list.
    Simple format with palette name, author, and hex color codes.
    
    Format structure::

        {
          "name": "Palette Name",
          "author": "Author Name",
          "colors": ["000000", "1d2b53", "7e2553", ...]
        }

    Example output::

        {
          "name": "My Palette",
          "author": "",
          "colors": ["000000", "ff0000", "00ff00"]
        }
    
    Hex codes are lowercase without # prefix.
    Perfect for sharing palettes on https://lospec.com/palette-list
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('lospec')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.records[:10], 'palette.json')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='lospec',
            description='Lospec palette JSON format',
            file_extension='json',
            supports_colors=True,
            supports_filaments=False,  # Loses filament metadata (maker, type, finish)
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to Lospec JSON format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        # Build color array (lowercase hex without #)
        color_array = [color.hex.lstrip('#').lower() for color in colors]
        
        # Create Lospec format
        palette_data = {
            'name': Path(output_path).stem,  # Use filename as palette name
            'author': '',
            'colors': color_array
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(palette_data, f, ensure_ascii=False)
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Not supported - Lospec format loses filament metadata."""
        # This won't be called due to supports_filaments=False
        # But we need to implement the abstract method
        raise NotImplementedError("Lospec format does not support filaments (loses metadata)")
