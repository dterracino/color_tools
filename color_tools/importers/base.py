"""
Base classes, metadata, dependency handling, and shared color construction for
palette importers.

Palette importers convert external palette formats into the library's existing
internal palette representation:

    PaletteExportData
        ├── colors: list[ColorRecord]
        └── metadata: PaletteMetadata

Importers do not introduce a separate imported-palette model. This allows an
imported palette to be passed directly to any palette exporter.

Color-space conversion is delegated to color_tools.conversions so importers use
the same conversion logic as the rest of the library.

Example:
    >>> importer = SomePaletteImporter()
    >>> palette = importer.import_palette("palette.gpl")
    >>> print(palette.metadata.name)
    My Palette
    >>> print(palette.colors[0].rgb)
    (255, 127, 80)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from color_tools.conversions import (
    lab_to_lch,
    rgb_to_hsl,
    rgb_to_lab,
)
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.palette import ColorRecord


@dataclass(frozen=True, slots=True)
class ImporterDependency:
    """
    Optional third-party dependency required by an importer.

    Attributes:
        package:
            Distribution/package name used when installing the dependency.

        import_name:
            Python module name used to test whether the dependency is
            installed.

        extra:
            Optional color-tools dependency extra that installs the package.
    """

    package: str
    import_name: str
    extra: str | None = None


@dataclass(frozen=True, slots=True)
class ImporterMetadata:
    """
    Metadata describing a palette importer's capabilities.

    Attributes:
        name:
            Machine-readable importer identifier such as ``"gpl"`` or
            ``"jasc_pal"``.

        description:
            Human-readable description of the palette format.

        file_extensions:
            File extensions recognized by the importer, without leading dots.

            Importers use a tuple because a single format may legitimately be
            associated with more than one extension.

        is_binary:
            Whether the input format is binary.

        dependencies:
            Optional third-party dependencies required by the importer.
    """

    name: str
    description: str
    file_extensions: tuple[str, ...]
    is_binary: bool = False
    dependencies: tuple[ImporterDependency, ...] = ()

    def __post_init__(self) -> None:
        """Validate importer metadata."""
        if not self.name:
            raise ValueError(
                "Importer name must not be empty"
            )

        if not self.description:
            raise ValueError(
                "Importer description must not be empty"
            )

        if not self.file_extensions:
            raise ValueError(
                "Importer file_extensions must not be empty"
            )

        for extension in self.file_extensions:
            if not extension:
                raise ValueError(
                    "Importer file extensions must not be empty"
                )

            if extension.startswith("."):
                raise ValueError(
                    "Importer file extensions must not include "
                    "the leading dot"
                )


class MissingImporterDependencyError(RuntimeError):
    """
    Raised when an importer requires an unavailable optional dependency.

    Attributes:
        importer_name:
            Machine-readable importer name.

        dependencies:
            Missing dependencies required by the importer.
    """

    def __init__(
        self,
        importer_name: str,
        dependencies: tuple[ImporterDependency, ...],
    ) -> None:
        self.importer_name = importer_name
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
            f"{importer_name} importer requires missing optional "
            f"{dependency_word}: {package_names}."
        )

        if len(extras) == 1:
            extra = next(iter(extras))

            message += (
                f" Install the '{extra}' optional extra to enable "
                "this importer."
            )

        elif len(extras) > 1:
            extra_names = ", ".join(
                sorted(extras)
            )

            message += (
                " Install the required optional extras to enable "
                f"this importer: {extra_names}."
            )

        super().__init__(message)


class PaletteImporter(ABC):
    """
    Base class for all palette importers.

    Concrete importers provide format metadata and implement
    ``_import_palette_impl()``.

    The base class handles:

        - Input-path validation.
        - Optional dependency checking.
        - Extension matching.
        - Format-detection dispatch.
        - Shared ColorRecord construction.

    Color-space conversions are performed through color_tools.conversions so
    imported colors use the same calculations as colors created elsewhere in
    the library.

    A format with an ambiguous extension should override
    ``_can_import_impl()`` to inspect the file signature or contents.

    For example, both JASC PAL and RIFF PAL use ``.pal``, so those importers
    should distinguish themselves by examining their respective headers.
    """

    @property
    @abstractmethod
    def metadata(self) -> ImporterMetadata:
        """
        Return metadata describing this importer.

        Returns:
            Importer metadata.
        """
        raise NotImplementedError

    @property
    def missing_dependencies(
        self,
    ) -> tuple[ImporterDependency, ...]:
        """
        Return optional dependencies that are not currently installed.

        Returns:
            Tuple containing unavailable dependencies.
        """
        return tuple(
            dependency
            for dependency in self.metadata.dependencies
            if find_spec(dependency.import_name) is None
        )

    @property
    def is_available(self) -> bool:
        """
        Return whether the importer can run in the current environment.

        Returns:
            True if all required dependencies are installed.
        """
        return not self.missing_dependencies

    def import_palette(
        self,
        input_path: Path | str,
    ) -> PaletteExportData:
        """
        Import a palette file.

        Args:
            input_path:
                Palette file to read.

        Returns:
            PaletteExportData containing imported colors and metadata.

        Raises:
            FileNotFoundError:
                If the supplied file does not exist.

            IsADirectoryError:
                If input_path refers to a directory.

            MissingImporterDependencyError:
                If a required optional dependency is unavailable.
        """
        path = Path(
            input_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Palette file does not exist: {path}"
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"Palette input path is not a file: {path}"
            )

        self._ensure_dependencies()

        return self._import_palette_impl(
            path
        )

    def can_import(
        self,
        input_path: Path | str,
    ) -> bool:
        """
        Return whether this importer recognizes a palette file.

        Extension matching is performed first. The concrete importer may then
        inspect the file to distinguish formats that share an extension.

        Args:
            input_path:
                Candidate palette file.

        Returns:
            True if this importer recognizes the file.
        """
        path = Path(
            input_path
        )

        extension = (
            path.suffix
            .removeprefix(".")
            .lower()
        )

        supported_extensions = {
            item.lower()
            for item in self.metadata.file_extensions
        }

        if extension not in supported_extensions:
            return False

        if not path.is_file():
            return False

        if not self.is_available:
            return False

        return self._can_import_impl(
            path
        )

    def _can_import_impl(
        self,
        input_path: Path,
    ) -> bool:
        """
        Perform format-specific detection.

        The default implementation accepts any file whose extension matches
        ImporterMetadata.file_extensions.

        Formats that share an extension should override this method.

        Args:
            input_path:
                Candidate palette file.

        Returns:
            True if the file appears to use this format.
        """
        return True

    @abstractmethod
    def _import_palette_impl(
        self,
        input_path: Path,
    ) -> PaletteExportData:
        """
        Implement format-specific palette parsing.

        Args:
            input_path:
                Validated palette file.

        Returns:
            Imported palette.
        """
        raise NotImplementedError

    def _ensure_dependencies(self) -> None:
        """
        Ensure that every required optional dependency is installed.

        Raises:
            MissingImporterDependencyError:
                If one or more dependencies are unavailable.
        """
        missing = self.missing_dependencies

        if missing:
            raise MissingImporterDependencyError(
                importer_name=self.metadata.name,
                dependencies=missing,
            )

    @classmethod
    def _make_color_record(
        cls,
        *,
        rgb: tuple[int, int, int],
        name: str = "",
        source: str = "imported",
    ) -> ColorRecord:
        """
        Construct a complete ColorRecord from an RGB value.

        ColorRecord stores its supported color-space values directly, so this
        helper uses color_tools.conversions to calculate HSL, Lab, and LCh from
        imported RGB data.

        Args:
            rgb:
                RGB tuple with integer values from 0 through 255.

            name:
                Optional color name.

            source:
                Source identifier stored in ColorRecord.

        Returns:
            Fully populated immutable ColorRecord.

        Raises:
            ValueError:
                If the RGB value is invalid.
        """
        cls._validate_rgb(
            rgb
        )

        r, g, b = rgb

        hex_value = (
            f"#{r:02X}{g:02X}{b:02X}"
        )

        hsl = rgb_to_hsl(
            rgb
        )

        lab = rgb_to_lab(
            rgb
        )

        lch = lab_to_lch(
            lab
        )

        return ColorRecord(
            name=name.strip(),
            hex=hex_value,
            rgb=rgb,
            hsl=hsl,
            lab=lab,
            lch=lch,
            source=source,
        )

    @staticmethod
    def _validate_rgb(
        rgb: tuple[int, int, int],
    ) -> None:
        """
        Validate an RGB tuple.

        Args:
            rgb:
                RGB value to validate.

        Raises:
            ValueError:
                If the tuple does not contain exactly three integer channels
                between 0 and 255.
        """
        if len(rgb) != 3:
            raise ValueError(
                "RGB colors must contain exactly three channels"
            )

        if any(
            not isinstance(channel, int)
            for channel in rgb
        ):
            raise ValueError(
                "RGB channels must be integers"
            )

        if any(
            channel < 0 or channel > 255
            for channel in rgb
        ):
            raise ValueError(
                f"RGB channels must be between 0 and 255: {rgb}"
            )