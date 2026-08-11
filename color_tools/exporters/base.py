"""
Base classes, metadata, and dependency handling for palette exporters.

This module defines the common exporter interface used by all palette export
formats. Exporters declare their capabilities and optional dependencies through
ExporterMetadata, while PaletteExporter provides consistent validation,
dependency checking, filename generation, palette-aware export support, and
optional per-export configuration.

Design:
    - PaletteExporter:
        Base class defining the exporter interface.

    - ExporterMetadata:
        Describes format capabilities and output characteristics.

    - ExporterDependency:
        Describes an optional third-party dependency.

    - MissingExporterDependencyError:
        Raised when an optional dependency is required but unavailable.

    - PaletteExportData:
        Supplies exporters with both ordered palette colors and optional
        palette-level metadata.

    - ExportOptionsBase:
        Base class for strongly typed exporter-specific configuration.

Exporters only need to override the operations they actually support.

For example, a colors-only exporter implements _export_colors_impl() but does
not need to provide a placeholder _export_filaments_impl().

Palette-aware exporters may additionally override _export_palette_impl() when
their format can preserve metadata such as palette name, author, description,
or preferred column count. Exporters that do not override it automatically
fall back to normal color export.

Configurable exporters remain stateless. They declare an options type in their
metadata and override the appropriate options-aware implementation method.

Existing exporters that do not accept options do not need to change.

Example:
    >>> from color_tools.exporters.base import (
    ...     ExporterMetadata,
    ...     PaletteExporter,
    ... )
    >>>
    >>> class MyExporter(PaletteExporter):
    ...     @property
    ...     def metadata(self) -> ExporterMetadata:
    ...         return ExporterMetadata(
    ...             name="myformat",
    ...             description="My custom palette format",
    ...             file_extension="txt",
    ...             supports_colors=True,
    ...             supports_filaments=False,
    ...         )
    ...
    ...     def _export_colors_impl(self, colors, output_path):
    ...         # Implementation here.
    ...         return str(output_path)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.export_options_base import ExportOptionsBase

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.filament_palette import FilamentRecord
    from color_tools.palette import ColorRecord


@dataclass(frozen=True, slots=True)
class ExporterDependency:
    """
    Optional third-party dependency required by an exporter.

    Attributes:
        package:
            Distribution/package name used when installing the dependency,
            such as ``"swatch"`` or ``"Pillow"``.

        import_name:
            Python module name used to test whether the dependency is
            installed, such as ``"swatch"`` or ``"PIL"``.

        extra:
            Optional color-tools dependency extra that installs the package,
            such as ``"image"``.

    Example:
        >>> dependency = ExporterDependency(
        ...     package="swatch",
        ...     import_name="swatch",
        ...     extra="image",
        ... )
    """

    package: str
    import_name: str
    extra: str | None = None


@dataclass(frozen=True, slots=True)
class ExporterMetadata:
    """
    Metadata describing an exporter's capabilities.

    Attributes:
        name:
            Machine-readable format identifier, such as ``"gpl"``,
            ``"jasc_pal"``, or ``"ase"``.

        description:
            Human-readable format description.

        file_extension:
            Default file extension without the leading dot.

        supports_colors:
            Whether this exporter supports ColorRecord palettes.

        supports_filaments:
            Whether this exporter supports FilamentRecord palettes.

        supports_palette_metadata:
            Whether this exporter preserves palette-level metadata when
            export_palette() is used.

            This flag is informational. All color exporters may be called
            through export_palette(); exporters that do not preserve metadata
            simply fall back to normal color export.

        is_binary:
            Whether the output format is binary rather than text.

        is_image:
            Whether the output format is an image.

        dependencies:
            Optional third-party packages required by the exporter.

        options_type:
            Exporter-specific ExportOptionsBase subclass accepted by this
            exporter. None means the exporter does not accept per-export
            configuration.

    Example:
        >>> metadata = ExporterMetadata(
        ...     name="ase",
        ...     description="Adobe Swatch Exchange",
        ...     file_extension="ase",
        ...     supports_colors=True,
        ...     supports_filaments=False,
        ...     supports_palette_metadata=True,
        ...     is_binary=True,
        ...     dependencies=(
        ...         ExporterDependency(
        ...             package="swatch",
        ...             import_name="swatch",
        ...             extra="image",
        ...         ),
        ...     ),
        ... )
    """

    name: str
    description: str
    file_extension: str
    supports_colors: bool
    supports_filaments: bool
    supports_palette_metadata: bool = False
    is_binary: bool = False
    is_image: bool = False
    dependencies: tuple[ExporterDependency, ...] = ()
    options_type: type[ExportOptionsBase] | None = None

    def __post_init__(self) -> None:
        """Validate exporter metadata."""
        if not self.name:
            raise ValueError(
                "Exporter name must not be empty"
            )

        if not self.description:
            raise ValueError(
                "Exporter description must not be empty"
            )

        if not self.file_extension:
            raise ValueError(
                "Exporter file_extension must not be empty"
            )

        if self.file_extension.startswith("."):
            raise ValueError(
                "Exporter file_extension must not include the leading dot"
            )

        if (
            self.options_type is not None
            and not issubclass(
                self.options_type,
                ExportOptionsBase,
            )
        ):
            raise TypeError(
                "Exporter options_type must inherit from ExportOptionsBase"
            )


class MissingExporterDependencyError(RuntimeError):
    """
    Raised when an exporter requires an unavailable optional dependency.

    Attributes:
        exporter_name:
            Machine-readable name of the exporter that could not run.

        dependencies:
            Missing dependencies required by the exporter.
    """

    def __init__(
        self,
        exporter_name: str,
        dependencies: tuple[ExporterDependency, ...],
    ) -> None:
        self.exporter_name = exporter_name
        self.dependencies = dependencies

        package_names = ", ".join(
            dependency.package
            for dependency in dependencies
        )

        extras = {
            dependency.extra
            for dependency in dependencies
            if dependency.extra
        }

        dependency_word = (
            "dependency"
            if len(dependencies) == 1
            else "dependencies"
        )

        message = (
            f"{exporter_name} exporter requires missing optional "
            f"{dependency_word}: {package_names}."
        )

        if len(extras) == 1:
            extra = next(iter(extras))

            message += (
                f" Install the '{extra}' optional extra to enable "
                "this exporter."
            )

        elif len(extras) > 1:
            extra_names = ", ".join(
                sorted(extras)
            )

            message += (
                " Install the required optional extras to enable this "
                f"exporter: {extra_names}."
            )

        super().__init__(message)


class PaletteExporter(ABC):
    """
    Base class for all palette exporters.

    Concrete exporters must provide the ``metadata`` property and implement
    only the export operations they support.

    The base class handles:

        - Capability checking.
        - Optional dependency discovery and validation.
        - Per-export option validation.
        - Consistent unsupported-operation errors.
        - Palette-aware export fallback.
        - Timestamped filename generation.

    A colors-only exporter with ``supports_colors=True`` should override
    ``_export_colors_impl()``.

    A filament exporter with ``supports_filaments=True`` should override
    ``_export_filaments_impl()``.

    A palette-aware exporter with ``supports_palette_metadata=True`` may
    override ``_export_palette_impl()`` to preserve palette-level metadata.

    A configurable exporter declares ``metadata.options_type`` and overrides
    the appropriate options-aware implementation method.

    Unsupported implementation methods do not need to be overridden.
    """

    @property
    @abstractmethod
    def metadata(self) -> ExporterMetadata:
        """
        Return metadata describing this exporter.

        Returns:
            Exporter metadata including its identifier, file extension,
            capabilities, output characteristics, optional dependencies, and
            supported options type.
        """
        raise NotImplementedError

    @property
    def missing_dependencies(
        self,
    ) -> tuple[ExporterDependency, ...]:
        """
        Return optional dependencies that are not currently installed.

        Dependency availability is checked using each dependency's Python
        import name rather than its distribution/package name.

        Returns:
            Tuple containing every unavailable dependency. The tuple is empty
            when all required dependencies are installed.
        """
        return tuple(
            dependency
            for dependency in self.metadata.dependencies
            if find_spec(dependency.import_name) is None
        )

    @property
    def is_available(self) -> bool:
        """
        Return whether all dependencies required by this exporter are available.

        Exporters without optional dependencies are always available.

        Returns:
            True if the exporter can be used in the current environment.
        """
        return not self.missing_dependencies

    def export_colors(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None = None,
        options: ExportOptionsBase | None = None,
    ) -> str:
        """
        Export colors to a file.

        Args:
            colors:
                Color records to export.

            output_path:
                Output path. The concrete exporter may generate a path when
                this is None.

            options:
                Optional exporter-specific configuration.

        Returns:
            Path to the exported file as a string.

        Raises:
            NotImplementedError:
                If the exporter does not support color export.

            MissingExporterDependencyError:
                If an optional dependency required by the exporter is not
                installed.

            TypeError:
                If unsupported or incorrect options are supplied.
        """
        if not self.metadata.supports_colors:
            raise NotImplementedError(
                f"{self.metadata.name} exporter does not support "
                "color export"
            )

        self._ensure_dependencies()
        self._validate_options(options)

        if options is not None:
            return self._export_colors_with_options_impl(
                colors,
                output_path,
                options,
            )

        return self._export_colors_impl(
            colors,
            output_path,
        )

    def export_palette(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None = None,
        options: ExportOptionsBase | None = None,
    ) -> str:
        """
        Export colors together with optional palette-level metadata.

        Exporters that do not override ``_export_palette_impl()`` automatically
        fall back to normal color export and ignore the metadata.

        Args:
            palette:
                Palette colors and palette-level metadata.

            output_path:
                Output path. The concrete exporter may generate a path when
                this is None.

            options:
                Optional exporter-specific configuration.

        Returns:
            Path to the exported file as a string.

        Raises:
            NotImplementedError:
                If the exporter does not support color export.

            MissingExporterDependencyError:
                If an optional dependency required by the exporter is not
                installed.

            TypeError:
                If unsupported or incorrect options are supplied.
        """
        if not self.metadata.supports_colors:
            raise NotImplementedError(
                f"{self.metadata.name} exporter does not support "
                "color export"
            )

        self._ensure_dependencies()
        self._validate_options(options)

        if options is not None:
            return self._export_palette_with_options_impl(
                palette,
                output_path,
                options,
            )

        return self._export_palette_impl(
            palette,
            output_path,
        )

    def export_filaments(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None = None,
        options: ExportOptionsBase | None = None,
    ) -> str:
        """
        Export filaments to a file.

        Args:
            filaments:
                Filament records to export.

            output_path:
                Output path. The concrete exporter may generate a path when
                this is None.

            options:
                Optional exporter-specific configuration.

        Returns:
            Path to the exported file as a string.

        Raises:
            NotImplementedError:
                If the exporter does not support filament export.

            MissingExporterDependencyError:
                If an optional dependency required by the exporter is not
                installed.

            TypeError:
                If unsupported or incorrect options are supplied.
        """
        if not self.metadata.supports_filaments:
            raise NotImplementedError(
                f"{self.metadata.name} exporter does not support "
                "filament export"
            )

        self._ensure_dependencies()
        self._validate_options(options)

        if options is not None:
            return self._export_filaments_with_options_impl(
                filaments,
                output_path,
                options,
            )

        return self._export_filaments_impl(
            filaments,
            output_path,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Implement color export.

        Concrete exporters only need to override this method when
        ``metadata.supports_colors`` is True.
        """
        raise NotImplementedError(
            f"{self.metadata.name} exporter declares color support "
            "but does not implement _export_colors_impl()"
        )

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """
        Implement configurable color export.

        Configurable color exporters override this method.
        """
        raise NotImplementedError(
            f"{self.metadata.name} exporter accepts export options "
            "but does not implement _export_colors_with_options_impl()"
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """
        Implement palette-aware export.

        The default implementation intentionally ignores palette-level metadata
        and delegates to the normal color exporter.
        """
        return self._export_colors_impl(
            palette.colors,
            output_path,
        )

    def _export_palette_with_options_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """
        Implement configurable palette-aware export.

        The default implementation ignores palette-level metadata and delegates
        to configurable color export. This allows an options-aware exporter to
        support export_palette() without implementing a separate metadata-aware
        path when its format does not preserve palette metadata.
        """
        return self._export_colors_with_options_impl(
            palette.colors,
            output_path,
            options,
        )

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Implement filament export.

        Concrete exporters only need to override this method when
        ``metadata.supports_filaments`` is True.
        """
        raise NotImplementedError(
            f"{self.metadata.name} exporter declares filament support "
            "but does not implement _export_filaments_impl()"
        )

    def _export_filaments_with_options_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """
        Implement configurable filament export.

        Configurable filament exporters override this method.
        """
        raise NotImplementedError(
            f"{self.metadata.name} exporter accepts export options "
            "but does not implement _export_filaments_with_options_impl()"
        )

    def _validate_options(
        self,
        options: ExportOptionsBase | None,
    ) -> None:
        """
        Validate exporter-specific options.

        Args:
            options:
                Options supplied for the current export.

        Raises:
            TypeError:
                If the exporter does not accept options or the supplied
                options have the wrong type.
        """
        if options is None:
            return

        expected_type = self.metadata.options_type

        if expected_type is None:
            raise TypeError(
                f"{self.metadata.name} exporter does not accept "
                "export options"
            )

        if not isinstance(options, expected_type):
            raise TypeError(
                f"{self.metadata.name} exporter requires "
                f"{expected_type.__name__}, got "
                f"{type(options).__name__}"
            )

    def _ensure_dependencies(self) -> None:
        """
        Ensure that every optional dependency required by the exporter exists.

        Raises:
            MissingExporterDependencyError:
                If one or more dependencies are unavailable.
        """
        missing = self.missing_dependencies

        if missing:
            raise MissingExporterDependencyError(
                exporter_name=self.metadata.name,
                dependencies=missing,
            )

    def generate_filename(
        self,
        data_type: str,
    ) -> str:
        """
        Generate a timestamped filename for an export.

        Format:
            ``{data_type}_{format_name}_{YYYYMMDD}_{HHMMSS}.{extension}``

        Args:
            data_type:
                Logical type being exported, normally ``"colors"`` or
                ``"filaments"``.

        Returns:
            Generated filename without a directory component.

        Example:
            >>> exporter.generate_filename("colors")
            'colors_json_20260811_081500.json'
        """
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        metadata = self.metadata

        return (
            f"{data_type}_{metadata.name}_{timestamp}."
            f"{metadata.file_extension}"
        )