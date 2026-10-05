"""Aseprite native palette export as a single-frame swatch document.

Writes the subset described by https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md:
an sRGB profile, named palette entries, a background layer, and a compressed cel.
The .aseprite extension deliberately distinguishes this format from Adobe .ase.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools._color_utils import _validate_rgb
from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@register_exporter
class AsepriteExporter(PaletteExporter):
    """Export 1-65,535 ordered opaque RGB swatches in native Aseprite format.

    Up to 256 colors use indexed pixels; larger palettes use RGBA pixels.
    Names and duplicate colors are preserved. Palette metadata supplies the
    layer name and grid columns, not a native palette-title field. Other
    metadata is not represented. None/zero columns produce a horizontal strip.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Describe the dependency-free .aseprite color exporter."""
        return ExporterMetadata(
            name="aseprite",
            description="Aseprite native palette swatch document",
            file_extension="aseprite",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=True,
        )

    def _export_colors_impl(
        self, colors: list[ColorRecord], output_path: Path | str | None,
    ) -> str:
        return self._write_palette(colors, output_path, name="", columns=None)

    def _export_palette_impl(
        self, palette: PaletteExportData, output_path: Path | str | None,
    ) -> str:
        return self._write_palette(
            palette.colors, output_path,
            name=palette.metadata.name, columns=palette.metadata.columns,
        )

    @staticmethod
    def _string(value: str) -> bytes:
        """Encode the format's WORD-length UTF-8 string without truncation."""
        encoded = value.encode("utf-8")
        if len(encoded) > 65535:
            raise ValueError("Aseprite names must not exceed 65,535 UTF-8 bytes")
        return struct.pack("<H", len(encoded)) + encoded

    @staticmethod
    def _chunk(kind: int, payload: bytes) -> bytes:
        """Prefix a chunk with its total byte size and type."""
        size = 6 + len(payload)
        if size > 0xFFFFFFFF:
            raise ValueError("Aseprite chunk exceeds its 32-bit size field")
        return struct.pack("<IH", size, kind) + payload

    def _write_palette(
        self, colors: list[ColorRecord], output_path: Path | str | None,
        *, name: str, columns: int | None,
    ) -> str:
        """Validate and serialize all data before opening the destination."""
        count = len(colors)
        if not 1 <= count <= 65535:
            raise ValueError("Aseprite export requires 1-65,535 colors")
        if columns is not None and (type(columns) is not int or columns < 0):
            raise ValueError("Aseprite columns must be a nonnegative integer")
        path = Path(output_path if output_path is not None else self.generate_filename("colors"))
        if path.suffix.lower() != ".aseprite":
            raise ValueError("Aseprite exports require the .aseprite extension, not .ase")
        width = min(columns, count) if columns else count
        height = (count + width - 1) // width
        depth = 8 if count <= 256 else 32

        entries = bytearray(struct.pack("<III8x", count, 0, count - 1))
        rgba = bytearray()
        for color in colors:
            _validate_rgb(color.rgb)
            pixel = bytes((*color.rgb, 255))
            entries.extend(struct.pack("<H", 1 if color.name else 0))
            entries.extend(pixel)
            if color.name:
                entries.extend(self._string(color.name))
            rgba.extend(pixel)

        padding = width * height - count
        if depth == 8:
            pixels = bytes(range(count)) + bytes(padding)
        else:
            pixels = bytes(rgba) + bytes(rgba[:4]) * padding

        profile = self._chunk(0x2007, struct.pack("<HHI8x", 1, 0, 0))
        palette_chunk = self._chunk(0x2019, bytes(entries))
        # Background avoids treating the first indexed swatch as transparent.
        layer = self._chunk(
            0x2004,
            struct.pack("<6HB3x", 15, 0, 0, 0, 0, 0, 255)
            + self._string(name or path.stem),
        )
        cel = self._chunk(
            0x2005,
            struct.pack("<HhhBHh5xHH", 0, 0, 0, 255, 2, 0, width, height)
            + zlib.compress(pixels),
        )
        chunks = profile + palette_chunk + layer + cel
        frame_size = 16 + len(chunks)
        file_size = 128 + frame_size
        if file_size > 0xFFFFFFFF:
            raise ValueError("Aseprite file exceeds its 32-bit size field")
        frame = struct.pack("<IHHH2xI", frame_size, 0xF1FA, 4, 100, 4) + chunks
        header = bytearray(128)
        struct.pack_into(
            "<I5HIH", header, 0,
            file_size, 0xA5E0, 1, width, height, depth, 1, 100,
        )
        struct.pack_into("<HBBhhHH", header, 32, count, 1, 1, 0, 0, 16, 16)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(header) + frame)
        return str(path)
