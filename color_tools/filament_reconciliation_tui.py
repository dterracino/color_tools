"""Prompt-toolkit resolution UI for ambiguous filament imports."""

from __future__ import annotations

from collections.abc import Mapping

from color_tools._interactive_utils import check_prompt_toolkit, show_install_message
from color_tools.reconcilers.filament_reconciliation_models import (
    FilamentReconciliationEntry,
    FilamentReconciliationPlan,
)
from color_tools.reconcilers.resolutions import (
    FilamentResolution,
    ImportNew,
    Skip,
    UseExisting,
)


def _display_entry(entry: FilamentReconciliationEntry) -> None:
    """Print one ambiguous source record and its ranked candidates."""
    record = entry.provisional_record
    print()
    print(
        f"[{entry.source_index}] {record.maker} / {record.type} / "
        f"{record.finish or '-'} / {record.color} / {record.hex}"
    )
    for number, candidate in enumerate(entry.candidates, start=1):
        reasons = "; ".join(candidate.reasons) or candidate.kind
        print(
            f"  {number}. {candidate.filament_id} "
            f"({candidate.score:.1f}: {reasons})"
        )
    print(f"  n. Import new as {entry.proposed_filament_id}")
    print("  s. Skip")


def _ask_resolution(entry: FilamentReconciliationEntry) -> FilamentResolution | None:
    """Prompt until the user selects one resolution or cancels."""
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter

    choices = [str(index) for index in range(1, len(entry.candidates) + 1)]
    completer = WordCompleter([*choices, "n", "new", "s", "skip", "q", "quit"])
    while True:
        try:
            answer = prompt(
                "  Resolution: ",
                completer=completer,
                complete_while_typing=False,
            ).strip().casefold()
        except (EOFError, KeyboardInterrupt):
            return None
        if answer in {"q", "quit"}:
            return None
        if answer in {"n", "new"}:
            return ImportNew()
        if answer in {"s", "skip"}:
            return Skip()
        if answer.isdigit():
            candidate_index = int(answer) - 1
            if 0 <= candidate_index < len(entry.candidates):
                return UseExisting(entry.candidates[candidate_index].filament_id)
        print("  Choose a candidate number, n for new, s to skip, or q to cancel.")


def collect_filament_resolutions(
    plan: FilamentReconciliationPlan,
    initial: Mapping[int, FilamentResolution] | None = None,
) -> dict[int, FilamentResolution] | None:
    """Interactively resolve remaining ambiguities in a reconciliation plan.

    Args:
        plan: Prepared reconciliation plan to review.
        initial: Decisions already supplied through another interface.

    Returns:
        A complete decision mapping, or ``None`` if the user cancels.
    """
    if not check_prompt_toolkit():
        show_install_message()
        return None

    resolutions = dict(initial or {})
    unresolved = [
        entry
        for entry in plan.entries
        if entry.status == "ambiguous" and entry.source_index not in resolutions
    ]
    if not unresolved:
        print("No unresolved filament matches require interactive choices.")
        return resolutions

    print(f"Resolving {len(unresolved)} ambiguous filament match(es).")
    for entry in unresolved:
        _display_entry(entry)
        resolution = _ask_resolution(entry)
        if resolution is None:
            print("Reconciliation cancelled; no files were changed.")
            return None
        resolutions[entry.source_index] = resolution
    return resolutions


__all__ = ["collect_filament_resolutions"]
