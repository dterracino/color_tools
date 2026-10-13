"""Generate the small built-in retro palettes with reviewed source tables.

The hardware palettes are kept as explicit ordered definitions so their source
order and representation choices are reviewable. Derived color spaces are
calculated with the production conversion functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from color_tools.conversions import lab_to_lch, rgb_to_hex, rgb_to_hsl, rgb_to_lab


type RGB = tuple[int, int, int]
type ColorDefinition = tuple[str, RGB]


class _PaletteRecord(TypedDict):
    """Serialized shape of one built-in palette color."""

    name: str
    hex: str
    rgb: list[int]
    hsl: list[float]
    lab: list[float]
    lch: list[float]


# Acorn BBC Microcomputer System User Guide, physical colors 0 through 7.
_BBC_MICRO: tuple[ColorDefinition, ...] = (
    ("black", (0, 0, 0)),
    ("red", (255, 0, 0)),
    ("green", (0, 255, 0)),
    ("yellow", (255, 255, 0)),
    ("blue", (0, 0, 255)),
    ("magenta", (255, 0, 255)),
    ("cyan", (0, 255, 255)),
    ("white", (255, 255, 255)),
)

# Sinclair documents the normal/bright hardware states, not canonical sRGB.
# D7/FF is the conventional 85%/100% display approximation used here. Bright
# black is visually identical to black and is intentionally not duplicated.
_ZX_SPECTRUM: tuple[ColorDefinition, ...] = (
    ("black", (0, 0, 0)),
    ("blue", (0, 0, 215)),
    ("red", (215, 0, 0)),
    ("magenta", (215, 0, 215)),
    ("green", (0, 215, 0)),
    ("cyan", (0, 215, 215)),
    ("yellow", (215, 215, 0)),
    ("white", (215, 215, 215)),
    ("bright blue", (0, 0, 255)),
    ("bright red", (255, 0, 0)),
    ("bright magenta", (255, 0, 255)),
    ("bright green", (0, 255, 0)),
    ("bright cyan", (0, 255, 255)),
    ("bright yellow", (255, 255, 0)),
    ("bright white", (255, 255, 255)),
)

# Amstrad CPC firmware colors 0 through 26. The hardware's off/half/full RGB
# levels are represented as 0/128/255 in sRGB files.
_AMSTRAD_CPC: tuple[ColorDefinition, ...] = (
    ("black", (0, 0, 0)),
    ("blue", (0, 0, 128)),
    ("bright blue", (0, 0, 255)),
    ("red", (128, 0, 0)),
    ("magenta", (128, 0, 128)),
    ("mauve", (128, 0, 255)),
    ("bright red", (255, 0, 0)),
    ("purple", (255, 0, 128)),
    ("bright magenta", (255, 0, 255)),
    ("green", (0, 128, 0)),
    ("cyan", (0, 128, 128)),
    ("sky blue", (0, 128, 255)),
    ("yellow", (128, 128, 0)),
    ("white", (128, 128, 128)),
    ("pastel blue", (128, 128, 255)),
    ("orange", (255, 128, 0)),
    ("pink", (255, 128, 128)),
    ("pastel magenta", (255, 128, 255)),
    ("bright green", (0, 255, 0)),
    ("sea green", (0, 255, 128)),
    ("bright cyan", (0, 255, 255)),
    ("lime", (128, 255, 0)),
    ("pastel green", (128, 255, 128)),
    ("pastel cyan", (128, 255, 255)),
    ("bright yellow", (255, 255, 0)),
    ("pastel yellow", (255, 255, 128)),
    ("bright white", (255, 255, 255)),
)

# TIC-80's official default SWEETIE-16 palette in index order.
_TIC80: tuple[ColorDefinition, ...] = (
    ("black", (26, 28, 44)),
    ("purple", (93, 39, 93)),
    ("red", (177, 62, 83)),
    ("orange", (239, 125, 87)),
    ("yellow", (255, 205, 117)),
    ("light green", (167, 240, 112)),
    ("green", (56, 183, 100)),
    ("dark green", (37, 113, 121)),
    ("dark blue", (41, 54, 111)),
    ("blue", (59, 93, 201)),
    ("light blue", (65, 166, 246)),
    ("cyan", (115, 239, 247)),
    ("white", (244, 244, 244)),
    ("light gray", (148, 176, 194)),
    ("gray", (86, 108, 134)),
    ("dark gray", (51, 60, 87)),
)

# GB Studio's fixed four-color authoring palette, ordered darkest to lightest.
_GAMEBOY: tuple[ColorDefinition, ...] = (
    ("darkest", (7, 24, 33)),
    ("dark", (48, 104, 80)),
    ("light", (134, 192, 108)),
    ("lightest", (224, 248, 207)),
)

# SameBoy's GB_PALETTE_DMG screen approximation. SameBoy also defines a fifth
# LCD-off color, which is not one of the four addressable pixel intensities.
_GAMEBOY_DMG: tuple[ColorDefinition, ...] = (
    ("darkest", (8, 24, 16)),
    ("dark", (57, 97, 57)),
    ("light", (132, 165, 99)),
    ("lightest", (198, 222, 140)),
)

# An explicit neutral rendering of the Pocket's four monochrome intensities.
# These values also match SameBoy's GB_PALETTE_GREY table.
_GAMEBOY_POCKET: tuple[ColorDefinition, ...] = (
    ("darkest", (0, 0, 0)),
    ("dark", (85, 85, 85)),
    ("light", (170, 170, 170)),
    ("lightest", (255, 255, 255)),
)

# SameBoy's GB_PALETTE_GBL backlit-screen approximation. Its fifth LCD-off
# color is intentionally omitted for the same reason as the DMG value.
_GAMEBOY_LIGHT: tuple[ColorDefinition, ...] = (
    ("darkest", (10, 28, 21)),
    ("dark", (53, 120, 98)),
    ("light", (86, 180, 149)),
    ("lightest", (127, 226, 195)),
)

# Shared TMS9918-family display table, ordered by hardware color code 1-15.
# These values apply a gamma 1.6 CRT-style transform to RGB reconstructed from
# the TI luminance and color-difference levels. Code 0 is transparency/backdrop
# behavior and therefore has no palette record.
_TMS9918_CRT: tuple[ColorDefinition, ...] = (
    ("black", (0, 0, 0)),
    ("medium green", (10, 173, 30)),
    ("light green", (52, 200, 76)),
    ("dark blue", (43, 45, 227)),
    ("light blue", (81, 75, 251)),
    ("dark red", (189, 41, 37)),
    ("cyan", (30, 226, 239)),
    ("medium red", (251, 44, 43)),
    ("light red", (255, 95, 76)),
    ("dark yellow", (189, 162, 43)),
    ("light yellow", (215, 180, 84)),
    ("dark green", (10, 140, 24)),
    ("magenta", (175, 50, 154)),
    ("gray", (178, 178, 178)),
    ("white", (255, 255, 255)),
)

# Intellivision STIC color codes 0-F. These values are a vivid CRT-style
# representation, ordered by the AY-3-8900 hardware color code rather than by
# hue or luminance.
_INTELLIVISION: tuple[ColorDefinition, ...] = (
    ("black", (12, 0, 5)),
    ("blue", (0, 45, 255)),
    ("red", (255, 62, 0)),
    ("tan", (201, 212, 100)),
    ("dark green", (0, 120, 15)),
    ("green", (0, 167, 32)),
    ("yellow", (250, 234, 39)),
    ("white", (255, 252, 255)),
    ("gray", (167, 168, 168)),
    ("cyan", (90, 203, 255)),
    ("orange", (255, 166, 0)),
    ("brown", (60, 88, 0)),
    ("magenta", (255, 50, 118)),
    ("light blue", (189, 149, 255)),
    ("yellow-green", (108, 205, 48)),
    ("purple", (200, 26, 125)),
)

# VIC-I color codes 0-F. The selected CRT-style RGB values were published in
# shade-pair order, so they are remapped here to the MOS 6560/6561 register
# order documented by Commodore and used by VIC-20 emulators.
_VIC20: tuple[ColorDefinition, ...] = (
    ("black", (0, 0, 0)),
    ("white", (255, 255, 255)),
    ("red", (119, 45, 38)),
    ("cyan", (133, 212, 220)),
    ("purple", (168, 95, 180)),
    ("green", (85, 158, 74)),
    ("blue", (66, 52, 139)),
    ("yellow", (189, 204, 113)),
    ("orange", (168, 115, 74)),
    ("light orange", (233, 178, 135)),
    ("pink", (182, 104, 98)),
    ("light cyan", (197, 255, 255)),
    ("light purple", (233, 157, 245)),
    ("light green", (146, 223, 135)),
    ("light blue", (126, 112, 202)),
    ("light yellow", (255, 255, 176)),
)


PALETTES: dict[str, tuple[ColorDefinition, ...]] = {
    "amstrad-cpc": _AMSTRAD_CPC,
    "bbc-micro": _BBC_MICRO,
    "colecovision": _TMS9918_CRT,
    "gameboy": _GAMEBOY,
    "gameboy-dmg": _GAMEBOY_DMG,
    "gameboy-light": _GAMEBOY_LIGHT,
    "gameboy-pocket": _GAMEBOY_POCKET,
    "intellivision": _INTELLIVISION,
    "msx1": _TMS9918_CRT,
    "sg-1000": _TMS9918_CRT,
    "ti-99-4a": _TMS9918_CRT,
    "tic80": _TIC80,
    "vic-20": _VIC20,
    "zx-spectrum": _ZX_SPECTRUM,
}


def _rounded(values: tuple[float, float, float]) -> list[float]:
    """Round a three-component color value for serialized palette data."""
    return [round(value, 1) for value in values]


def build_palette(definitions: tuple[ColorDefinition, ...]) -> list[_PaletteRecord]:
    """Build serialized palette records from ordered RGB definitions."""
    records: list[_PaletteRecord] = []
    for name, rgb in definitions:
        lab = rgb_to_lab(rgb)
        records.append(
            {
                "name": name,
                "hex": rgb_to_hex(rgb).lower(),
                "rgb": list(rgb),
                "hsl": _rounded(rgb_to_hsl(rgb)),
                "lab": _rounded(lab),
                "lch": _rounded(lab_to_lch(lab)),
            }
        )
    return records


def _serialize_palette(records: list[_PaletteRecord]) -> str:
    """Serialize records with compact numeric arrays matching bundled data."""
    blocks: list[str] = []
    for record in records:
        blocks.append(
            "\n".join(
                (
                    "  {",
                    f'    "name": {json.dumps(record["name"])},',
                    f'    "hex": {json.dumps(record["hex"])},',
                    f'    "rgb": {json.dumps(record["rgb"])},',
                    f'    "hsl": {json.dumps(record["hsl"])},',
                    f'    "lab": {json.dumps(record["lab"])},',
                    f'    "lch": {json.dumps(record["lch"])}',
                    "  }",
                )
            )
        )
    return "[\n" + ",\n".join(blocks) + "\n]\n"


def write_palettes(output_dir: Path) -> tuple[Path, ...]:
    """Generate the reviewed palette files in *output_dir* and return paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for palette_name, definitions in PALETTES.items():
        output_path = output_dir / f"{palette_name}.json"
        output_path.write_text(
            _serialize_palette(build_palette(definitions)),
            encoding="utf-8",
            newline="\n",
        )
        written.append(output_path)
    return tuple(written)


def main() -> None:
    """Generate the additional built-in retro palettes."""
    output_dir = Path(__file__).parents[1] / "color_tools" / "data" / "palettes"
    for path in write_palettes(output_dir):
        print(f"Generated {path.name}")


if __name__ == "__main__":
    main()
