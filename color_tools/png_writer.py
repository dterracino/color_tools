"""
Minimal PNG writer for color swatch strips.

Encodes a list of RGB colors as a horizontal strip of swatches and writes it as
a PNG file. Uses only the standard library (``zlib`` and ``struct``), so it works
without Pillow or numpy.

This module belongs to the base package, not the optional image package.
It must not import Pillow, NumPy, or modules that require them.

Output format: 8-bit RGB (truecolor), no alpha, no interlacing, scanline filter
"None", with an ``sRGB`` chunk marking the pixels as sRGB.

Example:
--------
    >>> from color_tools.png_writer import SimplePNGWriter
    >>> writer = SimplePNGWriter(
    ...     [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
    ...     swatch_width=32,
    ...     swatch_height=32,
    ... )
    >>> writer.width, writer.height
    (96, 32)
    >>> writer.save("rgb_swatches.png")
    >>> png_bytes = writer.to_bytes()
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from ._color_utils import validate_rgb

RGB = tuple[int, int, int]


class SimplePNGWriter:
    """
    Write a horizontal strip of solid-color swatches as a PNG.

    The image is ``len(colors) * swatch_width`` pixels wide and ``swatch_height``
    pixels tall. Each color fills one ``swatch_width`` x ``swatch_height`` block.

    Attributes:
        colors: Immutable validated (R, G, B) tuples, in left-to-right order
        swatch_width: Width of each swatch in pixels
        swatch_height: Height of each swatch (and of the image) in pixels
        width: Total image width in pixels
        height: Total image height in pixels
    """

    # ------------------------------------------------------------------
    # PNG spec constants (https://www.w3.org/TR/png/)
    # ------------------------------------------------------------------
    _SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"

    # Chunk type codes
    _CHUNK_IHDR: Final = b"IHDR"
    _CHUNK_IDAT: Final = b"IDAT"
    _CHUNK_IEND: Final = b"IEND"
    # sRGB marks the pixels as sRGB so viewers render them consistently.
    # NOTE: The spec also suggests writing gAMA and cHRM chunks alongside sRGB
    # for older decoders that don't understand sRGB. If compatibility issues
    # ever show up, add those chunks here (they go between IHDR and IDAT).
    _CHUNK_SRGB: Final = b"sRGB"

    # IHDR fields
    _BIT_DEPTH: Final = 8
    _COLOR_TYPE_RGB: Final = 2        # Truecolor: one R, G, B sample per pixel
    _COMPRESSION_METHOD: Final = 0    # Deflate (the only method defined)
    _FILTER_METHOD: Final = 0         # Adaptive filtering (the only method defined)
    _INTERLACE_NONE: Final = 0        # No interlacing

    # Per-scanline filter type byte (distinct from the IHDR filter *method*)
    _SCANLINE_FILTER_NONE: Final = 0

    # sRGB rendering intent: 0 perceptual, 1 relative colorimetric,
    # 2 saturation, 3 absolute colorimetric
    _SRGB_INTENT_PERCEPTUAL: Final = 0

    # Width and height are unsigned 32-bit values capped at 2^31 - 1 by the spec
    _MAX_DIMENSION: Final = 2**31 - 1

    # Not a spec value: zlib compression level (9 = smallest output)
    _ZLIB_LEVEL: Final = 9

    def __init__(
        self,
        colors: Sequence[RGB | list[int]],
        swatch_width: int = 1,
        swatch_height: int = 1,
    ) -> None:
        """
        Args:
            colors: RGB tuples/lists, each channel a built-in int in 0-255.
                Colors are copied into immutable tuples.
            swatch_width: Positive built-in integer width of each swatch.
            swatch_height: Positive built-in integer height of each swatch.

        Raises:
            ValueError: If colors is empty, a color fails strict RGB validation,
                a swatch dimension is not a positive built-in integer, or the resulting
                image exceeds the PNG dimension limit
        """
        if not colors:
            raise ValueError("colors must not be empty")
        if type(swatch_width) is not int or swatch_width < 1:
            raise ValueError("swatch_width must be a positive integer")
        if type(swatch_height) is not int or swatch_height < 1:
            raise ValueError("swatch_height must be a positive integer")

        for index, color in enumerate(colors):
            try:
                validate_rgb(color)
            except ValueError as error:
                raise ValueError(f"colors[{index}]: {error}") from error

        self.colors: tuple[RGB, ...] = tuple(
            (color[0], color[1], color[2]) for color in colors
        )
        self.swatch_width = swatch_width
        self.swatch_height = swatch_height
        self.width: int = len(self.colors) * swatch_width
        self.height: int = swatch_height

        if self.width > self._MAX_DIMENSION:
            raise ValueError(
                f"image width {self.width} exceeds PNG limit of {self._MAX_DIMENSION}"
            )
        if self.height > self._MAX_DIMENSION:
            raise ValueError(
                f"image height {self.height} exceeds PNG limit of {self._MAX_DIMENSION}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def to_bytes(self) -> bytes:
        """Encode the swatch strip and return the complete PNG file as bytes."""
        return b"".join(
            (
                self._SIGNATURE,
                self._chunk(self._CHUNK_IHDR, self._ihdr_data()),
                self._chunk(self._CHUNK_SRGB, self._srgb_data()),
                self._chunk(self._CHUNK_IDAT, self._idat_data()),
                self._chunk(self._CHUNK_IEND, b""),
            )
        )

    def save(self, path: str | Path) -> None:
        """
        Write the PNG to a file, creating missing parent directories.

        Args:
            path: Destination file path (overwritten if it exists)

        Raises:
            OSError: If creating directories or writing the file fails.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(self.to_bytes())

    # ------------------------------------------------------------------
    # Chunk construction
    # ------------------------------------------------------------------
    @staticmethod
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Build one chunk: length + type + data + CRC (CRC covers type and data)."""
        crc = zlib.crc32(chunk_type + data)
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    def _ihdr_data(self) -> bytes:
        """IHDR payload: dimensions plus the fixed format fields."""
        return struct.pack(
            ">IIBBBBB",
            self.width,
            self.height,
            self._BIT_DEPTH,
            self._COLOR_TYPE_RGB,
            self._COMPRESSION_METHOD,
            self._FILTER_METHOD,
            self._INTERLACE_NONE,
        )

    def _srgb_data(self) -> bytes:
        """sRGB payload: a single rendering-intent byte."""
        return bytes([self._SRGB_INTENT_PERCEPTUAL])

    def _scanline(self) -> bytes:
        """One image row: filter byte, then each color repeated swatch_width times."""
        pixels = b"".join(bytes(color) * self.swatch_width for color in self.colors)
        return bytes([self._SCANLINE_FILTER_NONE]) + pixels

    def _idat_data(self) -> bytes:
        """IDAT payload: every row is identical, so build one and repeat it."""
        return zlib.compress(self._scanline() * self.height, self._ZLIB_LEVEL)
