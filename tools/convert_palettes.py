#!/usr/bin/env python3
"""Convert bundled palette arrays to the versioned indexed document schema."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NotRequired, TypedDict, cast


class _Metadata(TypedDict):
    """Metadata authored for one bundled palette."""

    name: str
    description: str
    release_year: NotRequired[int]


SYSTEM_METADATA: dict[str, _Metadata] = {
    "amstrad-cpc": {"name": "Amstrad CPC", "description": "An 8-bit home computer family developed by Amstrad.", "release_year": 1984},
    "apple2": {"name": "Apple II", "description": "An 8-bit home computer introduced by Apple Computer.", "release_year": 1977},
    "bbc-micro": {"name": "BBC Micro", "description": "An 8-bit microcomputer designed by Acorn Computers for the BBC Computer Literacy Project.", "release_year": 1981},
    "cga4": {"name": "CGA 4-Color", "description": "A four-color mode of IBM's Color Graphics Adapter.", "release_year": 1981},
    "cga16": {"name": "CGA 16-Color", "description": "The full RGBI color set of IBM's Color Graphics Adapter.", "release_year": 1981},
    "colecovision": {"name": "ColecoVision", "description": "A home video game console released by Coleco.", "release_year": 1982},
    "commodore64": {"name": "Commodore 64", "description": "An 8-bit home computer released by Commodore.", "release_year": 1982},
    "crayola": {"name": "Crayola Colors", "description": "A collection of named crayon colors used by Crayola."},
    "ega16": {"name": "EGA 16-Color", "description": "The standard 16-color set of IBM's Enhanced Graphics Adapter.", "release_year": 1984},
    "ega64": {"name": "EGA 64-Color", "description": "The complete color domain of IBM's Enhanced Graphics Adapter.", "release_year": 1984},
    "gameboy": {"name": "GB Studio", "description": "The four-color authoring environment used to create Game Boy games with GB Studio."},
    "gameboy-dmg": {"name": "Nintendo Game Boy", "description": "The original monochrome handheld game console released by Nintendo.", "release_year": 1989},
    "gameboy-light": {"name": "Nintendo Game Boy Light", "description": "A backlit Game Boy model released by Nintendo in Japan.", "release_year": 1998},
    "gameboy-pocket": {"name": "Nintendo Game Boy Pocket", "description": "A smaller monochrome Game Boy model released by Nintendo.", "release_year": 1996},
    "intellivision": {"name": "Intellivision", "description": "A home video game console released by Mattel Electronics.", "release_year": 1979},
    "macintosh": {"name": "Apple Macintosh", "description": "The original Macintosh personal computer introduced by Apple Computer.", "release_year": 1984},
    "msx1": {"name": "MSX1", "description": "The first generation of the MSX home computer standard.", "release_year": 1983},
    "nes": {"name": "Nintendo Entertainment System", "description": "An 8-bit home video game console released by Nintendo.", "release_year": 1983},
    "pico8": {"name": "PICO-8", "description": "A fantasy console for creating, sharing, and playing small games.", "release_year": 2015},
    "sg-1000": {"name": "Sega SG-1000", "description": "Sega's first home video game console.", "release_year": 1983},
    "sms": {"name": "Sega Master System", "description": "A home video game console released by Sega.", "release_year": 1986},
    "tandy16": {"name": "Tandy 16-Color", "description": "The 16-color set used by enhanced Tandy computer graphics modes."},
    "ti-99-4a": {"name": "TI-99/4A", "description": "A 16-bit home computer released by Texas Instruments.", "release_year": 1981},
    "tic80": {"name": "TIC-80", "description": "A free and open-source fantasy console for making small games."},
    "vga": {"name": "VGA", "description": "IBM's Video Graphics Array display standard.", "release_year": 1987},
    "vic-20": {"name": "Commodore VIC-20", "description": "An 8-bit home computer released by Commodore.", "release_year": 1980},
    "virtualboy": {"name": "Nintendo Virtual Boy", "description": "A stereoscopic tabletop video game console released by Nintendo.", "release_year": 1995},
    "web": {"name": "Web-Safe Colors", "description": "A color set designed for consistent display by early web browsers."},
    "zx-spectrum": {"name": "ZX Spectrum", "description": "An 8-bit home computer developed by Sinclair Research.", "release_year": 1982},
}


_ARRAY_PATTERN = re.compile(
    r'("(?:rgb|hsl|lab|lch)": )\[\s*([^\]]+?)\s*\]',
    re.MULTILINE,
)


def _extract_colors(data: object, source: Path) -> list[object]:
    """Extract colors from the legacy array or current indexed document."""
    if isinstance(data, list):
        return cast(list[object], data)
    if isinstance(data, dict):
        document = cast(dict[object, object], data)
        palette = document.get("palette")
        if isinstance(palette, dict):
            colors = cast(dict[object, object], palette).get("colors")
            if isinstance(colors, list):
                return cast(list[object], colors)
    raise ValueError(f"Unsupported palette structure in {source}")


def _compact_color_arrays(text: str) -> str:
    """Keep small color-coordinate arrays readable on one line."""
    def replace(match: re.Match[str]) -> str:
        values: object = json.loads(f"[{match.group(2)}]")
        return f"{match.group(1)}{json.dumps(values)}"

    return _ARRAY_PATTERN.sub(replace, text)


def build_palette_document(
    palette_id: str,
    colors: list[object],
) -> dict[str, object]:
    """Build a schema-version-1 document for a registered bundled palette."""
    metadata = SYSTEM_METADATA.get(palette_id)
    if metadata is None:
        raise ValueError(f"No approved metadata for palette {palette_id!r}")
    return {
        "schema_version": 1,
        "metadata": {"id": palette_id, **metadata},
        "palette": {"type": "indexed", "colors": colors},
    }


def serialize_palette_document(document: dict[str, object]) -> str:
    """Serialize a palette document with compact color-coordinate arrays."""
    serialized = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    return _compact_color_arrays(serialized)


def convert_palette_file(path: Path) -> None:
    """Convert one registered bundled palette to schema version 1."""
    data: object = json.loads(path.read_text(encoding="utf-8"))
    colors = _extract_colors(data, path)
    document = build_palette_document(path.stem, colors)
    path.write_text(
        serialize_palette_document(document),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Converted {path.name}: {len(colors)} colors")


def main() -> None:
    """Convert specified palettes, or every registered bundled palette."""
    if len(sys.argv) > 1:
        paths = [Path(argument) for argument in sys.argv[1:]]
    else:
        palette_dir = Path(__file__).parents[1] / "color_tools" / "data" / "palettes"
        paths = [palette_dir / f"{palette_id}.json" for palette_id in SYSTEM_METADATA]

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        convert_palette_file(path)


if __name__ == "__main__":
    main()
