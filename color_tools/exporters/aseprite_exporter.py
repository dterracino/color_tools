"""Aseprite native palette export as a single-frame swatch document.

Writes the subset described by https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md:
an sRGB profile, named palette entries, a background layer, and a compressed cel.
The .aseprite extension deliberately distinguishes this format from Adobe .ase.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools._color_utils import validate_rgb
from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord


@dataclass(slots=True)
class AsepriteExportOptions(ExportOptionsBase):
    """Control Aseprite palette serialization.

    include_transparent defaults to True: prepend a named transparent-black
    entry at index zero without modifying input records. Supplied colors shift
    by one index and remain opaque. Set False to export only supplied colors.
    The added entry counts toward grid layout and the 256-entry indexed limit.
    """

    include_transparent: bool = True

    def __post_init__(self) -> None:
        if type(self.include_transparent) is not bool:
            raise TypeError("include_transparent must be a bool")


@register_exporter
class AsepriteExporter(PaletteExporter):
    """Export ordered RGB swatches with a transparent entry by default.

    Up to 256 total entries use indexed pixels; larger palettes use RGBA pixels.
    Accepts 1-65,534 input colors by default, or 1-65,535 with transparency off.
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
            options_type=AsepriteExportOptions,
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

    def _export_colors_with_options_impl(
        self, colors: list[ColorRecord], output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        assert isinstance(options, AsepriteExportOptions)
        return self._write_palette(
            colors, output_path, name="", columns=None,
            include_transparent=options.include_transparent,
        )

    def _export_palette_with_options_impl(
        self, palette: PaletteExportData, output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        assert isinstance(options, AsepriteExportOptions)
        return self._write_palette(
            palette.colors, output_path,
            name=palette.metadata.name, columns=palette.metadata.columns,
            include_transparent=options.include_transparent,
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
        *, name: str, columns: int | None, include_transparent: bool = True,
    ) -> str:
        """Validate and serialize all data before opening the destination."""
        count = len(colors) + int(include_transparent)
        if not colors or count > 65535:
            maximum = 65534 if include_transparent else 65535
            raise ValueError(f"Aseprite export requires 1-{maximum:,} input colors")
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
        if include_transparent:
            entries.extend(struct.pack("<H4B", 1, 0, 0, 0, 0))
            entries.extend(self._string("Transparent"))
            rgba.extend(bytes(4))
        for color in colors:
            validate_rgb(color.rgb)
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
