#!/usr/bin/env python3
"""
generate_palette_textures.py
============================
Utility that reads color_tools palette JSON files and generates 1-D palette
texture images (PNG strips) that can be loaded as GPU textures.

Each output image is a 1×N (or N×1) strip of colours that can be sampled in
a shader with a 1-D or 2-D texture lookup.  This provides an alternative
rendering path to the hard-coded GLSL palette arrays in the shader files:
a shader can simply do a nearest-sample lookup against the texture instead of
iterating over all colours.

Usage
-----
  # Generate all supported palettes
  python generate_palette_textures.py

  # Generate a specific palette
  python generate_palette_textures.py --palette nes

  # Specify custom output directory
  python generate_palette_textures.py --output /tmp/palette_textures

  # Also print GLSL snippet for each palette
  python generate_palette_textures.py --glsl

Output files
------------
  palette_textures/nes.png        – 54×1 pixel strip
  palette_textures/gameboy.png    –  4×1 pixel strip
  palette_textures/cga16.png      – 16×1 pixel strip
  palette_textures/pico8.png      – 16×1 pixel strip
  ...

GLSL texture-lookup pattern
----------------------------
  // Bind the generated texture to unit 1
  uniform sampler2D u_palette;
  uniform int       u_palette_size;

  vec3 nearest_palette(vec3 color) {
      float best_dist = 1e9;
      int   best_idx  = 0;
      for (int i = 0; i < u_palette_size; i++) {
          vec2  uv    = vec2((float(i) + 0.5) / float(u_palette_size), 0.5);
          vec3  pal   = texture(u_palette, uv).rgb;
          vec3  delta = color - pal;
          float dist  = dot(delta, delta);
          if (dist < best_dist) { best_dist = dist; best_idx = i; }
      }
      vec2 best_uv = vec2((float(best_idx) + 0.5) / float(u_palette_size), 0.5);
      return texture(u_palette, best_uv).rgb;
  }

Where should shaders live in the library?
-----------------------------------------
  When the shader collection grows, a sensible home would be:

    color_tools/shaders/
      palette/
        nes.frag
        gameboy.frag
        cga16.frag
        pico8.frag
        ...
      common/
        quad.vert
        palette_lookup.glsl   (shared include / snippet)
      README.md               (documents each shader)

  This keeps them alongside the palette JSON data they are derived from and
  makes it trivial to install with the package (add a MANIFEST.in glob).
  For now all shaders live in demos/shaders/ as requested.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Pillow and numpy are required.  Run:  pip install -r requirements.txt")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEMO_DIR    = Path(__file__).parent
REPO_ROOT   = DEMO_DIR.parent
PALETTE_DIR = REPO_ROOT / "color_tools" / "data" / "palettes"

# Palettes to generate by default
DEFAULT_PALETTES = [
    "nes",
    "gameboy",
    "cga16",
    "pico8",
    "commodore64",
    "ega16",
    "sms",
    "apple2",
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_palette_json(name: str) -> list[dict]:
    """Load palette JSON data for the given palette name."""
    path = PALETTE_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Palette '{name}' not found at {path}\n"
            f"Available: {', '.join(p.stem for p in PALETTE_DIR.glob('*.json'))}"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected array of colours in {path}")
    return data


def palette_to_rgb_array(data: list[dict]) -> np.ndarray:
    """Convert a palette JSON list to a numpy uint8 array of shape (N, 3)."""
    colours = []
    for entry in data:
        r, g, b = entry["rgb"]
        colours.append((int(r), int(g), int(b)))
    return np.array(colours, dtype=np.uint8)


def save_palette_texture(
    name: str,
    output_dir: Path,
    *,
    height: int = 1,
    verbose: bool = True,
) -> Path:
    """
    Load a palette and save it as a 1-D texture PNG strip.

    Args:
        name:       Palette name (matches JSON filename without extension)
        output_dir: Directory to write the PNG into
        height:     Pixel height of the strip (default 1, can use >1 for preview)
        verbose:    Print status

    Returns:
        Path of the written PNG file
    """
    data    = load_palette_json(name)
    colours = palette_to_rgb_array(data)
    n       = len(colours)

    # Create a (height × N) image by repeating the strip vertically
    strip = np.tile(colours[np.newaxis, :, :], (height, 1, 1))  # (H, N, 3)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{name}.png"
    Image.fromarray(strip, mode="RGB").save(out_path)

    if verbose:
        print(f"  {name:20s} → {out_path}  ({n} colours, {strip.shape[1]}×{strip.shape[0]}px)")
    return out_path


def print_glsl_snippet(name: str) -> None:
    """Print the GLSL hard-coded palette array for the given palette."""
    data = load_palette_json(name)
    n    = len(data)
    print(f"\n// {name.upper()} palette ({n} colours) — GLSL vec3 array")
    print(f"const int   {name.upper()}_SIZE = {n};")
    print(f"const vec3  {name.upper()}_PALETTE[{n}] = vec3[{n}](")
    for i, entry in enumerate(data):
        r, g, b = [v / 255.0 for v in entry["rgb"]]
        comma   = "," if i < n - 1 else " "
        hex_str = entry.get("hex", "")
        col_name = entry.get("name", "")
        print(f"    vec3({r:.4f}, {g:.4f}, {b:.4f}){comma}  // {col_name} {hex_str}")
    print(");")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 1-D palette texture PNGs from color_tools JSON palettes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--palette",
        nargs="+",
        default=DEFAULT_PALETTES,
        metavar="NAME",
        help="One or more palette names to generate (default: all common palettes)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_DIR / "palette_textures",
        metavar="DIR",
        help="Output directory for PNG textures (default: demos/palette_textures/)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=16,
        help="Strip height in pixels; use >1 for visible preview (default: 16)",
    )
    parser.add_argument(
        "--glsl",
        action="store_true",
        help="Also print GLSL palette array snippet for each palette",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available palettes and exit",
    )

    args = parser.parse_args()

    if args.list:
        palettes = sorted(p.stem for p in PALETTE_DIR.glob("*.json"))
        print("Available palettes:")
        for p in palettes:
            data = load_palette_json(p)
            print(f"  {p:25s} ({len(data)} colours)")
        return

    # Deduplicate while preserving order
    palettes = list(dict.fromkeys(args.palette))

    print(f"Generating {len(palettes)} palette texture(s) → {args.output}/\n")
    for name in palettes:
        try:
            save_palette_texture(name, args.output, height=args.height)
            if args.glsl:
                print_glsl_snippet(name)
        except FileNotFoundError as exc:
            print(f"  WARNING: {exc}")
        except Exception as exc:
            print(f"  ERROR generating {name}: {exc}")

    print(f"\nDone. {len(palettes)} texture(s) written to {args.output}/")


if __name__ == "__main__":
    main()
