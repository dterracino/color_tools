"""CLI orchestration for reconciled external filament imports."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path
from typing import cast

from color_tools.filament_import_workflow import FilamentImportWorkflow
from color_tools.filament_palette import load_filaments, load_maker_synonyms
from color_tools.filament_reconciliation_tui import collect_filament_resolutions
from color_tools.exporters.user_filament_export_models import UserFilamentExportPlan
from color_tools.importers import get_filament_importer
from color_tools.reconcilers import (
    FilamentReconciliationEntry,
    FilamentReconciliationPlan,
    FilamentReconciliationResult,
    HueForgeFilamentReconciler,
    ImportNew,
    Skip,
    UseExisting,
)
from color_tools.reconcilers.resolutions import FilamentResolution


def _create_workflow(
    format_name: str,
    data_dir: Path | None,
) -> FilamentImportWorkflow:
    """Build the registered importer and format-specific reconciler pair."""
    if format_name != "hueforge":
        raise ValueError(f"Unsupported reconciled filament format: {format_name}")
    catalog = load_filaments(data_dir)
    synonyms = load_maker_synonyms(data_dir)
    reconciler = HueForgeFilamentReconciler(
        catalog,
        maker_synonyms=synonyms,
    )
    return FilamentImportWorkflow(
        get_filament_importer(format_name),
        reconciler,
        data_dir=data_dir,
    )


def _parse_resolution(value: str) -> tuple[int, FilamentResolution]:
    """Parse ``INDEX=use:ID``, ``INDEX=new``, or ``INDEX=skip``."""
    index_text, separator, action_text = value.partition("=")
    if not separator or not index_text.isdigit():
        raise ValueError(
            f"invalid resolution {value!r}; expected INDEX=use:ID, INDEX=new, "
            "or INDEX=skip"
        )
    source_index = int(index_text)
    normalized = action_text.strip()
    if normalized == "new":
        return source_index, ImportNew()
    if normalized == "skip":
        return source_index, Skip()
    prefix, action_separator, filament_id = normalized.partition(":")
    if prefix == "use" and action_separator and filament_id:
        return source_index, UseExisting(filament_id)
    raise ValueError(
        f"invalid resolution {value!r}; expected INDEX=use:ID, INDEX=new, "
        "or INDEX=skip"
    )


def _parse_resolutions(values: list[str] | None) -> dict[int, FilamentResolution]:
    """Parse and reject duplicate source-index decisions."""
    resolutions: dict[int, FilamentResolution] = {}
    for value in values or []:
        source_index, resolution = _parse_resolution(value)
        if source_index in resolutions:
            raise ValueError(
                f"multiple resolutions supplied for source index {source_index}"
            )
        resolutions[source_index] = resolution
    return resolutions


def _entry_label(entry: FilamentReconciliationEntry) -> str:
    """Return a compact source-record label for console reporting."""
    record = entry.provisional_record
    return (
        f"{record.maker} / {record.type} / {record.finish or '-'} / "
        f"{record.color} / {record.hex}"
    )


def _print_plan(plan: FilamentReconciliationPlan) -> None:
    """Print a complete, copyable reconciliation dry run."""
    print(f"Imported {len(plan.entries)} filament record(s)")
    print(
        "Reconciliation: "
        f"{plan.count('matched')} matched, "
        f"{plan.count('new')} new, "
        f"{plan.count('ambiguous')} ambiguous, "
        f"{plan.count('skipped')} skipped"
    )
    if not plan.fuzzy_matching_available:
        print("Note: install color-match-tools[fuzzy] for enhanced fuzzy matching.")

    for entry in plan.entries:
        if entry.status == "matched":
            decision = f"use:{entry.automatic_filament_id}"
        elif entry.status == "new":
            decision = f"new:{entry.proposed_filament_id}"
        else:
            decision = entry.status
        print(f"[{entry.source_index}] {decision} — {_entry_label(entry)}")
        if entry.status != "ambiguous":
            continue
        for candidate in entry.candidates:
            reasons = "; ".join(candidate.reasons) or candidate.kind
            print(
                f"    {candidate.score:5.1f}  {candidate.filament_id}  "
                f"({reasons})"
            )
            print(
                f"           --resolve "
                f"{entry.source_index}=use:{candidate.filament_id}"
            )
        print(f"           --resolve {entry.source_index}=new")
        print(f"           --resolve {entry.source_index}=skip")


def _print_result(result: FilamentReconciliationResult) -> None:
    """Print final reconciliation actions and ownership selection counts."""
    print(
        "Resolved: "
        f"{result.count('use_existing')} existing, "
        f"{result.count('import_new')} new, "
        f"{result.count('skip')} skipped"
    )
    print(
        "Owned selections after reconciliation: "
        f"{len(result.data.metadata.owned_filament_ids)}"
    )


def _unresolved_indices(
    plan: FilamentReconciliationPlan,
    resolutions: dict[int, FilamentResolution],
) -> list[int]:
    """Return ambiguous source indexes that still lack caller decisions."""
    return [
        entry.source_index
        for entry in plan.entries
        if entry.status == "ambiguous"
        and entry.source_index not in resolutions
    ]


def _print_catalog_plan(
    workflow: FilamentImportWorkflow,
    result: FilamentReconciliationResult,
) -> UserFilamentExportPlan:
    """Create and print the user-filament persistence plan."""
    plan = workflow.plan_catalog(result)
    print(
        "Catalog plan: "
        f"{plan.count('added')} added, "
        f"{plan.count('updated')} updated, "
        f"{plan.count('unchanged')} unchanged, "
        f"{plan.count('skipped')} skipped, "
        f"{plan.count('conflict')} conflicts"
    )
    for warning in plan.warnings:
        print(f"Warning: {warning}")
    return plan


def handle_filament_import_command(
    args: Namespace,
    data_dir: Path | None,
) -> None:
    """Inspect and optionally apply one reconciled filament import workflow."""
    format_name = cast(str, args.import_format)
    input_path = cast(Path, args.input_path)
    apply_catalog = cast(bool, args.apply_catalog)
    apply_owned = cast(bool, args.apply_owned)
    interactive = cast(bool, args.import_interactive)

    try:
        workflow = _create_workflow(format_name, data_dir)
        plan = workflow.prepare(input_path)
        resolutions = _parse_resolutions(cast(list[str] | None, args.resolve))
        _print_plan(plan)

        if interactive:
            collected = collect_filament_resolutions(plan, resolutions)
            if collected is None:
                if apply_catalog or apply_owned:
                    sys.exit(1)
                return
            resolutions = collected

        unresolved = _unresolved_indices(plan, resolutions)
        if unresolved:
            print(
                "Unresolved source indexes: "
                + ", ".join(str(index) for index in unresolved)
            )
            print("No files were changed.")
            if apply_catalog or apply_owned:
                sys.exit(1)
            return

        result = workflow.resolve(plan, resolutions)
        _print_result(result)
        catalog_plan = _print_catalog_plan(workflow, result)
        if not catalog_plan.can_apply:
            print("Catalog conflicts must be resolved before applying.", file=sys.stderr)
            if apply_catalog or apply_owned:
                sys.exit(1)
            return

        if apply_catalog:
            catalog_result = workflow.apply_catalog(catalog_plan)
            state = "updated" if catalog_result.data_written else "unchanged"
            print(f"Catalog applied: {state} ({catalog_plan.destination})")
        else:
            print("Catalog dry run only; use --apply-catalog to write it.")

        owned_count = len(result.data.metadata.owned_filament_ids)
        if not apply_owned:
            print(
                f"Ownership dry run: {owned_count} selected; use --apply-owned "
                "to add them."
            )
            return

        ownership_plan = workflow.plan_ownership(result)
        print(
            "Ownership plan: "
            f"{ownership_plan.count('added')} added, "
            f"{ownership_plan.count('already_owned')} already owned, "
            f"{ownership_plan.count('unknown')} unknown"
        )
        if not ownership_plan.can_apply:
            print(
                "Ownership includes IDs absent from the effective catalog; "
                "apply the catalog first.",
                file=sys.stderr,
            )
            sys.exit(1)
        ownership_result = workflow.apply_ownership(ownership_plan)
        state = "updated" if ownership_result.data_written else "unchanged"
        print(f"Ownership applied: {state} ({ownership_plan.destination})")
    except (FileNotFoundError, IsADirectoryError, TypeError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


__all__ = ["handle_filament_import_command"]
