"""Harmony command handler - Generate styled LCH color harmonies."""

from __future__ import annotations

import sys
from argparse import Namespace

from ...harmony import HarmonyResult, generate_harmony, generate_harmony_lch
from ..utils import parse_hex_or_exit


def _print_harmony_result(result: HarmonyResult) -> None:
    """Print a generated harmony in a readable CLI format."""
    print(f"Harmony: {result.scheme}")
    print(f"Mood: {result.mood or 'none'}")
    print(f"Tone: {result.tone}")
    print(f"Base graded: {'yes' if result.grade_base else 'no'}")
    print(
        "Base LCH: "
        f"({result.base_lch[0]:.2f}, {result.base_lch[1]:.2f}, {result.base_lch[2]:.1f}°)"
    )

    for index, color in enumerate(result.colors, 1):
        lightness, chroma, hue = color.ideal_lch
        print(f"\n{index}. Hue offset: {color.hue_offset:+.1f}°")
        print(f"   Ideal LCH: ({lightness:.2f}, {chroma:.2f}, {hue:.1f}°)")
        if color.rgb is None:
            print("   sRGB: out of gamut (not mapped)")
            continue

        print(f"   Hex: {color.hex}")
        print(f"   RGB: {color.rgb}")
        if color.was_in_gamut:
            print("   Gamut: in sRGB gamut")
        else:
            print(f"   Gamut: mapped to sRGB (Delta E {color.gamut_delta_e:.2f})")


def handle_harmony_command(args: Namespace) -> None:
    """Handle the top-level ``harmony`` command."""
    if args.value is not None and args.hex is not None:
        print("Error: Cannot specify both --value and --hex", file=sys.stderr)
        sys.exit(2)
    if args.value is None and args.hex is None:
        print("Error: harmony requires either --value or --hex", file=sys.stderr)
        sys.exit(2)

    try:
        if args.hex is not None:
            result = generate_harmony(
                parse_hex_or_exit(args.hex),
                args.scheme,
                map_to_gamut=not args.no_gamut_map,
                mood=args.mood,
                tone=args.tone,
                grade_base=args.grade_base,
            )
        elif args.space == "lch":
            lch = tuple(float(component) for component in args.value)
            result = generate_harmony_lch(
                lch,
                args.scheme,
                map_to_gamut=not args.no_gamut_map,
                mood=args.mood,
                tone=args.tone,
                grade_base=args.grade_base,
            )
        else:
            channels = tuple(float(component) for component in args.value)
            if any(not channel.is_integer() for channel in channels):
                raise ValueError("RGB harmony values must be integers")
            result = generate_harmony(
                tuple(int(channel) for channel in channels),
                args.scheme,
                map_to_gamut=not args.no_gamut_map,
                mood=args.mood,
                tone=args.tone,
                grade_base=args.grade_base,
            )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)

    _print_harmony_result(result)
    sys.exit(0)
