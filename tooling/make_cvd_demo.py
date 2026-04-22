"""
Generate an animated APNG CVD demo for the README.

Produces a 3-frame animation:
  Frame 1 — Original image          (labelled "Original")
  Frame 2 — CVD simulation          (labelled "Simulated: <deficiency>")
  Frame 3 — CVD correction applied  (labelled "Corrected: <deficiency>")

Each frame is held for --duration seconds (default 2.5 s).
Transition options: flip (hard cut) or crossfade (smooth blend).

Usage examples:
    python scripts/make_cvd_demo.py --file samples/image/my-photo.jpg
    python scripts/make_cvd_demo.py --file samples/image/my-photo.jpg --deficiency protanopia
    python scripts/make_cvd_demo.py --file samples/image/my-photo.jpg \\
        --transition crossfade --crossfade-steps 12 --duration 3.0
    python scripts/make_cvd_demo.py --file samples/image/my-photo.jpg \\
        --output samples/cvd-demo.png --max-width 800

Output: samples/cvd-demo.png  (animated APNG, full colour, lossless)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Label overlay helper
# ---------------------------------------------------------------------------

def _add_label(img: "PIL.Image.Image", text: str) -> "PIL.Image.Image":
    """Draw a semi-transparent label bar at the bottom of *img*."""
    from PIL import Image, ImageDraw, ImageFont

    img = img.copy().convert("RGBA")
    w, h = img.size
    bar_h = max(32, h // 14)
    font_size = max(14, bar_h - 8)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Semi-transparent dark bar
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 160))

    # Try to load a decent font; fall back to PIL's built-in
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

    # Centre text in bar
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (w - text_w) // 2
    y = h - bar_h + (bar_h - text_h) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 230))

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


# ---------------------------------------------------------------------------
# Crossfade helper
# ---------------------------------------------------------------------------

def _crossfade_frames(
    src: "PIL.Image.Image",
    dst: "PIL.Image.Image",
    steps: int,
) -> "list[PIL.Image.Image]":
    """Return *steps* intermediate frames blending from *src* to *dst*."""
    from PIL import Image

    frames = []
    src_arr = src.convert("RGB")
    dst_arr = dst.convert("RGB")
    for i in range(1, steps + 1):
        alpha = i / (steps + 1)
        blended = Image.blend(src_arr, dst_arr, alpha)
        frames.append(blended)
    return frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an animated APNG CVD demo (Original → Simulated → Corrected).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to input image (JPEG, PNG, WebP, etc.)",
    )
    parser.add_argument(
        "--deficiency", default="deuteranopia",
        choices=["protanopia", "protan", "deuteranopia", "deutan", "tritanopia", "tritan"],
        help="CVD deficiency type to simulate/correct (default: deuteranopia)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output APNG path (default: samples/cvd-demo.png)",
    )
    parser.add_argument(
        "--max-width", type=int, default=800,
        help="Resize image to at most this width, preserving aspect ratio (default: 800)",
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
        "--crossfade-steps", type=int, default=8,
        help="Number of intermediate frames for crossfade transition (default: 8)",
    )
    parser.add_argument(
        "--labels", action=argparse.BooleanOptionalAction, default=True,
        help="Overlay text labels on each frame (default: on)",
    )
    args = parser.parse_args()

    # Lazy import — requires [image] extra
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

    output_path = Path(args.output) if args.output else Path("samples/cvd-demo.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    deficiency = args.deficiency
    label_map = {
        "protanopia": "Protanopia (red-blind)",
        "protan":     "Protanopia (red-blind)",
        "deuteranopia": "Deuteranopia (green-blind)",
        "deutan":     "Deuteranopia (green-blind)",
        "tritanopia": "Tritanopia (blue-blind)",
        "tritan":     "Tritanopia (blue-blind)",
    }
    deficiency_label = label_map[deficiency]

    print(f"Loading:    {input_path}")
    original = Image.open(input_path).convert("RGB")

    # Resize if needed
    if args.max_width and original.width > args.max_width:
        ratio = args.max_width / original.width
        new_size = (args.max_width, int(original.height * ratio))
        original = original.resize(new_size, Image.LANCZOS)
        print(f"Resized to: {new_size[0]}×{new_size[1]}")

    print(f"Simulating: {deficiency} …")
    simulated = simulate_cvd_image(input_path, deficiency)
    if simulated.size != original.size:
        simulated = simulated.resize(original.size, Image.LANCZOS)

    print(f"Correcting: {deficiency} …")
    corrected = correct_cvd_image(input_path, deficiency)
    if corrected.size != original.size:
        corrected = corrected.resize(original.size, Image.LANCZOS)

    # Apply labels
    if args.labels:
        frame_original  = _add_label(original,  "Original")
        frame_simulated = _add_label(simulated, f"Simulated · {deficiency_label}")
        frame_corrected = _add_label(corrected, f"Corrected · {deficiency_label}")
    else:
        frame_original  = original.convert("RGB")
        frame_simulated = simulated.convert("RGB")
        frame_corrected = corrected.convert("RGB")

    # Convert duration to milliseconds for Pillow's 'duration' parameter
    hold_ms = int(args.duration * 1000)
    # Crossfade transitions use shorter per-frame duration so total ≈ 0.4 s
    transition_ms = max(30, 400 // max(args.crossfade_steps, 1))

    # Build frame list with durations
    # Each element: (PIL.Image, duration_ms)
    content_frames: list[tuple[Image.Image, int]] = [
        (frame_original,  hold_ms),
        (frame_simulated, hold_ms),
        (frame_corrected, hold_ms),
    ]

    sequence: list[tuple[Image.Image, int]] = []
    for i, (frame, dur) in enumerate(content_frames):
        sequence.append((frame, dur))
        # Add crossfade to next frame (wraps: last → first)
        if args.transition == "crossfade":
            next_frame = content_frames[(i + 1) % len(content_frames)][0]
            for blend in _crossfade_frames(frame, next_frame, args.crossfade_steps):
                sequence.append((blend, transition_ms))

    frames   = [f for f, _ in sequence]
    durations = [d for _, d in sequence]

    print(f"Saving:     {output_path}  ({len(frames)} frames)")
    frames[0].save(
        output_path,
        format="PNG",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,          # loop forever
        optimize=False,  # keep lossless
    )

    size_kb = output_path.stat().st_size // 1024
    print(f"Done!       {size_kb} KB")
    print()
    print("Embed in README.md with:")
    rel = output_path.as_posix()
    print(f'  ![CVD Demo]({rel})')

    return 0


if __name__ == "__main__":
    sys.exit(main())
