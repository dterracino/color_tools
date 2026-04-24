"""
Palette LUT exporter.

Exports a palette as a 1×N PNG strip suitable for use as a GLSL palette
LUT texture.  Each pixel in the strip is one palette colour, in palette order.
The strip can be loaded directly as a GPU texture and sampled with:

    float u   = (float(i) + 0.5) / float(u_palette_size);
    vec3  col = texture(u_palette, vec2(u, 0.5)).rgb;

No external dependencies are required — this exporter uses the built-in
``SimplePNGWriter`` (pure stdlib) instead of Pillow.

Format details
--------------
- Width:   number of palette colours (N)
- Height:  1 pixel (true LUT; sufficient for GPU sampling)
- Mode:    RGB, 8-bit per channel
- Sampling: NEAREST filter recommended on the GPU side

This exporter supports CSS colour palettes only.  Filaments are not
meaningful as indexed GPU colour tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from color_tools.exporters import register_exporter
from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.image.png_writer import SimplePNGWriter

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord
    from color_tools.palette import ColorRecord


@register_exporter
class PaletteLutExporter(PaletteExporter):
    """
    Palette LUT PNG exporter.

    Writes a 1×N PNG strip where each pixel is one palette colour.
    The output is a valid GPU LUT texture: load it with NEAREST filtering
    and sample by index to quantise any pixel to the nearest palette colour.

    Example::

        >>> from color_tools.exporters import get_exporter
        >>> from color_tools import load_palette
        >>> exporter = get_exporter('palette_lut')
        >>> palette  = load_palette('nes')
        >>> path = exporter.export_colors(palette.records, 'nes.png')
        >>> print(path)   # 54×1 px PNG strip
        nes.png

    The resulting PNG can be used directly in the ``palette_lut.frag`` shader::

        uniform sampler2D u_palette;      // bind nes.png here
        uniform int       u_palette_size; // 54

    See Also
    --------
    ``color_tools.image._png_writer.SimplePNGWriter`` — the underlying writer.
    ``demos/shaders/palette_lut.frag``                — the companion GLSL shader.
    ``demos/palette_lut_demo.py``                     — interactive demo.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        return ExporterMetadata(
            name="palette_lut",
            description="Palette LUT texture PNG (1×N strip for GLSL shaders)",
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
        """Write a 1×N LUT PNG strip from a list of ColorRecords."""
        if output_path is None:
            output_path = Path(f"palette_lut_{len(colors)}.png")

        rgb_tuples = [record.rgb for record in colors]
        SimplePNGWriter(rgb_tuples, swatch_width=1, swatch_height=1).save(output_path)
        return str(output_path)

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """Not supported - Palette LUT format loses filament metadata."""
        # Unreachable: supports_filaments=False causes base class to raise first
        raise NotImplementedError  # pragma: no cover
