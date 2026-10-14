"""
HEX palette exporter.

Exports colors as one lowercase six-digit hexadecimal RGB value per line by
default. Python callers may request uppercase output with ``HexExportOptions``.

Format example:

    ff0000
    00ff00
    0000ff

The leading ``#`` is omitted to match the common Lospec-style HEX palette
representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from color_tools.conversions import rgb_to_hex
from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@dataclass(slots=True)
class HexExportOptions(ExportOptionsBase):
    """Configure letter casing in plain-text HEX palette output."""

    uppercase: bool = False

    def __post_init__(self) -> None:
        """Validate HEX export options."""
        if type(self.uppercase) is not bool:
            raise TypeError("uppercase must be a bool")


@register_exporter
class HexExporter(PaletteExporter):
    """
    Export color palettes as plain-text hexadecimal RGB values.

    Each color is written as lowercase ``rrggbb`` on its own line with no
    leading ``#`` by default. ``HexExportOptions(uppercase=True)`` selects
    uppercase output for an individual Python export operation.

    This representation matches the HEX palette format commonly exported by
    Lospec and other palette-oriented tools.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the HEX exporter."""
        return ExporterMetadata(
            name="hex",
            description="Plain-text HEX palette (RRGGBB per line)",
            file_extension="hex",
            supports_colors=True,
            supports_filaments=False,
            options_type=HexExportOptions,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """Export colors using the default lowercase representation."""
        return self._write_colors(colors, output_path, uppercase=False)

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export colors using validated HEX options."""
        hex_options = cast(HexExportOptions, options)
        return self._write_colors(
            colors,
            output_path,
            uppercase=hex_options.uppercase,
        )

    def _write_colors(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        *,
        uppercase: bool,
    ) -> str:
        """Write colors to plain-text HEX format.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination HEX file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported HEX file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            for color in colors:
                hex_code = rgb_to_hex(color.rgb).removeprefix("#")
                if not uppercase:
                    hex_code = hex_code.lower()
                file.write(f"{hex_code}\n")

        return str(path)
