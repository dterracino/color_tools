"""
JSON format exporter for colors and filaments.

Provides a JSON exporter that outputs raw dataclass data in JSON format.
Useful for backups, data exchange, and restore operations.

The exporter is automatically registered and available via the exporter registry.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@register_exporter
class JSONExporter(PaletteExporter):
    """
    JSON format exporter for colors and filaments.
    
    Exports data in JSON format with proper indentation and UTF-8 encoding.
    Output format is identical to the core data files (colors.json, filaments.json),
    making this exporter suitable for backups and data restoration.
    
    Features:
        - Pretty-printed with 2-space indentation
        - UTF-8 encoding with non-ASCII characters preserved
        - Dataclass fields exported as-is (tuples become arrays)
    
    Example:
        >>> from color_tools.exporters import get_exporter
        >>> exporter = get_exporter('json')
        >>> from color_tools.palette import Palette
        >>> palette = Palette.load_default()
        >>> path = exporter.export_colors(palette.colors, 'my_colors.json')
    """
    
    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name='json',
            description='JSON format (raw data, backup/restore)',
            file_extension='json',
            supports_colors=True,
            supports_filaments=True,
        )
    
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """Export colors to JSON format."""
        if output_path is None:
            output_path = self.generate_filename('colors')
        
        output_path = Path(output_path)
        
        # Convert dataclasses to dicts
        data = [asdict(c) for c in colors]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """Export filaments to JSON format."""
        if output_path is None:
            output_path = self.generate_filename('filaments')
        
        output_path = Path(output_path)
        
        # Convert dataclasses to dicts
        data = [asdict(f) for f in filaments]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
