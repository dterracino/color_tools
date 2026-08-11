"""
Base class for exporter-specific options.

ExporterOptionsBase provides a common nominal type for configuration that
applies to a specific export operation rather than to an exporter instance.

Concrete exporters may define strongly typed dataclass subclasses containing
the options they support. Exporters themselves remain stateless and can
continue to be instantiated by the exporter registry without constructor
arguments.

Example:
    >>> from dataclasses import dataclass
    >>> from color_tools.exporters.export_options_base import ExportOptionsBase
    >>>
    >>> @dataclass(slots=True)
    ... class ExampleOptions(ExportOptionsBase):
    ...     include_names: bool = True
    ...     include_values: bool = False
"""

from __future__ import annotations

from abc import ABC


class ExportOptionsBase(ABC):
    """
    Base class for exporter-specific per-export configuration.

    Concrete exporters should define a typed subclass containing only the
    settings applicable to that exporter.

    ExporterMetadata.options_type identifies the supported options class,
    allowing PaletteExporter to validate configuration before dispatching the
    export operation.
    """