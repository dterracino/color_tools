"""
Pure-stdlib PNG writer for palette strips and LUT textures.

This module provides a minimal PNG encoder that writes RGB (or RGBA) color
strips without any external dependencies.  It is intentionally limited to
the use case of palette output — a horizontal strip of solid-color swatches.

It is used as the fallback path when Pillow is not installed, and as the
sole implementation in the palette_lut_exporter (which is part of the base
package and must not require Pillow).

For full image I/O (loading, resizing, compositing) use Pillow via the
``color_tools[image]`` optional extra.

Usage
-----
    >>> from color_tools.image._png_writer import SimplePNGWriter
    >>> colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    >>> writer = SimplePNGWriter(colors, swatch_width=1, swatch_height=1)
    >>> writer.save("lut.png")

    >>> # Wider swatches for a visible preview strip
    >>> writer = SimplePNGWriter(colors, swatch_width=32, swatch_height=32)
    >>> writer.save("palette_preview.png")
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


class SimplePNGWriter:
    """
    Minimal pure-Python PNG writer for palette color strips.

    Writes a horizontal strip image: each palette color occupies
    ``swatch_width`` pixels wide × ``swatch_height`` pixels tall.
    Every row is identical — the strip is uniform in color vertically.

    Output is always 8-bit RGB (no alpha).  This is sufficient for LUT
    textures and palette preview images.

    Attributes:
        colors: List of (R, G, B) tuples with values in 0–255.
        swatch_width: Pixel width of each color swatch (default 1).
        swatch_height: Pixel height of the strip (default 1).

    Example:
        >>> from color_tools.image._png_writer import SimplePNGWriter
        >>> nes = [(0, 0, 0), (102, 102, 102), ...]  # list of RGB tuples
        >>> # True LUT: 1 pixel per color, 1 row tall
        >>> SimplePNGWriter(nes, swatch_width=1, swatch_height=1).save("nes.png")
        >>> # Preview strip: 16px wide swatches, 16px tall
        >>> SimplePNGWriter(nes, swatch_width=16, swatch_height=16).save("nes_preview.png")
    """

    # PNG spec constants
    _SIGNATURE   = b'\x89PNG\r\n\x1a\n'
    _BIT_DEPTH   = 8
    _COLOR_TYPE  = 2   # RGB
    _COMPRESSION = 0   # deflate
    _FILTER      = 0   # adaptive (we use filter byte 0 per row = None)
    _INTERLACE   = 0   # no interlace

    def __init__(
        self,
        colors: list[tuple[int, int, int]],
        swatch_width: int = 1,
        swatch_height: int = 1,
    ) -> None:
        if not colors:
            raise ValueError("colors must not be empty")
        if swatch_width < 1:
            raise ValueError("swatch_width must be >= 1")
        if swatch_height < 1:
            raise ValueError("swatch_height must be >= 1")

        self.colors       = colors
        self.swatch_width = swatch_width
        self.swatch_height = swatch_height
        self.width  = len(colors) * swatch_width
        self.height = swatch_height

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        """Write the PNG to *path*.  Creates parent directories if needed."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(self._signature())
            f.write(self._ihdr())
            f.write(self._idat())
            f.write(self._iend())

    def to_bytes(self) -> bytes:
        """Return the PNG file contents as a bytes object (no file I/O)."""
        return (
            self._signature()
            + self._ihdr()
            + self._idat()
            + self._iend()
        )

    # ------------------------------------------------------------------
    # Private PNG chunk helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc    = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    def _signature(self) -> bytes:
        return self._SIGNATURE

    def _ihdr(self) -> bytes:
        data = struct.pack(
            ">IIBBBBB",
            self.width,
            self.height,
            self._BIT_DEPTH,
            self._COLOR_TYPE,
            self._COMPRESSION,
            self._FILTER,
            self._INTERLACE,
        )
        return self._chunk(b"IHDR", data)

    def _idat(self) -> bytes:
        # Build one scanline: filter byte 0 + pixel data
        row = bytearray()
        for r, g, b in self.colors:
            pixel = bytes([r & 0xFF, g & 0xFF, b & 0xFF])
            row.extend(pixel * self.swatch_width)

        scanline = bytes([0]) + bytes(row)   # filter byte 0 = None
        image_data = scanline * self.height

        return self._chunk(b"IDAT", zlib.compress(image_data))

    def _iend(self) -> bytes:
        return self._chunk(b"IEND", b"")
