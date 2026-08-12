"""
JASC PAL palette importer.

Imports JASC-PAL text palette files into PaletteExportData.

JASC PAL format:

    JASC-PAL
    0100
    <color count>
    R G B
    R G B
    ...

Example:

    JASC-PAL
    0100
    3
    255 0 0
    0 255 0
    0 0 255

The format does not contain color names or palette-level metadata, so imported
colors use their hexadecimal value as the ColorRecord name.
"""

from __future__ import annotations

from pathlib import Path

from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers.base import (
    ImporterMetadata,
    PaletteImporter,
)
from color_tools.importers.registry import register_importer


@register_importer
class JascPalImporter(PaletteImporter):
    """
    Import JASC-PAL (.pal) palette files.

    JASC PAL is a simple text format consisting of:

        - ``JASC-PAL`` signature
        - ``0100`` version
        - Declared color count
        - One ``R G B`` entry per color

    The ``.pal`` extension is shared with RIFF PAL, so this importer detects its
    format by checking the JASC-PAL header.
    """

    @property
    def metadata(self) -> ImporterMetadata:
        """Return metadata describing the JASC PAL importer."""
        return ImporterMetadata(
            name="jasc_pal",
            description="JASC-PAL palette",
            file_extensions=(
                "pal",
            ),
            is_binary=False,
        )

    def _can_import_impl(
        self,
        input_path: Path,
    ) -> bool:
        """
        Detect JASC PAL by its required text header.

        Args:
            input_path:
                Candidate .pal file.

        Returns:
            True if the file begins with the JASC-PAL signature and version.
        """
        try:
            with input_path.open(
                "r",
                encoding="ascii",
            ) as file:
                signature = (
                    file.readline()
                    .strip()
                )

                version = (
                    file.readline()
                    .strip()
                )

        except (
            OSError,
            UnicodeError,
        ):
            return False

        return (
            signature == "JASC-PAL"
            and version == "0100"
        )

    def _import_palette_impl(
        self,
        input_path: Path,
    ) -> PaletteExportData:
        """
        Parse a JASC-PAL palette file.

        Args:
            input_path:
                JASC PAL file to import.

        Returns:
            PaletteExportData containing imported colors.

        Raises:
            ValueError:
                If the file is malformed, contains an unsupported version,
                has an invalid color count, or contains invalid RGB entries.
        """
        try:
            lines = input_path.read_text(
                encoding="ascii",
            ).splitlines()

        except UnicodeError as exc:
            raise ValueError(
                f"Unable to decode JASC PAL palette '{input_path}' as ASCII"
            ) from exc

        if len(lines) < 3:
            raise ValueError(
                "Invalid JASC PAL palette: file is too short"
            )

        signature = lines[0].strip()

        if signature != "JASC-PAL":
            raise ValueError(
                "Invalid JASC PAL palette: expected 'JASC-PAL' header"
            )

        version = lines[1].strip()

        if version != "0100":
            raise ValueError(
                f"Unsupported JASC PAL version: {version!r}"
            )

        count_text = lines[2].strip()

        try:
            declared_count = int(
                count_text
            )

        except ValueError as exc:
            raise ValueError(
                f"Invalid JASC PAL color count: {count_text!r}"
            ) from exc

        if declared_count < 0:
            raise ValueError(
                "JASC PAL color count must not be negative"
            )

        color_lines = lines[3:]

        if len(color_lines) != declared_count:
            raise ValueError(
                "JASC PAL color count does not match file contents: "
                f"declared {declared_count}, found {len(color_lines)}"
            )

        colors = []

        for index, raw_line in enumerate(
            color_lines,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                raise ValueError(
                    "Invalid empty JASC PAL color entry at "
                    f"palette index {index}"
                )

            parts = line.split()

            if len(parts) != 3:
                raise ValueError(
                    "Invalid JASC PAL color entry at "
                    f"palette index {index}: {raw_line!r}"
                )

            try:
                rgb = (
                    int(parts[0]),
                    int(parts[1]),
                    int(parts[2]),
                )

            except ValueError as exc:
                raise ValueError(
                    "Invalid JASC PAL RGB value at "
                    f"palette index {index}: {raw_line!r}"
                ) from exc

            if any(
                channel < 0 or channel > 255
                for channel in rgb
            ):
                raise ValueError(
                    "JASC PAL RGB values must be between 0 and 255 at "
                    f"palette index {index}: {rgb}"
                )

            color_name = (
                f"#{rgb[0]:02X}"
                f"{rgb[1]:02X}"
                f"{rgb[2]:02X}"
            )

            colors.append(
                self._make_color_record(
                    rgb=rgb,
                    name=color_name,
                    source=input_path.name,
                )
            )

        return PaletteExportData(
            colors=colors,
            metadata=PaletteMetadata(),
        )