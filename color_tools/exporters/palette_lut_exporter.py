"""
Palette LUT PNG exporter.

Exports a palette as an N×1 PNG strip suitable for use as a GPU palette
lookup texture.

Each pixel represents one palette color in palette order. The texture may be
sampled directly by palette index:

    float u = (float(i) + 0.5) / float(u_palette_size);
    vec3 color = texture(u_palette, vec2(u, 0.5)).rgb;

No external dependencies are required. This exporter uses the built-in
SimplePNGWriter, which is implemented using only the Python standard library.

Format details:
    - Width: number of palette colors (N)
    - Height: 1 pixel
    - Mode: 8-bit RGB
    - Ordering: palette order
    - Recommended GPU filtering: NEAREST

The resulting texture performs indexed palette lookup:

    palette index -> RGB color

A shader may additionally use the texture as the palette source when
performing nearest-color quantization, but the LUT itself does not perform
that quantization.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.registry import register_exporter
from color_tools.image.png_writer import SimplePNGWriter

if TYPE_CHECKING:
    from color_tools.palette import ColorRecord


@register_exporter
class PaletteLutExporter(PaletteExporter):
    """
    Export color palettes as N×1 RGB PNG lookup textures.

    Each palette entry is written as one pixel in palette order.

    The resulting image is suitable for uploading directly to a GPU texture
    and sampling by palette index. NEAREST filtering is recommended so texture
    sampling does not interpolate between adjacent palette entries.

    Example:

        >>> from color_tools.exporters import get_exporter
        >>> from color_tools import load_palette
        >>>
        >>> exporter = get_exporter("palette_lut")
        >>> palette = load_palette("nes")
        >>> path = exporter.export_colors(
        ...     palette.records,
        ...     "nes.png",
        ... )

    GLSL indexed lookup:

        uniform sampler2D u_palette;
        uniform int u_palette_size;

        float u = (float(i) + 0.5) / float(u_palette_size);
        vec3 color = texture(
            u_palette,
            vec2(u, 0.5)
        ).rgb;
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the palette LUT exporter."""
        return ExporterMetadata(
            name="palette_lut",
            description="N×1 RGB palette LUT texture for GPU shaders",
            file_extension="png",
            supports_colors=True,
            supports_filaments=False,
            is_binary=True,
            is_image=True,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """
        Export colors as an N×1 RGB PNG lookup texture.

        Args:
            colors:
                Color records to export.

            output_path:
                Destination PNG file. If None, a timestamped filename is
                generated in the current working directory.

        Returns:
            Path to the exported PNG file as a string.

        Raises:
            ValueError:
                If the palette is empty. SimplePNGWriter requires at least
                one color.
        """
        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        rgb_values = [
            color.rgb
            for color in colors
        ]

        writer = SimplePNGWriter(
            rgb_values,
            swatch_width=1,
            swatch_height=1,
        )

        writer.save(path)

        return str(path)