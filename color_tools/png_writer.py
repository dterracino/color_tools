"""
Minimal PNG writer for repeated-row RGB images.

Encodes solid, block, gradient, and equal-width swatch rows as PNG files. Uses
only the standard library (``zlib`` and ``struct``), so it works without Pillow
or numpy.

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


def _validate_dimension(name: str, value: int, maximum: int) -> None:
    """Validate one public image dimension."""
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    if value > maximum:
        raise ValueError(f"image {name} {value} exceeds PNG limit of {maximum}")


def _freeze_colors(colors: Sequence[RGB | list[int]]) -> tuple[RGB, ...]:
    """Validate colors and return an immutable copy."""
    if not colors:
        raise ValueError("colors must not be empty")

    for index, color in enumerate(colors):
        try:
            validate_rgb(color)
        except ValueError as error:
            raise ValueError(f"colors[{index}]: {error}") from error

    return tuple((color[0], color[1], color[2]) for color in colors)


class SimplePNGWriter:
    """
    Write a repeated horizontal RGB row as a PNG.

    Direct construction creates an equal-width strip: the image is
    ``len(colors) * swatch_width`` pixels wide and ``swatch_height`` pixels
    tall. The named constructors create solid, deterministic block, or encoded-
    sRGB gradient rows. Every row in the resulting image is identical.

    Attributes:
        colors: Immutable validated (R, G, B) tuples, in left-to-right order
        swatch_width: Direct-constructor swatch width; 1 for generated rows
        swatch_height: Image height
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

    # Bound complete-image work even though repeated rows are streamed to zlib.
    # At this limit, decoded RGB pixel data is 48 MiB.
    _MAX_PIXELS: Final = 2**24

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
                image exceeds the PNG dimension or pixel-count limits
        """
        frozen_colors = _freeze_colors(colors)
        _validate_dimension("swatch_width", swatch_width, self._MAX_DIMENSION)
        _validate_dimension("swatch_height", swatch_height, self._MAX_DIMENSION)

        width = len(frozen_colors) * swatch_width
        _validate_dimension("width", width, self._MAX_DIMENSION)
        self._validate_image_size(width, swatch_height)
        pixel_row = b"".join(bytes(color) * swatch_width for color in frozen_colors)
        self._initialize(
            colors=frozen_colors,
            width=width,
            height=swatch_height,
            swatch_width=swatch_width,
            pixel_row=pixel_row,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def from_solid(
        cls,
        color: RGB | list[int],
        width: int,
        height: int,
    ) -> SimplePNGWriter:
        """Create a solid-color image with the requested dimensions."""
        colors = _freeze_colors([color])
        cls._validate_dimensions(width, height)
        return cls._from_pixel_row(colors, bytes(colors[0]) * width, width, height)

    @classmethod
    def from_blocks(
        cls,
        colors: Sequence[RGB | list[int]],
        width: int,
        height: int,
    ) -> SimplePNGWriter:
        """
        Create source-order vertical color blocks spanning the requested width.

        Block widths differ by at most one pixel. Remainder pixels are assigned
        to the earliest blocks, and every component receives at least one pixel.
        """
        frozen_colors = _freeze_colors(colors)
        cls._validate_dimensions(width, height)
        if width < len(frozen_colors):
            raise ValueError(
                "width must be at least the number of colors so no block is omitted"
            )

        base_width, remainder = divmod(width, len(frozen_colors))
        pixel_row = b"".join(
            bytes(color) * (base_width + (index < remainder))
            for index, color in enumerate(frozen_colors)
        )
        return cls._from_pixel_row(frozen_colors, pixel_row, width, height)

    @classmethod
    def from_gradient(
        cls,
        colors: Sequence[RGB | list[int]],
        width: int,
        height: int,
    ) -> SimplePNGWriter:
        """Create an encoded-sRGB gradient through equally spaced color stops."""
        frozen_colors = _freeze_colors(colors)
        cls._validate_dimensions(width, height)
        if len(frozen_colors) == 1:
            return cls._from_pixel_row(
                frozen_colors, bytes(frozen_colors[0]) * width, width, height
            )
        if width == 1:
            raise ValueError("multi-color gradients require a width of at least 2")

        pixel_row = bytearray()
        segment_count = len(frozen_colors) - 1
        for x in range(width):
            position = x * segment_count / (width - 1)
            segment = min(int(position), segment_count - 1)
            fraction = position - segment
            start = frozen_colors[segment]
            end = frozen_colors[segment + 1]
            pixel_row.extend(
                round(start[channel] + (end[channel] - start[channel]) * fraction)
                for channel in range(3)
            )
        return cls._from_pixel_row(
            frozen_colors, bytes(pixel_row), width, height
        )

    def to_bytes(self) -> bytes:
        """Encode the image and return the complete PNG file as bytes."""
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
    @classmethod
    def _validate_dimensions(cls, width: int, height: int) -> None:
        """Validate dimensions and the complete-image resource bound."""
        _validate_dimension("width", width, cls._MAX_DIMENSION)
        _validate_dimension("height", height, cls._MAX_DIMENSION)
        cls._validate_image_size(width, height)

    @classmethod
    def _validate_image_size(cls, width: int, height: int) -> None:
        """Reject images above the decoded-pixel resource limit."""
        pixels = width * height
        if pixels > cls._MAX_PIXELS:
            raise ValueError(
                f"image has {pixels} pixels; maximum is {cls._MAX_PIXELS}"
            )

    @classmethod
    def _from_pixel_row(
        cls,
        colors: tuple[RGB, ...],
        pixel_row: bytes,
        width: int,
        height: int,
    ) -> SimplePNGWriter:
        """Build an instance from one already validated RGB pixel row."""
        writer = cls.__new__(cls)
        writer._initialize(
            colors=colors,
            width=width,
            height=height,
            swatch_width=1,
            pixel_row=pixel_row,
        )
        return writer

    def _initialize(
        self,
        *,
        colors: tuple[RGB, ...],
        width: int,
        height: int,
        swatch_width: int,
        pixel_row: bytes,
    ) -> None:
        """Store the common immutable layout state for every construction path."""
        self.colors = colors
        self.swatch_width = swatch_width
        self.swatch_height = height
        self.width = width
        self.height = height
        self._pixel_row = pixel_row

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
        """Return one filter-none scanline."""
        return bytes([self._SCANLINE_FILTER_NONE]) + self._pixel_row

    def _idat_data(self) -> bytes:
        """Compress identical scanlines incrementally without copying the image."""
        compressor = zlib.compressobj(self._ZLIB_LEVEL)
        scanline = self._scanline()
        chunks: list[bytes] = []
        for _ in range(self.height):
            chunk = compressor.compress(scanline)
            if chunk:
                chunks.append(chunk)
        chunks.append(compressor.flush())
        return b"".join(chunks)
