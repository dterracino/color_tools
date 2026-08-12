"""
CSS custom-properties palette exporter.

Exports palette colors as CSS custom properties inside a :root block.

Example::

    :root {
        --coral: #FF7F50;
        --deep-blue: #1D2B53;
    }

Color names are converted to valid, readable CSS custom-property names.
"""

from __future__ import annotations

import re
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
class CSSExporter(PaletteExporter):
    """Export color palettes as CSS custom properties."""

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the CSS exporter."""
        return ExporterMetadata(
            name="css",
            description="CSS custom-properties palette",
            file_extension="css",
            supports_colors=True,
            supports_filaments=False,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors as CSS custom properties.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination CSS file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported CSS file as a string.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        used_names: set[str] = set()

        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            file.write(":root {\n")

            for index, color in enumerate(colors, start=1):
                name = self._make_unique_name(
                    self._to_css_name(color.name, index),
                    used_names,
                )

                hex_code = (
                    "#"
                    + color.hex.removeprefix("#").upper()
                )

                file.write(f"    --{name}: {hex_code};\n")

            file.write("}\n")

        return str(path)

    @staticmethod
    def _to_css_name(
        name: str | None,
        index: int,
    ) -> str:
        """
        Convert a color name to a CSS-friendly identifier.

        Args:
            name:
                Source color name.

            index:
                One-based palette index used when no usable name exists.

        Returns:
            Sanitized custom-property identifier without the leading ``--``.
        """
        if not name:
            return f"color-{index}"

        value = name.strip().lower()
        value = re.sub(r"\s+", "-", value)
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        value = re.sub(r"-{2,}", "-", value)
        value = value.strip("-_")

        if not value:
            return f"color-{index}"

        if value[0].isdigit():
            value = f"color-{value}"

        return value

    @staticmethod
    def _make_unique_name(
        name: str,
        used_names: set[str],
    ) -> str:
        """Ensure duplicate color names produce unique CSS properties."""
        candidate = name
        suffix = 2

        while candidate in used_names:
            candidate = f"{name}-{suffix}"
            suffix += 1

        used_names.add(candidate)
        return candidate
