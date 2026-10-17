"""Format-neutral orchestration for reconciled filament imports."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from color_tools.exporters.owned_filament_export_models import (
    OwnedFilamentExportPlan,
    OwnedFilamentExportResult,
)
from color_tools.exporters.owned_filaments_exporter import OwnedFilamentsExporter
from color_tools.exporters.user_filament_export_models import (
    UserFilamentConflictPolicy,
    UserFilamentExportPlan,
    UserFilamentExportResult,
)
from color_tools.exporters.user_filaments_exporter import UserFilamentsExporter
from color_tools.importers.filament_importer import FilamentImporter
from color_tools.reconcilers.filament_reconciler import FilamentReconciler
from color_tools.reconcilers.filament_reconciliation_models import (
    FilamentReconciliationPlan,
    FilamentReconciliationResult,
)
from color_tools.reconcilers.resolutions import FilamentResolution


class FilamentImportWorkflow:
    """Coordinate import, reconciliation, catalog, and ownership stages.

    The supplied importer and reconciler retain all format-specific behavior.
    This class standardizes the order of operations while delegating file
    writes to the existing state-aware exporters. Planning methods never write;
    every mutation requires a corresponding explicit ``apply`` call.
    """

    def __init__(
        self,
        importer: FilamentImporter,
        reconciler: FilamentReconciler,
        *,
        data_dir: Path | str | None = None,
    ) -> None:
        self._importer = importer
        self._reconciler = reconciler
        self._catalog_exporter = UserFilamentsExporter(data_dir)
        self._owned_exporter = OwnedFilamentsExporter(data_dir)

    def prepare(self, input_path: Path | str) -> FilamentReconciliationPlan:
        """Parse an external file and return its read-only reconciliation plan."""
        source = self._importer.import_filaments(input_path)
        return self._reconciler.plan(source)

    def resolve(
        self,
        plan: FilamentReconciliationPlan,
        resolutions: Mapping[int, FilamentResolution] | None = None,
    ) -> FilamentReconciliationResult:
        """Apply caller decisions to a prepared reconciliation plan in memory."""
        return self._reconciler.resolve(plan, resolutions)

    def plan_catalog(
        self,
        result: FilamentReconciliationResult,
        *,
        conflict_policy: UserFilamentConflictPolicy = "error",
    ) -> UserFilamentExportPlan:
        """Plan persistence of reconciled new records to user filaments."""
        return self._catalog_exporter.plan(
            result.data,
            conflict_policy=conflict_policy,
        )

    def apply_catalog(
        self,
        plan: UserFilamentExportPlan,
    ) -> UserFilamentExportResult:
        """Apply a reviewed user-filament catalog plan."""
        return self._catalog_exporter.apply(plan)

    def plan_ownership(
        self,
        result: FilamentReconciliationResult,
    ) -> OwnedFilamentExportPlan:
        """Plan additive ownership using reconciled final Color Tools IDs."""
        return self._owned_exporter.plan(result.data)

    def apply_ownership(
        self,
        plan: OwnedFilamentExportPlan,
    ) -> OwnedFilamentExportResult:
        """Apply a reviewed additive ownership plan."""
        return self._owned_exporter.apply(plan)


__all__ = ["FilamentImportWorkflow"]
