"""
Microsoft RIFF PAL palette exporter.

Exports colors to the binary Microsoft RIFF palette format.

RIFF PAL files use the Resource Interchange File Format (RIFF) container with
a ``PAL `` form type and a ``data`` chunk containing a Windows LOGPALETTE:

    RIFF
        <size>
        PAL
        data
            <size>
            WORD palVersion
            WORD palNumEntries
            PALETTEENTRY entries[...]

Each PALETTEENTRY contains four bytes:

    red, green, blue, flags

The palette version is written as ``0x0300`` and entry flags are set to zero.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@register_exporter
class RiffPalExporter(PaletteExporter):
    """
    Export color palettes in Microsoft RIFF PAL format.

    RIFF PAL is a binary Windows palette format based on the RIFF container.
    It stores an ordered sequence of 8-bit RGB palette entries.

    Color names and alpha values are not supported by this exporter.
    """

    PALETTE_VERSION = 0x0300

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the RIFF PAL exporter."""
        return ExporterMetadata(
            name="riff_pal",
            description="Microsoft RIFF palette format",
            file_extension="pal",
            supports_colors=True,
            supports_filaments=False,
            is_binary=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors to Microsoft RIFF PAL format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination PAL file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported PAL file as a string.

        Raises:
            ValueError:
                If more than 65,535 colors are supplied. The RIFF PAL entry
                count is stored as an unsigned 16-bit value.
        """
        if len(colors) > 0xFFFF:
            raise ValueError(
                "RIFF PAL supports at most 65,535 palette entries"
            )

        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        palette_data = self._build_palette_data(colors)
        data_chunk = self._build_chunk(b"data", palette_data)

        # RIFF size counts everything after the size field:
        #
        #     4 bytes form type ("PAL ")
        #   + complete child chunks
        riff_size = 4 + len(data_chunk)

        with path.open("wb") as file:
            file.write(b"RIFF")
            file.write(struct.pack("<I", riff_size))
            file.write(b"PAL ")
            file.write(data_chunk)

        return str(path)

    def _build_palette_data(
        self,
        colors: list[ColorRecord],
    ) -> bytes:
        """
        Build the LOGPALETTE payload stored in the RIFF ``data`` chunk.

        Args:
            colors:
                Color records to serialize.

        Returns:
            Binary LOGPALETTE payload.
        """
        data = bytearray()

        data.extend(
            struct.pack(
                "<HH",
                self.PALETTE_VERSION,
                len(colors),
            )
        )

        for color in colors:
            r, g, b = color.rgb

            data.extend(
                struct.pack(
                    "<BBBB",
                    r,
                    g,
                    b,
                    0,
                )
            )

        return bytes(data)

    @staticmethod
    def _build_chunk(
        chunk_id: bytes,
        data: bytes,
    ) -> bytes:
        """
        Build a RIFF chunk.

        RIFF chunks contain a four-byte identifier, a little-endian unsigned
        32-bit data size, and the chunk payload. Odd-sized payloads are padded
        to a WORD boundary.

        Args:
            chunk_id:
                Four-byte RIFF chunk identifier.

            data:
                Chunk payload.

        Returns:
            Complete encoded RIFF chunk.

        Raises:
            ValueError:
                If ``chunk_id`` is not exactly four bytes.
        """
        if len(chunk_id) != 4:
            raise ValueError(
                "RIFF chunk identifiers must be exactly four bytes"
            )

        chunk = bytearray()
        chunk.extend(chunk_id)
        chunk.extend(struct.pack("<I", len(data)))
        chunk.extend(data)

        if len(data) & 1:
            chunk.append(0)

        return bytes(chunk)