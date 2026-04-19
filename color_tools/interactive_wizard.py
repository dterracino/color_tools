"""
Interactive wizard for color-tools.

Provides a guided question-and-answer interface for the color, filament,
and convert commands. No need to remember flags — just answer the prompts.

Requires the [interactive] extra::

    pip install color-match-tools[interactive]

Launches automatically when color-tools is invoked with no arguments, or
explicitly with::

    color-tools --interactive
    color-tools -i
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    import argparse

from ._interactive_utils import PROMPT_TOOLKIT_AVAILABLE, check_prompt_toolkit, show_install_message

# Import prompt_toolkit symbols needed by this module
try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.styles import Style
except ImportError:
    pass  # PROMPT_TOOLKIT_AVAILABLE from _interactive_utils handles the guard

__all__ = [
    "run_interactive_wizard",
    "check_prompt_toolkit",
]

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

_WIZARD_STYLE: "Style | None" = None


def _get_style() -> "Style | None":
    global _WIZARD_STYLE
    if _WIZARD_STYLE is None and PROMPT_TOOLKIT_AVAILABLE:
        _WIZARD_STYLE = Style.from_dict({
            "": "ansicyan",
        })
    return _WIZARD_STYLE


# ---------------------------------------------------------------------------
# Parser introspection helpers
# ---------------------------------------------------------------------------

def _get_subparser(command: str) -> "argparse.ArgumentParser | None":
    """Return the subparser for the given command name, or None."""
    try:
        from .cli import build_parser
        parser = build_parser()
        for action in parser._actions:
            if hasattr(action, '_name_parser_map'):
                return action._name_parser_map.get(command)
    except Exception:
        pass
    return None


def _get_choices(command: str, dest: str) -> list[str]:
    """
    Return the choices list for a given argument in a subcommand.
    Falls back to [] if introspection fails.
    """
    sub = _get_subparser(command)
    if sub is None:
        return []
    for action in sub._actions:
        if action.dest == dest and action.choices:
            return list(action.choices)
    return []


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _pt(message: str, completer: "WordCompleter | None" = None) -> str:
    """Wrapper around prompt_toolkit prompt() — always returns a str."""
    return _pt_prompt(message, completer=completer, style=_get_style())  # type: ignore[return-value]


def _ask_choice(question: str, choices: list[str],
                labels: list[str] | None = None) -> int | None:
    """
    Display a numbered menu and return the 1-based index of the user's choice.
    Returns None if the user quits.

    Args:
        question: The question to display above the menu.
        choices:  Internal values (used for completion).
        labels:   Display strings (same length as choices). Defaults to choices.
    """
    display = labels if labels else choices
    print()
    for i, label in enumerate(display, 1):
        print(f"  {i}  {label}")
    print()

    completer = WordCompleter([str(i) for i in range(1, len(choices) + 1)])
    while True:
        try:
            answer = _pt(f"  {question} [1-{len(choices)}, q=quit]: ",
                         completer=completer).strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if answer.lower() in ("q", "quit", "exit"):
            return None
        try:
            n = int(answer)
            if 1 <= n <= len(choices):
                return n
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(choices)}.")


def _ask_color_input(label: str = "color to match") -> tuple[list[str], str] | None:
    """
    Ask "hex or RGB?" then collect the value.

    Returns:
        (args_fragment, display_string) where args_fragment is either
        ["--hex", "#RRGGBB"]  or  ["--value", "R", "G", "B"],
        or None if the user cancelled.
    """
    mode = _ask_choice(
        f"How do you want to enter the {label}?",
        ["hex", "rgb"],
        ["Hex code  (e.g. #FF8040 or FF8040)",
         "RGB values  (0-255 each)"],
    )
    if mode is None:
        return None

    if mode == 1:
        # Hex
        print()
        while True:
            try:
                raw = _pt("  Hex color (#RRGGBB or RRGGBB): ").strip()
            except (KeyboardInterrupt, EOFError):
                return None
            if raw.lower() in ("q", "quit", "exit"):
                return None
            cleaned = raw.lstrip("#").strip()
            if len(cleaned) == 6 and all(c in "0123456789abcdefABCDEF"
                                          for c in cleaned):
                return ["--hex", f"#{cleaned.upper()}"], f"#{cleaned.upper()}"
            print("  Not a valid hex code. Try again (e.g. FF8040 or #FF8040).")

    else:
        # RGB
        print()
        values: list[int] = []
        for channel in ("R", "G", "B"):
            while True:
                try:
                    raw = _pt(f"    {channel} (0-255): ").strip()
                except (KeyboardInterrupt, EOFError):
                    return None
                if raw.lower() in ("q", "quit", "exit"):
                    return None
                try:
                    n = int(raw)
                    if 0 <= n <= 255:
                        values.append(n)
                        break
                    print("    Must be 0-255.")
                except ValueError:
                    print("    Please enter a whole number.")

        return (["--value", str(values[0]), str(values[1]), str(values[2])],
                f"rgb({values[0]}, {values[1]}, {values[2]})")


def _ask_float(label: str, lo: float, hi: float) -> float | None:
    """Prompt for a float in [lo, hi]. Returns None on cancel."""
    while True:
        try:
            raw = _pt(f"    {label} ({lo:g}-{hi:g}): ").strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if raw.lower() in ("q", "quit", "exit"):
            return None
        try:
            v = float(raw)
            if lo <= v <= hi:
                return v
            print(f"    Must be between {lo:g} and {hi:g}.")
        except ValueError:
            print("    Please enter a number.")


def _ask_optional(label: str,
                  completer: "WordCompleter | None" = None) -> str | None:
    """
    Prompt for optional text (Enter to skip, q to quit).
    Returns the text, "" for skip, or None on quit/cancel.
    """
    try:
        raw = _pt(f"  {label} [Enter to skip, q=quit]: ",
                  completer=completer).strip()
    except (KeyboardInterrupt, EOFError):
        return None
    if raw.lower() in ("q", "quit", "exit"):
        return None
    return raw  # "" means skip


def _ask_multi(label: str, options: list[str]) -> list[str] | None:
    """
    Prompt for zero or more values from *options* with Tab-completion.

    The user picks one at a time; an empty Enter finishes the selection.
    Returns the list of chosen values (may be empty = skip), or None on quit.

    Example interaction::

        Filter by finish? (Tab, empty=done, q=quit)
          Selected: (none)
        > Matte
          Selected: Matte
        > Basic
          Selected: Matte, Basic
        >             ← empty Enter → done
    """
    chosen: list[str] = []
    remaining = list(options)
    completer = WordCompleter(remaining, ignore_case=True) if remaining else None

    print(f"\n  {label}")
    while True:
        selected_display = ", ".join(chosen) if chosen else "(none)"
        print(f"    Selected: {selected_display}")
        try:
            raw = _pt("  > ", completer=completer).strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if raw.lower() in ("q", "quit", "exit"):
            return None
        if raw == "":
            return chosen
        # Accept any value (typed or from completion)
        chosen.append(raw)
        # Remove from completion list to avoid duplicates
        remaining = [o for o in remaining if o.lower() != raw.lower()]
        completer = WordCompleter(remaining, ignore_case=True) if remaining else None


def _print_header(title: str) -> None:
    bar = "─" * max(0, 62 - len(title) - 4)
    print(f"\n── {title} {bar}")


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------

def _run_command(args_list: list[str], json_path: "Path | None" = None) -> None:
    """
    Print the equivalent CLI command, then execute it via main().
    The existing handler calls sys.exit() — that is the intended outcome.
    """
    import shlex
    from .cli_commands.utils import get_program_name

    prog = get_program_name()
    full_args = list(args_list)
    if json_path is not None:
        full_args = ["--json", str(json_path)] + full_args

    cmd_str = prog + " " + " ".join(shlex.quote(str(a)) for a in full_args)
    print(f"\n  ▶  {cmd_str}")
    print("  " + "─" * min(len(cmd_str) + 5, 78))
    sys.stdout.flush()  # must flush before main() replaces sys.stdout on Windows

    from .cli import main  # lazy import — cli already loaded in sys.modules
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + full_args
    try:
        main()
    finally:
        sys.argv = old_argv


# ---------------------------------------------------------------------------
# color wizard
# ---------------------------------------------------------------------------

def _run_color_wizard(json_path: "Path | None" = None) -> None:
    _print_header("Color search")

    op = _ask_choice(
        "What do you want to do?",
        ["name", "nearest"],
        ["Find a color by name  (e.g. coral, steel blue)",
         "Find the nearest CSS color to a given color value"],
    )
    if op is None:
        return

    args_list: list[str] = ["color"]

    if op == 1:
        # By name
        print()
        try:
            name = _pt("  Color name: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if not name or name.lower() in ("q", "quit", "exit"):
            return
        args_list += ["--name", name]

    else:
        # Nearest
        print()
        result = _ask_color_input("color to match")
        if result is None:
            return
        color_args, _ = result
        args_list += ["--nearest"] + color_args

        # --space only matters for --value (not --hex)
        if "--value" in color_args:
            spaces = _get_choices("color", "space") or ["rgb", "hsl", "lab", "lch"]
            space_idx = _ask_choice(
                "Which color space are those values in?",
                spaces,
                [s.upper() for s in spaces],
            )
            if space_idx is None:
                return
            args_list += ["--space", spaces[space_idx - 1]]

        # Optional: distance metric
        metrics = _get_choices("color", "metric") or ["de2000", "de76", "de94", "cmc", "euclidean", "hyab"]
        print()
        metric_idx = _ask_choice(
            "Distance metric?",
            metrics,
            [f"{m}{'  ← default' if m == 'de2000' else ''}" for m in metrics],
        )
        if metric_idx is None:
            return
        chosen_metric = metrics[metric_idx - 1]
        if chosen_metric != "de2000":
            args_list += ["--metric", chosen_metric]

        # Optional: palette
        print()
        palette_raw = _ask_optional(
            "Use a retro palette? (cga4, cga16, ega16, vga, web, gameboy, pico8…)"
        )
        if palette_raw is None:
            return
        if palette_raw:
            args_list += ["--palette", palette_raw]

    _run_command(args_list, json_path)


# ---------------------------------------------------------------------------
# filament wizard
# ---------------------------------------------------------------------------

def _run_filament_wizard(json_path: "Path | None" = None) -> None:
    _print_header("Filament search")

    # Pre-load palette for Tab-completion on maker/type/finish
    makers: list[str] = []
    types: list[str] = []
    finishes: list[str] = []
    try:
        from .filament_palette import FilamentPalette
        palette = FilamentPalette.load_default() if json_path is None else None
        if palette:
            makers = sorted({r.maker for r in palette.records})
            types = sorted({r.type for r in palette.records})
            finishes = sorted({r.finish for r in palette.records if r.finish})
    except Exception:
        pass

    # Color input
    print()
    result = _ask_color_input("filament color to match")
    if result is None:
        return
    color_args, _ = result

    args_list: list[str] = ["filament", "--nearest"] + color_args

    # Optional: distance metric (pulled from parser)
    metrics = _get_choices("filament", "metric") or ["de2000", "de76", "de94", "cmc", "euclidean", "hyab"]
    print()
    metric_idx = _ask_choice(
        "Distance metric?",
        metrics,
        [f"{m}{'  ← default' if m == 'de2000' else ''}" for m in metrics],
    )
    if metric_idx is None:
        return
    if metrics[metric_idx - 1] != "de2000":
        args_list += ["--metric", metrics[metric_idx - 1]]

    # Optional filters
    print()
    maker_values = _ask_multi("Filter by maker? (Tab for suggestions, empty=done)",
                              makers)
    if maker_values is None:
        return
    if maker_values:
        args_list += ["--maker"] + maker_values

    print()
    type_values = _ask_multi("Filter by filament type? (Tab for suggestions, empty=done)",
                             types)
    if type_values is None:
        return
    if type_values:
        args_list += ["--type"] + type_values

    print()
    finish_values = _ask_multi("Filter by finish? (Tab for suggestions, empty=done)",
                               finishes)
    if finish_values is None:
        return
    if finish_values:
        args_list += ["--finish"] + finish_values

    # Owned vs all
    print()
    try:
        owned_answer = _pt(
            "  Search only owned filaments? [y/N, q=quit]: "
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return
    if owned_answer in ("q", "quit", "exit"):
        return
    if owned_answer not in ("y", "yes"):
        args_list.append("--all-filaments")

    _run_command(args_list, json_path)


# ---------------------------------------------------------------------------
# convert wizard
# ---------------------------------------------------------------------------

# (space key, display label, [(component_label, lo, hi, is_int), ...])
_SPACE_DEFS: list[tuple[str, str, list[tuple[str, float, float, bool]]]] = [
    ("rgb",  "RGB   — Red, Green, Blue  (0-255 each)",
     [("R", 0, 255, True), ("G", 0, 255, True), ("B", 0, 255, True)]),
    ("hsl",  "HSL   — Hue (0-360°), Saturation (0-100%), Lightness (0-100%)",
     [("H hue °", 0, 360, False), ("S saturation %", 0, 100, False),
      ("L lightness %", 0, 100, False)]),
    ("lab",  "LAB   — CIE L*a*b*  perceptual color space",
     [("L*", 0, 100, False), ("a*", -128, 127, False), ("b*", -128, 127, False)]),
    ("lch",  "LCH   — CIE L*C*h°  cylindrical perceptual color space",
     [("L*", 0, 100, False), ("C*", 0, 230, False), ("h° hue", 0, 360, False)]),
    ("cmy",  "CMY   — Cyan, Magenta, Yellow  (0-100% each)",
     [("C cyan %", 0, 100, False), ("M magenta %", 0, 100, False),
      ("Y yellow %", 0, 100, False)]),
    ("cmyk", "CMYK  — Cyan, Magenta, Yellow, Key/Black  (0-100% each)",
     [("C cyan %", 0, 100, False), ("M magenta %", 0, 100, False),
      ("Y yellow %", 0, 100, False), ("K black %", 0, 100, False)]),
]
_SPACE_KEYS   = [s for s, _, _ in _SPACE_DEFS]
_SPACE_LABELS = [l for _, l, _ in _SPACE_DEFS]


def _prompt_space_values(space_key: str) -> list[str] | None:
    """Prompt for each component of the given color space. Returns None on cancel."""
    components = next((comps for k, _, comps in _SPACE_DEFS if k == space_key), None)
    if components is None:
        return None
    values: list[str] = []
    for label, lo, hi, is_int in components:
        if is_int:
            v = _ask_float(label, float(lo), float(hi))
            if v is None:
                return None
            values.append(str(int(v)))
        else:
            v = _ask_float(label, lo, hi)
            if v is None:
                return None
            values.append(str(v))
    return values


def _run_convert_wizard(json_path: "Path | None" = None) -> None:
    _print_header("Color conversion")

    # Pull available spaces from parser if possible, fall back to _SPACE_KEYS
    parser_spaces = _get_choices("convert", "from_space") or _SPACE_KEYS
    # Build display labels only for spaces that the parser also knows about
    avail = [(k, l) for k, l, _ in _SPACE_DEFS if k in parser_spaces]
    avail_keys   = [k for k, _ in avail]
    avail_labels = [l for _, l in avail]

    from_idx = _ask_choice("Convert FROM which space?", avail_keys, avail_labels)
    if from_idx is None:
        return
    from_space = avail_keys[from_idx - 1]

    to_idx = _ask_choice("Convert TO which space?", avail_keys, avail_labels)
    if to_idx is None:
        return
    to_space = avail_keys[to_idx - 1]

    # For RGB source the user may prefer hex input
    if from_space == "rgb":
        result = _ask_color_input("source color")
        if result is None:
            return
        color_args, _ = result
        # If hex was chosen, no --from needed (handler infers rgb from --hex)
        if "--hex" in color_args:
            args_list = ["convert", "--to", to_space] + color_args
        else:
            args_list = ["convert", "--from", from_space, "--to", to_space] + color_args
    else:
        print(f"\n  Enter {from_space.upper()} values:")
        values = _prompt_space_values(from_space)
        if values is None:
            return
        args_list = ["convert", "--from", from_space, "--to", to_space,
                     "--value"] + values

    _run_command(args_list, json_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_interactive_wizard(json_path: "Path | None" = None) -> None:
    """
    Launch the interactive wizard.

    Guides the user through color search, filament matching, and color space
    conversion via prompted questions. Requires the [interactive] extra.

    Args:
        json_path: Optional custom data directory (passed to handlers).
    """
    if not PROMPT_TOOLKIT_AVAILABLE:
        show_install_message()
        sys.exit(1)

    print()
    print("  color-tools interactive wizard")
    print("  " + "─" * 58)
    print("  Guided prompts for color search, filament matching,")
    print("  and color space conversion.")
    print("  Press Ctrl-C or type 'q' at any prompt to quit.")

    choice = _ask_choice(
        "What would you like to do?",
        ["color", "filament", "convert"],
        [
            "color    — Find a CSS color by name or nearest match",
            "filament — Find the nearest 3D printing filament for a color",
            "convert  — Convert a color between spaces (RGB, LAB, LCH, HSL, CMY, CMYK)",
        ],
    )

    if choice is None:
        print()
        sys.exit(0)

    if choice == 1:
        _run_color_wizard(json_path)
    elif choice == 2:
        _run_filament_wizard(json_path)
    elif choice == 3:
        _run_convert_wizard(json_path)

