"""
RIFF PAL palette importer.

Imports RIFF PAL binary palette files into PaletteExportData.

RIFF PAL format structure:

    RIFF
    <file size>
    PAL
    data
    <chunk size>
    <LOGPALETTE data>

The LOGPALETTE payload inside the ``data`` chunk is:

    WORD palVersion
    WORD palNumEntries
    PALETTEENTRY[palNumEntries]

Each PALETTEENTRY is:

    BYTE peRed
    BYTE peGreen
    BYTE peBlue
    BYTE peFlags

The format does not contain color names or palette-level metadata, so imported
colors use their hexadecimal value as the ColorRecord name.
"""

from __future__ import annotations

import struct
from pathlib import Path

from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers.base import (
    ImporterMetadata,
    PaletteImporter,
)
from color_tools.importers.registry import register_importer


@register_importer
class RiffPalImporter(PaletteImporter):
    """
    Import RIFF PAL (.pal) palette files.

    RIFF PAL is a binary RIFF container whose form type is ``PAL `` and whose
    palette data is stored in a ``data`` chunk.

    The ``.pal`` extension is shared with JASC PAL, so this importer detects
    its format by checking the RIFF and PAL signatures.
    """

    @property
    def metadata(self) -> ImporterMetadata:
        """Return metadata describing the RIFF PAL importer."""
        return ImporterMetadata(
            name="riff_pal",
            description="RIFF PAL palette",
            file_extensions=(
                "pal",
            ),
            is_binary=True,
        )

    def _can_import_impl(
        self,
        input_path: Path,
    ) -> bool:
        """
        Detect RIFF PAL by its binary RIFF header and PAL form type.

        Args:
            input_path:
                Candidate .pal file.

        Returns:
            True if the file appears to be a RIFF PAL palette.
        """
        try:
            header = input_path.read_bytes()[:12]

        except OSError:
            return False

        if len(header) < 12:
            return False

        return (
            header[0:4] == b"RIFF"
            and header[8:12] == b"PAL "
        )

    def _import_palette_impl(
        self,
        input_path: Path,
    ) -> PaletteExportData:
        """
        Parse a RIFF PAL palette file.

        Args:
            input_path:
                RIFF PAL file to import.

        Returns:
            PaletteExportData containing imported colors.

        Raises:
            ValueError:
                If the file is malformed or does not contain a valid RIFF PAL
                data chunk.
        """
        try:
            data = input_path.read_bytes()

        except OSError as exc:
            raise ValueError(
                f"Unable to read RIFF PAL palette '{input_path}'"
            ) from exc

        if len(data) < 12:
            raise ValueError(
                "Invalid RIFF PAL palette: file is too short"
            )

        if data[0:4] != b"RIFF":
            raise ValueError(
                "Invalid RIFF PAL palette: expected 'RIFF' header"
            )

        riff_size = struct.unpack(
            "<I",
            data[4:8],
        )[0]

        if data[8:12] != b"PAL ":
            raise ValueError(
                "Invalid RIFF PAL palette: expected 'PAL ' form type"
            )

        expected_total_size = riff_size + 8

        if expected_total_size > len(data):
            raise ValueError(
                "Invalid RIFF PAL palette: RIFF size exceeds file length"
            )

        data_chunk = self._find_data_chunk(
            data
        )

        if data_chunk is None:
            raise ValueError(
                "Invalid RIFF PAL palette: missing 'data' chunk"
            )

        colors = self._parse_logpalette(
            data_chunk=data_chunk,
            source=input_path.name,
        )

        return PaletteExportData(
            colors=colors,
            metadata=PaletteMetadata(),
        )

    @staticmethod
    def _find_data_chunk(
        data: bytes,
    ) -> bytes | None:
        """
        Locate the RIFF ``data`` chunk.

        Args:
            data:
                Complete RIFF file bytes.

        Returns:
            The raw ``data`` chunk payload, or None if no such chunk exists.

        Raises:
            ValueError:
                If a chunk header or chunk size is malformed.
        """
        offset = 12
        file_length = len(data)

        while offset + 8 <= file_length:
            chunk_id = data[
                offset : offset + 4
            ]

            chunk_size = struct.unpack(
                "<I",
                data[offset + 4 : offset + 8],
            )[0]

            chunk_data_start = offset + 8
            chunk_data_end = (
                chunk_data_start + chunk_size
            )

            if chunk_data_end > file_length:
                raise ValueError(
                    "Invalid RIFF PAL palette: chunk extends beyond file size"
                )

            if chunk_id == b"data":
                return data[
                    chunk_data_start:chunk_data_end
                ]

            offset = chunk_data_end

            if chunk_size % 2 == 1:
                offset += 1

        return None

    def _parse_logpalette(
        self,
        *,
        data_chunk: bytes,
        source: str,
    ) -> list:
        """
        Parse a LOGPALETTE structure from a RIFF data chunk.

        Args:
            data_chunk:
                Raw bytes of the RIFF ``data`` chunk.

            source:
                Source filename for constructed ColorRecord instances.

        Returns:
            Imported ColorRecord list.

        Raises:
            ValueError:
                If the LOGPALETTE structure is malformed.
        """
        if len(data_chunk) < 4:
            raise ValueError(
                "Invalid RIFF PAL palette: data chunk is too short"
            )

        version, color_count = struct.unpack(
            "<HH",
            data_chunk[:4],
        )

        if version != 0x0300:
            raise ValueError(
                f"Unsupported RIFF PAL version: 0x{version:04X}"
            )

        expected_size = 4 + color_count * 4

        if len(data_chunk) < expected_size:
            raise ValueError(
                "Invalid RIFF PAL palette: data chunk is shorter than the "
                "declared palette size"
            )

        colors = []

        for index in range(color_count):
            entry_offset = 4 + index * 4

            red, green, blue, _flags = (
                data_chunk[
                    entry_offset : entry_offset + 4
                ]
            )

            rgb = (
                red,
                green,
                blue,
            )

            color_name = (
                f"#{red:02X}"
                f"{green:02X}"
                f"{blue:02X}"
            )

            colors.append(
                self._make_color_record(
                    rgb=rgb,
                    name=color_name,
                    source=source,
                )
            )

        return colors