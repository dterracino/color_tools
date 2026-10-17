"""Base contract and shared color construction for palette importers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from color_tools._color_utils import validate_rgb
from color_tools.conversions import lab_to_lch, rgb_to_hex, rgb_to_hsl, rgb_to_lab
from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.palette import ColorRecord


__all__ = [
    "ImporterDependency",
    "ImporterMetadata",
    "MissingImporterDependencyError",
    "PaletteImporter",
]


@dataclass(frozen=True, slots=True)
class ImporterDependency:
    """Optional third-party dependency required by an importer."""

    package: str
    import_name: str
    extra: str | None = None


@dataclass(frozen=True, slots=True)
class ImporterMetadata:
    """Metadata describing an importer's format and requirements."""

    name: str
    description: str
    file_extensions: tuple[str, ...]
    is_binary: bool = False
    dependencies: tuple[ImporterDependency, ...] = ()

    def __post_init__(self) -> None:
        """Validate importer metadata."""
        if not self.name:
            raise ValueError("Importer name must not be empty")
        if not self.description:
            raise ValueError("Importer description must not be empty")
        if not self.file_extensions:
            raise ValueError("Importer file_extensions must not be empty")

        for extension in self.file_extensions:
            if not extension:
                raise ValueError("Importer file extensions must not be empty")
            if extension.startswith("."):
                raise ValueError(
                    "Importer file extensions must not include the leading dot"
                )


class MissingImporterDependencyError(RuntimeError):
    """Raised when an importer requires unavailable optional dependencies."""

    def __init__(
        self,
        importer_name: str,
        dependencies: tuple[ImporterDependency, ...],
    ) -> None:
        self.importer_name = importer_name
        self.dependencies = dependencies
        package_names = ", ".join(item.package for item in dependencies)
        extras = {item.extra for item in dependencies if item.extra}
        dependency_word = "dependency" if len(dependencies) == 1 else "dependencies"
        message = (
            f"{importer_name} importer requires missing optional "
            f"{dependency_word}: {package_names}."
        )

        if len(extras) == 1:
            message += (
                f" Install the '{next(iter(extras))}' optional extra to enable "
                "this importer."
            )
        elif len(extras) > 1:
            message += (
                " Install the required optional extras to enable this importer: "
                f"{', '.join(sorted(extras))}."
            )

        super().__init__(message)


class ImporterBase(ABC):
    """Shared format-neutral importer infrastructure."""

    @property
    @abstractmethod
    def metadata(self) -> ImporterMetadata:
        """Return metadata describing this importer."""
        raise NotImplementedError

    @property
    def missing_dependencies(self) -> tuple[ImporterDependency, ...]:
        """Return optional dependencies unavailable in this environment."""
        return tuple(
            dependency
            for dependency in self.metadata.dependencies
            if find_spec(dependency.import_name) is None
        )

    @property
    def is_available(self) -> bool:
        """Return whether all required dependencies are installed."""
        return not self.missing_dependencies

    def can_import(self, input_path: Path | str) -> bool:
        """Return whether this importer recognizes the candidate file."""
        path = Path(input_path)
        extension = path.suffix.removeprefix(".").lower()
        supported_extensions = {
            item.lower() for item in self.metadata.file_extensions
        }
        if extension not in supported_extensions:
            return False
        if not path.is_file() or not self.is_available:
            return False
        return self._can_import_impl(path)

    def _can_import_impl(self, input_path: Path) -> bool:
        """Perform optional format-specific detection after extension checks."""
        return True

    def _validated_input_path(
        self,
        input_path: Path | str,
        *,
        data_label: str,
    ) -> Path:
        """Return a validated file path using data-specific diagnostics."""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"{data_label} file does not exist: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"{data_label} input path is not a file: {path}")
        return path

    def _ensure_dependencies(self) -> None:
        """Raise when one or more required dependencies are unavailable."""
        missing = self.missing_dependencies
        if missing:
            raise MissingImporterDependencyError(
                importer_name=self.metadata.name,
                dependencies=missing,
            )


class PaletteImporter(ImporterBase):
    """Base class for importers that produce palette transfer data.

    Concrete importers provide format metadata and implement
    :meth:`_import_palette_impl`. Shared infrastructure validates paths,
    checks optional dependencies, and performs extension/content detection.
    """

    def import_palette(self, input_path: Path | str) -> PaletteExportData:
        """Import a validated palette file.

        Args:
            input_path: Palette file to read.

        Returns:
            Imported colors and palette metadata.

        Raises:
            FileNotFoundError: If the supplied file does not exist.
            IsADirectoryError: If the supplied path is a directory.
            MissingImporterDependencyError: If a dependency is unavailable.
        """
        path = self._validated_input_path(input_path, data_label="Palette")
        self._ensure_dependencies()
        return self._import_palette_impl(path)

    @abstractmethod
    def _import_palette_impl(self, input_path: Path) -> PaletteExportData:
        """Implement format-specific palette parsing."""
        raise NotImplementedError

    @classmethod
    def _make_color_record(
        cls,
        *,
        rgb: tuple[int, int, int],
        name: str = "",
        source: str = "imported",
    ) -> ColorRecord:
        """Construct a complete color record from canonical RGB input."""
        cls._validate_rgb(rgb)
        lab = rgb_to_lab(rgb)
        return ColorRecord(
            name=name.strip(),
            hex=rgb_to_hex(rgb),
            rgb=rgb,
            hsl=rgb_to_hsl(rgb),
            lab=lab,
            lch=lab_to_lch(lab),
            source=source,
        )

    @staticmethod
    def _validate_rgb(rgb: tuple[object, ...]) -> None:
        """Validate three integer RGB channels in the inclusive 0-255 range."""
        validate_rgb(rgb)
