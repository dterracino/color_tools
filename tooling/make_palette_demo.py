"""
Generate an animated APNG palette quantization demo for the README.

Produces an animation cycling through: Original → Quantized (→ Dithered).

  --palette <name> [name ...]   One or more palette names (e.g. cga4 nes gameboy)
  --dither                      Also show a Floyd-Steinberg dithered frame per palette
  --metric <metric>             Distance metric for quantization (default: de2000)

Transition options: flip (hard cut) or crossfade (smoothstep-eased blend).

Usage examples:
    python tooling/make_palette_demo.py samples/pencils.png --palette cga4
    python tooling/make_palette_demo.py samples/pencils.png --palette cga4 --dither
    python tooling/make_palette_demo.py samples/pencils.png --palette cga4 nes gameboy
    python tooling/make_palette_demo.py samples/pencils.png \\
        --palette cga4 nes --dither --transition crossfade --optimize
    python tooling/make_palette_demo.py samples/pencils.png \\
        --palette ega16 --output samples/ega-demo.png --optimize

Output: animated APNG beside the source image (or --output path).
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

# Internal framerate used to convert transition-duration to frame count.
_FPS = 25

# Human-readable labels for built-in palette names.
_PALETTE_LABELS: dict[str, str] = {
    "cga4":         "CGA 4",
    "cga16":        "CGA 16",
    "ega16":        "EGA 16",
    "ega64":        "EGA 64",
    "vga":          "VGA 256",
    "web":          "Web Safe 216",
    "nes":          "NES",
    "gameboy":      "Game Boy",
    "gameboy_dmg":  "Game Boy (DMG)",
    "gameboy_gbl":  "Game Boy Light",
    "gameboy_mgb":  "Game Boy Pocket",
    "gameboy-color": "Game Boy Color",
    "commodore64":  "Commodore 64",
    "pico8":        "PICO-8",
    "sms":          "Sega Master System",
    "tandy16":      "Tandy 16",
    "apple2":       "Apple II",
    "macintosh":    "Macintosh",
    "virtualboy":   "Virtual Boy",
    "crayola":      "Crayola 120",
}


def _palette_label(name: str) -> str:
    """Return a human-readable label for a palette name."""
    return _PALETTE_LABELS.get(name, name.replace("_", " ").replace("-", " ").title())


# ---------------------------------------------------------------------------
# Helpers (adapted from make_cvd_demo.py)
# ---------------------------------------------------------------------------

def _smoothstep(t: float) -> float:
    """Smoothstep easing: 3t^2 - 2t^3  (S-curve, 0 to 1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _add_label(img: PILImage.Image, text: str) -> PILImage.Image:
    """Draw a semi-transparent label bar with stroked text at the bottom of img."""
    from PIL import Image, ImageDraw, ImageFont

    img = img.copy().convert("RGBA")
    w, h = img.size
    bar_h = max(32, h // 14)
    font_size = max(14, bar_h - 8)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 160))

    font = None
    for font_name in ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except (OSError, IOError):
            pass
    if font is None:
        try:
            font = ImageFont.load_default(size=font_size)
        except TypeError:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (w - text_w) // 2
    y = h - bar_h + (bar_h - text_h) // 2 - bbox[1]
    draw.text(
        (x, y), text, font=font,
        fill=(255, 255, 255, 230),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


def _crossfade_frames(
    src: PILImage.Image,
    dst: PILImage.Image,
    transition_duration: float,
) -> list[tuple[PILImage.Image, int]]:
    """Return smoothstep-blended (frame, duration_ms) pairs from src to dst."""
    from PIL import Image

    steps = max(1, round(_FPS * transition_duration))
    frame_ms = max(1, math.floor(transition_duration * 1000 / steps))

    result: list[tuple[Image.Image, int]] = []
    src_rgb = src.convert("RGB")
    dst_rgb = dst.convert("RGB")
    for i in range(1, steps + 1):
        t = _smoothstep(i / (steps + 1))
        blended = Image.blend(src_rgb, dst_rgb, t)
        result.append((blended, frame_ms))
    return result


def _expand_transitions(
    content_frames: list[tuple[PILImage.Image, int]],
    transition: str,
    transition_duration: float,
) -> list[tuple[PILImage.Image, int]]:
    """Expand content frames with inter-frame transitions."""
    sequence: list[tuple[PILImage.Image, int]] = []
    for i, (frame, dur) in enumerate(content_frames):
        sequence.append((frame, dur))
        if transition == "crossfade":
            next_frame = content_frames[(i + 1) % len(content_frames)][0]
            for bf, bms in _crossfade_frames(frame, next_frame, transition_duration):
                sequence.append((bf, bms))
    return sequence


def _save_apng(
    output_path: Path,
    sequence: list[tuple[PILImage.Image, int]],
    optimize: bool,
) -> None:
    """Save sequence to APNG, optionally optimize with oxipng."""
    frames    = [f for f, _ in sequence]
    durations = [d for _, d in sequence]

    frames[0].save(
        output_path,
        format="PNG",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    original_bytes = output_path.stat().st_size
    original_kb = original_bytes // 1024
    print(f"Saved:      {output_path}  ({original_kb} KB, {len(frames)} frames)")

    if optimize:
        _run_apngopt(output_path, original_bytes)

    print(f"Embed with: ![Palette Demo]({output_path.as_posix()})")


def _run_apngopt(path: Path, original_bytes: int) -> None:
    """Optimize an APNG in-place using oxipng."""
    try:
        result = subprocess.run(
            ["oxipng", "-o", "4", "--strip", "safe", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip() or "unknown error"
            print(f"  oxipng failed: {msg}")
            return
        compressed_bytes = path.stat().st_size
        compressed_kb = compressed_bytes // 1024
        saving_pct = (1.0 - compressed_bytes / original_bytes) * 100.0
        print(f"  Optimized:  {original_bytes // 1024} KB -> {compressed_kb} KB  ({saving_pct:.1f}% smaller)")
    except FileNotFoundError:
        print("  oxipng not found in PATH -- skipping optimization")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an animated APNG palette quantization demo (Original → Quantized).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        help="Path to input image (JPEG, PNG, WebP, etc.)",
    )
    parser.add_argument(
        "--palette", nargs="+", default=["cga4"], metavar="NAME",
        help="One or more palette names to cycle through (default: cga4). "
             "Examples: cga4, nes, gameboy, ega16, commodore64, pico8",
    )
    parser.add_argument(
        "--dither", action="store_true",
        help="Also show a Floyd-Steinberg dithered frame for each palette",
    )
    parser.add_argument(
        "--metric", default="de2000",
        choices=["de2000", "de94", "de76", "cmc", "euclidean", "hsl_euclidean"],
        help="Color distance metric for palette matching (default: de2000)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output APNG path (auto-named beside source if omitted)",
    )
    parser.add_argument(
        "--duration", type=float, default=2.5,
        help="Seconds each content frame is held (default: 2.5)",
    )
    parser.add_argument(
        "--transition", choices=["flip", "crossfade"], default="flip",
        help="Transition style between frames (default: flip)",
    )
    parser.add_argument(
        "--transition-duration", type=float, default=0.4, dest="transition_duration",
        help="Duration of crossfade transition in seconds (default: 0.4)",
    )
    parser.add_argument(
        "--no-labels", action="store_false", dest="labels",
        help="Omit text labels on each frame (labels are on by default)",
    )
    parser.add_argument(
        "--optimize", action="store_true",
        help="Optimize output APNG with oxipng (must be in PATH)",
    )
    parser.set_defaults(labels=True)
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is required. Install with: pip install color-match-tools[image]")
        return 1

    try:
        from color_tools.image import quantize_image_to_palette
    except ImportError as exc:
        print(f"ERROR: color_tools image module unavailable: {exc}")
        print("Install with: pip install color-match-tools[image]")
        return 1

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    palettes: list[str] = args.palette
    hold_ms = int(args.duration * 1000)

    def labelled(img: Image.Image, text: str) -> Image.Image:
        return _add_label(img, text) if args.labels else img.copy().convert("RGB")

    # Load original
    print(f"Loading:    {input_path}")
    with Image.open(input_path) as _src:
        original_rgb = _src.convert("RGB")

    # Build content frames
    # Sequence: Original → for each palette → Quantized [→ Dithered]
    content_frames: list[tuple[Image.Image, int]] = [
        (labelled(original_rgb, "Original"), hold_ms),
    ]

    for palette_name in palettes:
        label = _palette_label(palette_name)
        print(f"Quantizing: {palette_name} (no dither) ...")
        try:
            quantized = quantize_image_to_palette(
                input_path, palette_name, metric=args.metric, dither=False
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}")
            return 1
        content_frames.append((labelled(quantized, label), hold_ms))

        if args.dither:
            print(f"Quantizing: {palette_name} (dithered) ...")
            dithered = quantize_image_to_palette(
                input_path, palette_name, metric=args.metric, dither=True
            )
            content_frames.append((labelled(dithered, f"{label} (Dithered)"), hold_ms))

    # Build APNG sequence with transitions
    sequence = _expand_transitions(content_frames, args.transition, args.transition_duration)

    # Determine output path
    if args.output:
        out = Path(args.output)
    else:
        palette_slug = "-".join(palettes[:3])
        if len(palettes) > 3:
            palette_slug += f"-plus{len(palettes) - 3}"
        dither_suffix = "-dither" if args.dither else ""
        out = input_path.parent / f"{input_path.stem}-{palette_slug}{dither_suffix}-{args.transition}.png"

    out.parent.mkdir(parents=True, exist_ok=True)
    _save_apng(out, sequence, args.optimize)
    return 0


if __name__ == "__main__":
    sys.exit(main())
