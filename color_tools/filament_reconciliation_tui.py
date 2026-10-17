"""Prompt-toolkit resolution UI for ambiguous filament imports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

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


def _entry_description(entry: FilamentReconciliationEntry) -> str:
    """Return the source-filament details shown in the selection dialog."""
    record = entry.provisional_record
    return (
        f"[{entry.source_index}] {record.maker} / {record.type} / "
        f"{record.finish or '-'} / {record.color} / {record.hex}"
    )


def _resolution_choices(
    entry: FilamentReconciliationEntry,
) -> Sequence[tuple[str, str]]:
    """Build prompt-toolkit radio-list values for one ambiguous record."""
    choices: list[tuple[str, str]] = []
    for number, candidate in enumerate(entry.candidates, start=1):
        reasons = "; ".join(candidate.reasons) or candidate.kind
        choices.append(
            (
                f"use:{candidate.filament_id}",
                f"{number}. {candidate.filament_id} "
                f"({candidate.score:.1f}: {reasons})",
            )
        )
    choices.extend(
        (
            ("new", f"Import new as {entry.proposed_filament_id}"),
            ("skip", "Skip this filament"),
        )
    )
    return choices


def _ask_resolution(entry: FilamentReconciliationEntry) -> FilamentResolution | None:
    """Show a prompt-toolkit radio-list dialog for one resolution."""
    from prompt_toolkit.key_binding import (
        KeyBindings,
        KeyPressEvent,
        merge_key_bindings,
    )
    from prompt_toolkit.shortcuts import radiolist_dialog
    from prompt_toolkit.styles import Style

    style = Style.from_dict(
        {
            "dialog frame.label": "bold",
            "dialog.body": "bg:#202020 #f0f0f0",
            "dialog shadow": "bg:#101010",
            "button.focused": "bg:#ffffff #000000 bold",
            "radio-selected": "#00d7ff bold",
        }
    )
    try:
        dialog = radiolist_dialog(
            title="Resolve filament import",
            text=_entry_description(entry),
            values=_resolution_choices(entry),
            ok_text="Use",
            cancel_text="Cancel",
            style=style,
        )
        cancel_bindings = KeyBindings()

        def _cancel(event: KeyPressEvent) -> None:
            event.app.exit(result=None)

        cancel_bindings.add("escape")(_cancel)
        if dialog.key_bindings is None:
            dialog.key_bindings = cancel_bindings
        else:
            dialog.key_bindings = merge_key_bindings(
                [dialog.key_bindings, cancel_bindings]
            )
        selection = cast(
            str | None,
            dialog.run(),
        )
    except (EOFError, KeyboardInterrupt):
        return None

    if selection is None:
        return None
    if selection == "new":
        return ImportNew()
    if selection == "skip":
        return Skip()
    prefix, separator, filament_id = selection.partition(":")
    if prefix == "use" and separator and filament_id:
        return UseExisting(filament_id)
    raise RuntimeError(f"Unexpected filament resolution selection: {selection!r}")


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
        resolution = _ask_resolution(entry)
        if resolution is None:
            print("Reconciliation cancelled; no files were changed.")
            return None
        resolutions[entry.source_index] = resolution
    return resolutions


__all__ = ["collect_filament_resolutions"]
