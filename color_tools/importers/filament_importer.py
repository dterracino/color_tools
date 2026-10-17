"""Base contract for filament collection importers."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from color_tools.exporters.filament_export_data import FilamentExportData
from color_tools.importers.base import ImporterBase


class FilamentImporter(ImporterBase):
    """Base class for importers that produce filament transfer data."""

    def import_filaments(self, input_path: Path | str) -> FilamentExportData:
        """Import a validated filament collection file.

        Args:
            input_path: Filament collection file to read.

        Returns:
            Imported filament records and collection metadata.

        Raises:
            FileNotFoundError: If the supplied file does not exist.
            IsADirectoryError: If the supplied path is a directory.
            color_tools.importers.base.MissingImporterDependencyError:
                If a dependency is unavailable.
        """
        path = self._validated_input_path(input_path, data_label="Filament")
        self._ensure_dependencies()
        return self._import_filaments_impl(path)

    @abstractmethod
    def _import_filaments_impl(self, input_path: Path) -> FilamentExportData:
        """Implement format-specific filament parsing."""
        raise NotImplementedError
