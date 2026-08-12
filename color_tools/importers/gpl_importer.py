"""
GIMP Palette (GPL) importer.

Imports standard GIMP .gpl palette files into PaletteExportData.

Supported palette-level fields:

    - Name
    - Columns

The importer additionally understands the optional metadata comments emitted by
color_tools' GPL exporter:

    # Author: ...
    # Description: ...
    # Tags: ...

These comments are additive and do not interfere with ordinary GPL files from
GIMP or other applications.

Example GPL file:

    GIMP Palette
    Name: Autumn
    Columns: 4
    #
    # Author: Example Author
    # Description: Warm autumn palette
    # Tags: warm, autumn
    255 127  80    Coral
    139  69  19    Saddle Brown
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


_COLOR_LINE_RE = re.compile(
    r"^\s*"
    r"(?P<r>\d+)"
    r"\s+"
    r"(?P<g>\d+)"
    r"\s+"
    r"(?P<b>\d+)"
    r"(?:\s+(?P<name>.*?))?"
    r"\s*$"
)


@register_importer
class GPLImporter(PaletteImporter):
    """
    Import GIMP Palette (.gpl) files.

    Standard GPL metadata is preserved where possible. color_tools-specific
    Author, Description, and Tags comments are also recovered when present.
    """

    @property
    def metadata(self) -> ImporterMetadata:
        """Return metadata describing the GPL importer."""
        return ImporterMetadata(
            name="gpl",
            description="GIMP Palette",
            file_extensions=(
                "gpl",
            ),
            is_binary=False,
        )

    def _can_import_impl(
        self,
        input_path: Path,
    ) -> bool:
        """
        Detect a GPL file by its required header.

        Args:
            input_path:
                Candidate GPL file.

        Returns:
            True if the first line is ``GIMP Palette``.
        """
        try:
            with input_path.open(
                "r",
                encoding="utf-8-sig",
            ) as file:
                first_line = (
                    file.readline()
                    .rstrip("\r\n")
                )

        except (
            OSError,
            UnicodeError,
        ):
            return False

        return (
            first_line
            == "GIMP Palette"
        )

    def _import_palette_impl(
        self,
        input_path: Path,
    ) -> PaletteExportData:
        """
        Parse a GIMP Palette file.

        Args:
            input_path:
                GPL palette file.

        Returns:
            PaletteExportData containing imported colors and metadata.

        Raises:
            ValueError:
                If the file is not valid GPL or contains malformed palette
                entries.
        """
        try:
            text = input_path.read_text(
                encoding="utf-8-sig",
            )

        except UnicodeError as exc:
            raise ValueError(
                f"Unable to decode GPL palette '{input_path}' as UTF-8"
            ) from exc

        lines = text.splitlines()

        if not lines:
            raise ValueError(
                "GPL palette is empty"
            )

        if lines[0].strip() != "GIMP Palette":
            raise ValueError(
                "Invalid GPL palette: expected 'GIMP Palette' header"
            )

        palette_name = ""
        author = ""
        description = ""
        columns: int | None = None
        tags: tuple[str, ...] = ()

        colors = []

        for line_number, raw_line in enumerate(
            lines[1:],
            start=2,
        ):
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                (
                    author,
                    description,
                    tags,
                ) = self._parse_metadata_comment(
                    line=line,
                    author=author,
                    description=description,
                    tags=tags,
                )

                continue

            if line.lower().startswith(
                "name:"
            ):
                palette_name = (
                    line
                    .partition(":")[2]
                    .strip()
                )

                continue

            if line.lower().startswith(
                "columns:"
            ):
                value = (
                    line
                    .partition(":")[2]
                    .strip()
                )

                try:
                    columns = int(
                        value
                    )

                except ValueError as exc:
                    raise ValueError(
                        "Invalid GPL Columns value on "
                        f"line {line_number}: {value!r}"
                    ) from exc

                if (
                    columns < 0
                    or columns > 255
                ):
                    raise ValueError(
                        "GPL Columns value must be between "
                        f"0 and 255 on line {line_number}"
                    )

                continue

            match = _COLOR_LINE_RE.match(
                raw_line
            )

            if match is None:
                raise ValueError(
                    "Invalid GPL palette entry on "
                    f"line {line_number}: {raw_line!r}"
                )

            rgb = (
                int(
                    match.group("r")
                ),
                int(
                    match.group("g")
                ),
                int(
                    match.group("b")
                ),
            )

            if any(
                channel < 0
                or channel > 255
                for channel in rgb
            ):
                raise ValueError(
                    "GPL RGB values must be between 0 and 255 "
                    f"on line {line_number}: {rgb}"
                )

            color_name = (
                match.group("name")
                or ""
            ).strip()

            if not color_name:
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
            metadata=PaletteMetadata(
                name=palette_name,
                author=author,
                description=description,
                columns=columns,
                tags=tags,
            ),
        )

    @staticmethod
    def _parse_metadata_comment(
        *,
        line: str,
        author: str,
        description: str,
        tags: tuple[str, ...],
    ) -> tuple[
        str,
        str,
        tuple[str, ...],
    ]:
        """
        Parse color_tools metadata stored in GPL comments.

        Unknown comments are ignored because GPL permits arbitrary comments.

        Args:
            line:
                Complete comment line including the leading ``#``.

            author:
                Current author value.

            description:
                Current description value.

            tags:
                Current tags value.

        Returns:
            Updated ``(author, description, tags)`` tuple.
        """
        comment = (
            line
            .removeprefix("#")
            .strip()
        )

        if not comment:
            return (
                author,
                description,
                tags,
            )

        key, separator, value = (
            comment.partition(":")
        )

        if not separator:
            return (
                author,
                description,
                tags,
            )

        key = (
            key
            .strip()
            .lower()
        )

        value = value.strip()

        if key == "author":
            author = value

        elif key == "description":
            description = value

        elif key == "tags":
            tags = tuple(
                item.strip()
                for item in value.split(",")
                if item.strip()
            )

        return (
            author,
            description,
            tags,
        )