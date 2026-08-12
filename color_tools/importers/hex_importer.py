"""
HEX palette importer.

Imports simple text palettes containing one hexadecimal RGB color per line.

Supported color forms:

    RRGGBB
    #RRGGBB

Blank lines are ignored.

Comment lines beginning with ``# `` or ``;`` are ignored. A line containing a
bare ``#RRGGBB`` value is treated as a color rather than as a comment.

Because the HEX format contains no palette metadata or color names, imported
colors use their hexadecimal value as the ColorRecord name.

Example:

    FF0000
    00FF00
    #0000FF

becomes:

    #FF0000
    #00FF00
    #0000FF
"""

from __future__ import annotations

import re
from pathlib import Path

from color_tools.exporters.palette_export_data import PaletteExportData
from color_tools.exporters.palette_metadata import PaletteMetadata
from color_tools.importers.base import (
    ImporterMetadata,
    PaletteImporter,
)
from color_tools.importers.registry import register_importer


_HEX_RE = re.compile(
    r"^#?(?P<hex>[0-9A-Fa-f]{6})$"
)


@register_importer
class HexImporter(PaletteImporter):
    """
    Import plain-text hexadecimal RGB palette files.

    The format is intentionally minimal:

        - One RGB color per line.
        - Six hexadecimal digits.
        - Leading ``#`` is accepted but not required.
        - Blank lines are ignored.
        - Comment lines beginning with ``# `` or ``;`` are ignored.

    No palette-level metadata is available in the format.
    """

    @property
    def metadata(self) -> ImporterMetadata:
        """Return metadata describing the HEX importer."""
        return ImporterMetadata(
            name="hex",
            description="Plain hexadecimal RGB palette",
            file_extensions=(
                "hex",
            ),
            is_binary=False,
        )

    def _can_import_impl(
        self,
        input_path: Path,
    ) -> bool:
        """
        Determine whether a file appears to contain a HEX palette.

        The file is considered valid if every nonblank, noncomment line is a
        six-digit hexadecimal RGB value and at least one color is present.

        Args:
            input_path:
                Candidate HEX palette file.

        Returns:
            True if the file appears to be a HEX palette.
        """
        try:
            lines = input_path.read_text(
                encoding="utf-8-sig",
            ).splitlines()

        except (
            OSError,
            UnicodeError,
        ):
            return False

        found_color = False

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                continue

            if self._is_comment(
                line
            ):
                continue

            if _HEX_RE.fullmatch(
                line
            ) is None:
                return False

            found_color = True

        return found_color

    def _import_palette_impl(
        self,
        input_path: Path,
    ) -> PaletteExportData:
        """
        Parse a HEX palette file.

        Args:
            input_path:
                HEX palette file.

        Returns:
            PaletteExportData containing imported colors.

        Raises:
            ValueError:
                If the file contains malformed color entries or no colors.
        """
        try:
            lines = input_path.read_text(
                encoding="utf-8-sig",
            ).splitlines()

        except UnicodeError as exc:
            raise ValueError(
                f"Unable to decode HEX palette '{input_path}' as UTF-8"
            ) from exc

        colors = []

        for line_number, raw_line in enumerate(
            lines,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            if self._is_comment(
                line
            ):
                continue

            match = _HEX_RE.fullmatch(
                line
            )

            if match is None:
                raise ValueError(
                    "Invalid HEX palette entry on "
                    f"line {line_number}: {raw_line!r}"
                )

            hex_value = match.group(
                "hex"
            ).upper()

            rgb = (
                int(
                    hex_value[0:2],
                    16,
                ),
                int(
                    hex_value[2:4],
                    16,
                ),
                int(
                    hex_value[4:6],
                    16,
                ),
            )

            color_name = (
                f"#{hex_value}"
            )

            colors.append(
                self._make_color_record(
                    rgb=rgb,
                    name=color_name,
                    source=input_path.name,
                )
            )

        if not colors:
            raise ValueError(
                "HEX palette contains no colors"
            )

        return PaletteExportData(
            colors=colors,
            metadata=PaletteMetadata(),
        )

    @staticmethod
    def _is_comment(
        line: str,
    ) -> bool:
        """
        Return whether a line is a HEX palette comment.

        ``#RRGGBB`` must remain a valid color, so only a hash followed by
        whitespace is treated as a comment.

        Examples:

            # FF0000      -> comment
            # palette     -> comment
            ; palette     -> comment
            #FF0000       -> color

        Args:
            line:
                Stripped input line.

        Returns:
            True if the line is a comment.
        """
        if line.startswith(";"):
            return True

        return (
            len(line) > 1
            and line[0] == "#"
            and line[1].isspace()
        )