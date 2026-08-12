"""
PAINT.NET palette format exporter.

Exports colors in PAINT.NET's .txt palette format with AARRGGBB hex codes.
Supports optional comment headers for palette metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@dataclass(slots=True)
class PaintNetExportOptions(ExportOptionsBase):
    """Options controlling Paint.NET palette serialization."""

    pad_to_96: bool = False


@register_exporter
class PaintNetExporter(PaletteExporter):
    """
    Export color palettes in Paint.NET palette format.

    Paint.NET stores colors as 8-digit hexadecimal ARGB values:

        AARRGGBB

    Since ColorRecord currently contains opaque RGB colors, alpha is always
    written as ``FF``.

    Paint.NET palettes support a maximum of 96 palette entries. Optionally,
    palettes may be padded to 96 entries with opaque white.
    """

    MAX_COLORS = 96

    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name="paintnet",
            description="Paint.NET palette format",
            file_extension="txt",
            supports_colors=True,
            supports_filaments=False,
            options_type=PaintNetExportOptions,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        return self._write_palette(
            colors,
            output_path,
            pad_to_96=False,
        )

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        assert isinstance(options, PaintNetExportOptions)

        return self._write_palette(
            colors,
            output_path,
            pad_to_96=options.pad_to_96,
        )

    def _write_palette(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        *,
        pad_to_96: bool,
    ) -> str:
        if len(colors) > self.MAX_COLORS:
            raise ValueError(
                f"Paint.NET palettes support at most "
                f"{self.MAX_COLORS} colors; received {len(colors)}"
            )

        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            file.write(";paint.net Palette File\n")
            file.write(f"; Colors: {len(colors)}\n")

            for color in colors:
                hex_code = color.hex.removeprefix("#").upper()
                file.write(f"FF{hex_code}\n")

            if pad_to_96:
                for _ in range(self.MAX_COLORS - len(colors)):
                    file.write("FFFFFFFF\n")

        return str(path)
