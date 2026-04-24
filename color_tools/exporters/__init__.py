"""
Palette exporter plugin system.

This module provides a plugin-based architecture for palette exporters.
Exporters automatically register themselves on import, and can be discovered
via the registry functions.

Architecture:
    1. Each exporter subclasses PaletteExporter (from base.py)
    2. Exporters use @register_exporter decorator to auto-register
    3. Registry tracks all available exporters
    4. CLI and export.py query registry to discover formats

Usage:
    >>> from color_tools.exporters import get_exporter, list_export_formats
    >>> 
    >>> # List available formats
    >>> formats = list_export_formats('filaments')
    >>> print(formats)
    {'autoforge': 'AutoForge filament library CSV format', ...}
    >>> 
    >>> # Get an exporter and use it
    >>> exporter = get_exporter('json')
    >>> from color_tools.palette import Palette
    >>> palette = Palette.load_default()
    >>> path = exporter.export_colors(palette.colors, 'output.json')
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.exporters.base import PaletteExporter


# Global registry of exporters
# Maps format name -> exporter class
_EXPORTERS: dict[str, type[PaletteExporter]] = {}


def register_exporter(cls: type[PaletteExporter]) -> type[PaletteExporter]:
    """
    Decorator to register an exporter class.
    
    Automatically instantiates the exporter and registers it in the global
    registry using its metadata.name as the key.
    
    Args:
        cls: Exporter class to register (must subclass PaletteExporter)
    
    Returns:
        The same class (unchanged), for decorator chaining
    
    Raises:
        ValueError: If an exporter with this name is already registered
    
    Example:
        >>> from color_tools.exporters import register_exporter
        >>> from color_tools.exporters.base import PaletteExporter, ExporterMetadata
        >>> 
        >>> @register_exporter
        ... class MyExporter(PaletteExporter):
        ...     @property
        ...     def metadata(self):
        ...         return ExporterMetadata(...)
        ...     # ... implementation
    """
    # Instantiate to get metadata
    instance = cls()
    name = instance.metadata.name
    
    # Check for duplicates
    if name in _EXPORTERS:
        raise ValueError(
            f"Exporter '{name}' is already registered. "
            f"Each exporter must have a unique name."
        )
    
    # Register the class (not instance - we'll instantiate on demand)
    _EXPORTERS[name] = cls
    
    return cls


def get_exporter(format_name: str) -> PaletteExporter:
    """
    Get exporter instance by format name.
    
    Args:
        format_name: Name of the export format (e.g., 'json', 'csv', 'autoforge')
    
    Returns:
        Fresh instance of the requested exporter
    
    Raises:
        ValueError: If format_name is not recognized
    
    Example:
        >>> exporter = get_exporter('json')
        >>> print(exporter.metadata.description)
        JSON format (raw data, backup/restore)
    """
    if format_name not in _EXPORTERS:
        available = ', '.join(sorted(_EXPORTERS.keys()))
        raise ValueError(
            f"Unknown export format: '{format_name}'. "
            f"Available formats: {available}"
        )
    
    # Return fresh instance
    return _EXPORTERS[format_name]()


def list_export_formats(data_type: str = 'both') -> dict[str, str]:
    """
    List available export formats.
    
    Backward-compatible function that queries the exporter registry.
    
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
    
    for name, exporter_class in _EXPORTERS.items():
        # Instantiate to check capabilities
        exporter = exporter_class()
        meta = exporter.metadata
        
        # Determine if this exporter applies
        if data_type == 'both':
            # Include if supports either colors or filaments
            applies = meta.supports_colors or meta.supports_filaments
        elif data_type == 'filaments':
            applies = meta.supports_filaments
        elif data_type == 'colors':
            applies = meta.supports_colors
        else:
            applies = False
        
        if applies:
            result[name] = meta.description
    
    return result


def get_export_formats_dict() -> dict[str, dict[str, str | bool]]:
    """
    Get EXPORT_FORMATS-compatible dictionary.
    
    This provides backward compatibility with the old EXPORT_FORMATS dict
    that existed in export.py. Returns format metadata in the legacy structure.
    
    Returns:
        Dict mapping format name to metadata dict with keys:
            - description: Human-readable description
            - file_extension: File extension (without dot)
            - applies_to: 'colors', 'filaments', or 'both'
    
    Example:
        >>> formats = get_export_formats_dict()
        >>> print(formats['json']['applies_to'])
        both
    """
    result = {}
    
    for name, exporter_class in _EXPORTERS.items():
        exporter = exporter_class()
        meta = exporter.metadata
        
        # Determine applies_to
        if meta.supports_colors and meta.supports_filaments:
            applies_to = 'both'
        elif meta.supports_colors:
            applies_to = 'colors'
        elif meta.supports_filaments:
            applies_to = 'filaments'
        else:
            applies_to = 'none'  # Should never happen
        
        result[name] = {
            'description': meta.description,
            'file_extension': meta.file_extension,
            'applies_to': applies_to,
        }
    
    return result


# Import all exporters to trigger registration
# This must be at the end so the registry functions are defined first
from color_tools.exporters.base import PaletteExporter, ExporterMetadata
from color_tools.exporters.csv_exporter import CSVExporter
from color_tools.exporters.autoforge_exporter import AutoForgeExporter
from color_tools.exporters.json_exporter import JSONExporter
from color_tools.exporters.gpl_exporter import GPLExporter
from color_tools.exporters.hex_exporter import HexExporter
from color_tools.exporters.jascpal_exporter import JascPalExporter
from color_tools.exporters.paintnet_exporter import PaintNetExporter
from color_tools.exporters.lospec_exporter import LospecExporter
from color_tools.exporters.palette_lut_exporter import PaletteLutExporter


# Create EXPORT_FORMATS for backward compatibility with old export.py
EXPORT_FORMATS = get_export_formats_dict()


# Public API
__all__ = [
    'PaletteExporter',
    'ExporterMetadata',
    'register_exporter',
    'get_exporter',
    'list_export_formats',
    'EXPORT_FORMATS',
]
