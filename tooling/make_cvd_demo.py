"""
Generate an animated APNG CVD demo for the README.

Produces an animation cycling: Original -> Simulated -> Corrected.

  --deficiency <type>   Single deficiency type (default: deuteranopia)
  --deficiency each     One output file per deficiency type
  --deficiency all      One output file with all three deficiency types

  --label-type long     Full labels: "Simulated (Protanopia)"  [default]
  --label-type short    Short labels: "Simulated (Protan)"

Transition options: flip (hard cut) or crossfade (smoothstep-eased blend).

Usage examples:
    python tooling/make_cvd_demo.py samples/image/my-photo.jpg
    python tooling/make_cvd_demo.py samples/image/my-photo.jpg --deficiency each
    python tooling/make_cvd_demo.py samples/image/my-photo.jpg --deficiency all
    python tooling/make_cvd_demo.py samples/image/my-photo.jpg \\
        --deficiency protan --transition crossfade --transition-duration 0.6
    python tooling/make_cvd_demo.py samples/image/my-photo.jpg \\
        --output samples/cvd-demo.png --optimize

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

# Canonical processing order for "each" and "all" modes.
_DEFICIENCY_ORDER = ["protanopia", "deuteranopia", "tritanopia"]

# Normalize aliases (protan -> protanopia, etc.)
_NORMALIZE: dict[str, str] = {
    "protan":       "protanopia",
    "deutan":       "deuteranopia",
    "tritan":       "tritanopia",
    "protanopia":   "protanopia",
    "deuteranopia": "deuteranopia",
    "tritanopia":   "tritanopia",
}

_LABEL_LONG: dict[str, str] = {
    "protanopia":   "Protanopia",
    "deuteranopia": "Deuteranopia",
    "tritanopia":   "Tritanopia",
}
_LABEL_SHORT: dict[str, str] = {
    "protanopia":   "Protan",
    "deuteranopia": "Deutan",
    "tritanopia":   "Tritan",
}


# ---------------------------------------------------------------------------
# Helpers
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

    print(f"Embed with: ![CVD Demo]({output_path.as_posix()})")


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
        description="Generate an animated APNG CVD demo (Original -> Simulated -> Corrected).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        help="Path to input image (JPEG, PNG, WebP, etc.)",
    )
    parser.add_argument(
        "--deficiency", default="deuteranopia",
        choices=[
            "protanopia", "protan",
            "deuteranopia", "deutan",
            "tritanopia", "tritan",
            "each", "all",
        ],
        help="CVD type, 'each' (one file per type), or 'all' (combined file) (default: deuteranopia)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output APNG path (auto-named beside source if omitted; ignored for --deficiency each)",
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
        "--label-type", choices=["long", "short"], default="long", dest="label_type",
        help="Label style: long 'Protanopia' or short 'Protan' (default: long)",
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
        from color_tools.image import simulate_cvd_image, correct_cvd_image
    except ImportError as exc:
        print(f"ERROR: color_tools image module unavailable: {exc}")
        print("Install with: pip install color-match-tools[image]")
        return 1

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    # --- Load source, strip alpha ---
    print(f"Loading:    {input_path}")
    _src = Image.open(input_path)
    has_alpha = _src.mode in ("RGBA", "LA", "PA") or "transparency" in _src.info
    alpha_channel = _src.convert("RGBA").getchannel("A") if has_alpha else None
    original_rgb = _src.convert("RGB")

    # --- Helpers scoped to this run ---
    hold_ms = int(args.duration * 1000)
    label_map = _LABEL_SHORT if args.label_type == "short" else _LABEL_LONG

    def apply_alpha(img: Image.Image) -> Image.Image:
        if alpha_channel is None:
            return img
        out = img.convert("RGBA")
        out.putalpha(alpha_channel)
        return out

    def labelled(img: Image.Image, text: str) -> Image.Image:
        f = _add_label(img, text) if args.labels else img.copy()
        return apply_alpha(f)

    def process_deficiency(d: str) -> list[tuple[Image.Image, int]]:
        """Return content_frames (Original, Sim, Corr) for one canonical deficiency."""
        dlabel = label_map[d]
        print(f"Simulating: {d} ...")
        sim  = simulate_cvd_image(input_path, d).convert("RGB")
        print(f"Correcting: {d} ...")
        corr = correct_cvd_image(input_path, d).convert("RGB")
        return [
            (labelled(original_rgb, "Original"),                   hold_ms),
            (labelled(sim,  f"Simulated ({dlabel})"),              hold_ms),
            (labelled(corr, f"Corrected ({dlabel})"),              hold_ms),
        ]

    # --- Dispatch ---
    mode = args.deficiency

    if mode == "each":
        if args.output:
            print("NOTE: --output is ignored with --deficiency each (files are auto-named)")
        for d in _DEFICIENCY_ORDER:
            print(f"\n[{d}]")
            content_frames = process_deficiency(d)
            sequence = _expand_transitions(content_frames, args.transition, args.transition_duration)
            out = input_path.parent / f"{input_path.stem}-{d}-{args.transition}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            _save_apng(out, sequence, args.optimize)

    elif mode == "all":
        # One file: Original -> Sim+Corr(protan) -> Sim+Corr(deutan) -> Sim+Corr(tritan)
        content_frames = [(labelled(original_rgb, "Original"), hold_ms)]
        for d in _DEFICIENCY_ORDER:
            dlabel = label_map[d]
            print(f"Simulating: {d} ...")
            sim  = simulate_cvd_image(input_path, d).convert("RGB")
            print(f"Correcting: {d} ...")
            corr = correct_cvd_image(input_path, d).convert("RGB")
            content_frames.append((labelled(sim,  f"Simulated ({dlabel})"), hold_ms))
            content_frames.append((labelled(corr, f"Corrected ({dlabel})"), hold_ms))
        sequence = _expand_transitions(content_frames, args.transition, args.transition_duration)
        if args.output:
            out = Path(args.output)
        else:
            out = input_path.parent / f"{input_path.stem}-all-{args.transition}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        _save_apng(out, sequence, args.optimize)

    else:
        # Single deficiency
        d = _NORMALIZE[mode]
        content_frames = process_deficiency(d)
        sequence = _expand_transitions(content_frames, args.transition, args.transition_duration)
        if args.output:
            out = Path(args.output)
        else:
            out = input_path.parent / f"{input_path.stem}-{d}-{args.transition}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        _save_apng(out, sequence, args.optimize)

    return 0


if __name__ == "__main__":
    sys.exit(main())