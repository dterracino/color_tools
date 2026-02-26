"""
Base classes and metadata for palette exporters.

This module provides the abstract base class and metadata dataclass that all
palette exporters must implement. This allows for a plugin-style architecture
where new exporters can be added without modifying existing code.

Design Pattern:
    - PaletteExporter: Abstract base class defining the exporter interface
    - ExporterMetadata: Dataclass describing exporter capabilities
    - Exporters register themselves via decorator in __init__.py
    - CLI and export.py use the registry to discover available formats

Example:
    >>> from color_tools.exporters.base import PaletteExporter, ExporterMetadata
    >>> 
    >>> class MyExporter(PaletteExporter):
    ...     @property
    ...     def metadata(self) -> ExporterMetadata:
    ...         return ExporterMetadata(
    ...             name="myformat",
    ...             description="My custom format",
    ...             file_extension="txt",
    ...             supports_colors=True,
    ...             supports_filaments=False,
    ...         )
    ...     
    ...     def _export_colors_impl(self, colors, output_path):
    ...         # Implementation here
    ...         pass
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord, FilamentRecord


@dataclass(frozen=True)
class ExporterMetadata:
    """
    Metadata describing an exporter's capabilities.
    
    Attributes:
        name: Machine-readable format name (e.g., "autoforge", "csv", "gpl")
        description: Human-readable description for help text
        file_extension: File extension without dot (e.g., "csv", "json", "ase")
        supports_colors: Whether this exporter can export CSS colors
        supports_filaments: Whether this exporter can export 3D printing filaments
        is_binary: Whether output is binary (True) or text (False) - default False
        is_image: Whether output is an image file (PNG, etc.) - default False
    
    Example:
        >>> meta = ExporterMetadata(
        ...     name="json",
        ...     description="JSON format (raw data)",
        ...     file_extension="json",
        ...     supports_colors=True,
        ...     supports_filaments=True,
        ... )
        >>> print(meta.name)
        json
    """
    name: str
    description: str
    file_extension: str
    supports_colors: bool
    supports_filaments: bool
    is_binary: bool = False
    is_image: bool = False


class PaletteExporter(ABC):
    """
    Abstract base class for all palette exporters.
    
    All exporters must subclass this and implement:
    - metadata property: Return ExporterMetadata describing capabilities
    - _export_colors_impl: Logic for exporting colors (if supports_colors=True)
    - _export_filaments_impl: Logic for exporting filaments (if supports_filaments=True)
    
    The base class handles:
    - Capability checking (prevents unsupported operations)
    - Filename generation with timestamps
    - Consistent error messages
    
    Example:
        >>> from color_tools.exporters.base import PaletteExporter, ExporterMetadata
        >>> 
        >>> class TextExporter(PaletteExporter):
        ...     @property
        ...     def metadata(self) -> ExporterMetadata:
        ...         return ExporterMetadata(
        ...             name="txt",
        ...             description="Plain text format",
        ...             file_extension="txt",
        ...             supports_colors=True,
        ...             supports_filaments=False,
        ...         )
        ...     
        ...     def _export_colors_impl(self, colors, output_path):
        ...         # Write colors to text file
        ...         return str(output_path)
        ...     
        ...     def _export_filaments_impl(self, filaments, output_path):
        ...         # Not implemented (supports_filaments=False)
        ...         pass
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ExporterMetadata:
        """
        Return metadata describing this exporter's capabilities.
        
        Returns:
            ExporterMetadata instance with name, description, capabilities
        """
        pass
    
    def export_colors(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None = None
    ) -> str:
        """
        Export colors to file.
        
        Args:
            colors: List of ColorRecord objects to export
            output_path: Output file path (auto-generated if None)
        
        Returns:
            Path to exported file as string
        
        Raises:
            NotImplementedError: If this exporter doesn't support colors
        """
        if not self.metadata.supports_colors:
            raise NotImplementedError(
                f"{self.metadata.name} exporter does not support color export"
            )
        return self._export_colors_impl(colors, output_path)
    
    def export_filaments(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None = None
    ) -> str:
        """
        Export filaments to file.
        
        Args:
            filaments: List of FilamentRecord objects to export
            output_path: Output file path (auto-generated if None)
        
        Returns:
            Path to exported file as string
        
        Raises:
            NotImplementedError: If this exporter doesn't support filaments
        """
        if not self.metadata.supports_filaments:
            raise NotImplementedError(
                f"{self.metadata.name} exporter does not support filament export"
            )
        return self._export_filaments_impl(filaments, output_path)
    
    @abstractmethod
    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None
    ) -> str:
        """
        Implementation of color export logic.
        
        Override this method to implement color export.
        Only called if metadata.supports_colors is True.
        
        Args:
            colors: List of ColorRecord objects to export
            output_path: Output file path (may be None for auto-generation)
        
        Returns:
            Path to exported file as string
        """
        pass
    
    @abstractmethod
    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None
    ) -> str:
        """
        Implementation of filament export logic.
        
        Override this method to implement filament export.
        Only called if metadata.supports_filaments is True.
        
        Args:
            filaments: List of FilamentRecord objects to export
            output_path: Output file path (may be None for auto-generation)
        
        Returns:
            Path to exported file as string
        """
        pass
    
    def generate_filename(self, data_type: str) -> str:
        """
        Generate timestamped filename for export.
        
        Format: {data_type}_{format_name}_{YYYYMMDD}_{HHMMSS}.{ext}
        
        Args:
            data_type: 'colors' or 'filaments'
        
        Returns:
            Generated filename (not full path, just filename)
        
        Example:
            >>> exporter.generate_filename('colors')
            'colors_json_20251223_143022.json'
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = self.metadata.file_extension
        return f"{data_type}_{self.metadata.name}_{timestamp}.{ext}"
