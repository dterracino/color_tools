"""
Palette swatch image exporter.

Exports a palette as a polished PNG swatch sheet intended for human viewing.

Each palette color is displayed as a card containing:

    - a large color swatch
    - an optional palette index
    - the color name
    - optional HEX, RGB, HSL, Lab, and LCh values

Palette-aware export can additionally display the palette name and description.

The layout automatically adapts its card height to the enabled color-value
fields.

This exporter uses Pillow and therefore requires the ``image`` optional extra.

Example:
    >>> from color_tools.exporters import get_exporter
    >>> from color_tools.exporters.palette_export_data import (
    ...     PaletteExportData,
    ... )
    >>> from color_tools.exporters.palette_metadata import PaletteMetadata
    >>> from color_tools.exporters.swatch_image_exporter import (
    ...     SwatchImageOptions,
    ... )
    >>>
    >>> exporter = get_exporter("swatch_image")
    >>>
    >>> palette = PaletteExportData(
    ...     colors=colors,
    ...     metadata=PaletteMetadata(
    ...         name="My Palette",
    ...         description="A generated color palette.",
    ...     ),
    ... )
    >>>
    >>> exporter.export_palette(
    ...     palette,
    ...     "palette.png",
    ...     options=SwatchImageOptions(
    ...         show_rgb=True,
    ...         show_lab=True,
    ...     ),
    ... )
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from color_tools.exporters.base import (
    ExporterDependency,
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont, ImageFont, TransposedFont

    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.palette import ColorRecord

    FontType = ImageFont | FreeTypeFont | TransposedFont
else:
    FontType = object


@dataclass(slots=True)
class SwatchImageOptions(ExportOptionsBase):
    """
    Display options for a swatch image export.

    Attributes:
        show_index:
            Show the palette position badge.

        show_hex:
            Show hexadecimal RGB values.

        show_rgb:
            Show integer RGB channel values.

        show_hsl:
            Show HSL values.

        show_lab:
            Show CIE Lab values.

        show_lch:
            Show CIE LCh values.
    """

    show_index: bool = True
    show_hex: bool = True
    show_rgb: bool = False
    show_hsl: bool = False
    show_lab: bool = False
    show_lch: bool = False


@register_exporter
class SwatchImageExporter(PaletteExporter):
    """
    Export palettes as presentation-oriented PNG swatch sheets.

    Each palette entry is rendered as a rounded card containing a large color
    sample, color name, and optionally several color-space representations.

    Palette-aware export additionally displays palette name and description
    when available.

    Pillow is loaded lazily so the exporter package remains importable when the
    ``image`` optional extra is not installed.

    Export-specific display settings are supplied through SwatchImageOptions
    rather than through the exporter constructor. This allows the registry to
    continue constructing exporters without arguments.

    Example:
        >>> from color_tools.exporters import get_exporter
        >>> from color_tools.exporters.swatch_image_exporter import (
        ...     SwatchImageOptions,
        ... )
        >>>
        >>> exporter = get_exporter("swatch_image")
        >>>
        >>> exporter.export_palette(
        ...     palette,
        ...     "palette.png",
        ...     options=SwatchImageOptions(
        ...         show_rgb=True,
        ...         show_hsl=True,
        ...         show_lab=True,
        ...         show_lch=True,
        ...     ),
        ... )
    """

    IMAGE_WIDTH = 1600

    OUTER_MARGIN = 64
    HEADER_GAP = 28

    CARD_WIDTH = 280
    CARD_GAP = 28

    CARD_PADDING = 18
    CARD_RADIUS = 20

    SWATCH_HEIGHT = 150
    SWATCH_RADIUS = 16
    SWATCH_BORDER_WIDTH = 1

    TITLE_FONT_SIZE = 64
    DESCRIPTION_FONT_SIZE = 22
    NAME_FONT_SIZE = 21
    VALUE_FONT_SIZE = 17
    INDEX_FONT_SIZE = 15

    NAME_VALUE_GAP = 10
    VALUE_LINE_GAP = 6
    CARD_BOTTOM_PADDING = 18

    BACKGROUND = (245, 245, 245)
    CARD_BACKGROUND = (255, 255, 255)

    TEXT_PRIMARY = (30, 30, 30)
    TEXT_SECONDARY = (85, 85, 85)

    SWATCH_BORDER = (218, 218, 218)

    INDEX_BACKGROUND = (238, 238, 238)
    INDEX_TEXT = (80, 80, 80)

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the swatch image exporter."""
        return ExporterMetadata(
            name="swatch_image",
            description="Presentation PNG palette swatch sheet",
            file_extension="png",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=True,
            is_image=True,
            dependencies=(
                ExporterDependency(
                    package="Pillow",
                    import_name="PIL",
                    extra="image",
                ),
            ),
            options_type=SwatchImageOptions,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """Export colors using default swatch image options."""
        return self._export_colors(
            colors=colors,
            output_path=output_path,
            options=SwatchImageOptions(),
        )

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export colors using caller-supplied swatch image options."""
        return self._export_colors(
            colors=colors,
            output_path=output_path,
            options=cast(
                SwatchImageOptions,
                options,
            ),
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """Export a palette using default swatch image options."""
        return self._export_palette(
            palette=palette,
            output_path=output_path,
            options=SwatchImageOptions(),
        )

    def _export_palette_with_options_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export a palette using caller-supplied swatch image options."""
        return self._export_palette(
            palette=palette,
            output_path=output_path,
            options=cast(
                SwatchImageOptions,
                options,
            ),
        )

    def _export_colors(
        self,
        *,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: SwatchImageOptions,
    ) -> str:
        """Shared color-only export implementation."""
        if output_path is None:
            output_path = self.generate_filename("colors")

        return self._write_image(
            colors=colors,
            path=Path(output_path),
            title="",
            description="",
            options=options,
        )

    def _export_palette(
        self,
        *,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: SwatchImageOptions,
    ) -> str:
        """Shared palette-aware export implementation."""
        if output_path is None:
            output_path = self.generate_filename("colors")

        return self._write_image(
            colors=palette.colors,
            path=Path(output_path),
            title=palette.metadata.name,
            description=palette.metadata.description,
            options=options,
        )

    def _write_image(
        self,
        *,
        colors: list[ColorRecord],
        path: Path,
        title: str,
        description: str,
        options: SwatchImageOptions,
    ) -> str:
        """
        Render and save the complete swatch sheet.

        Args:
            colors:
                Ordered palette colors.

            path:
                Destination PNG path.

            title:
                Optional palette title.

            description:
                Optional palette description.

            options:
                Swatch image display options.

        Returns:
            Path to the exported PNG file as a string.

        Raises:
            ValueError:
                If the palette contains no colors.
        """
        from PIL import Image, ImageDraw, ImageFont

        if not colors:
            raise ValueError(
                "Swatch image export requires at least one color"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fonts = self._load_fonts(ImageFont)

        title_font = fonts["title"]
        description_font = fonts["description"]
        name_font = fonts["name"]
        value_font = fonts["value"]
        index_font = fonts["index"]

        value_line_count = self._value_line_count(
            options
        )

        card_height = self._calculate_card_height(
            value_line_count
        )

        columns = self._calculate_columns()
        rows = math.ceil(
            len(colors) / columns
        )

        grid_width = (
            columns * self.CARD_WIDTH
            + (columns - 1) * self.CARD_GAP
        )

        grid_height = (
            rows * card_height
            + (rows - 1) * self.CARD_GAP
        )

        width = max(
            self.IMAGE_WIDTH,
            grid_width + self.OUTER_MARGIN * 2,
        )

        measure_image = Image.new(
            "RGB",
            (width, 1),
            self.BACKGROUND,
        )

        measure_draw = ImageDraw.Draw(
            measure_image
        )

        description_lines = self._wrap_text(
            draw=measure_draw,
            text=description,
            font=description_font,
            max_width=width - self.OUTER_MARGIN * 2,
        )

        header_height = self._calculate_header_height(
            draw=measure_draw,
            title=title,
            title_font=title_font,
            description_lines=description_lines,
            description_font=description_font,
        )

        height = (
            self.OUTER_MARGIN
            + header_height
            + grid_height
            + self.OUTER_MARGIN
        )

        image = Image.new(
            "RGB",
            (width, height),
            self.BACKGROUND,
        )

        draw = ImageDraw.Draw(
            image
        )

        current_y = self.OUTER_MARGIN

        if title:
            draw.text(
                (
                    self.OUTER_MARGIN,
                    current_y,
                ),
                title,
                fill=self.TEXT_PRIMARY,
                font=title_font,
            )

            current_y += (
                self._text_height(
                    draw,
                    title,
                    title_font,
                )
                + 16
            )

        if description_lines:
            line_height = (
                self._font_line_height(
                    draw,
                    description_font,
                )
                + 6
            )

            for line in description_lines:
                draw.text(
                    (
                        self.OUTER_MARGIN,
                        current_y,
                    ),
                    line,
                    fill=self.TEXT_SECONDARY,
                    font=description_font,
                )

                current_y += line_height

            current_y += self.HEADER_GAP

        elif title:
            current_y += self.HEADER_GAP

        grid_x = (
            width - grid_width
        ) // 2

        for index, color in enumerate(colors):
            row, column = divmod(
                index,
                columns,
            )

            x = (
                grid_x
                + column
                * (
                    self.CARD_WIDTH
                    + self.CARD_GAP
                )
            )

            y = (
                current_y
                + row
                * (
                    card_height
                    + self.CARD_GAP
                )
            )

            self._draw_card(
                draw=draw,
                color=color,
                index=index,
                x=x,
                y=y,
                card_height=card_height,
                name_font=name_font,
                value_font=value_font,
                index_font=index_font,
                options=options,
            )

        image.save(
            path,
            format="PNG",
        )

        return str(path)

    def _draw_card(
        self,
        *,
        draw,
        color: ColorRecord,
        index: int,
        x: int,
        y: int,
        card_height: int,
        name_font,
        value_font,
        index_font,
        options: SwatchImageOptions,
    ) -> None:
        """Draw a single palette swatch card."""
        card_right = (
            x + self.CARD_WIDTH
        )

        card_bottom = (
            y + card_height
        )

        draw.rounded_rectangle(
            (
                x,
                y,
                card_right,
                card_bottom,
            ),
            radius=self.CARD_RADIUS,
            fill=self.CARD_BACKGROUND,
        )

        swatch_left = (
            x + self.CARD_PADDING
        )

        swatch_top = (
            y + self.CARD_PADDING
        )

        swatch_right = (
            card_right
            - self.CARD_PADDING
        )

        swatch_bottom = (
            swatch_top
            + self.SWATCH_HEIGHT
        )

        draw.rounded_rectangle(
            (
                swatch_left,
                swatch_top,
                swatch_right,
                swatch_bottom,
            ),
            radius=self.SWATCH_RADIUS,
            fill=color.rgb,
            outline=self.SWATCH_BORDER,
            width=self.SWATCH_BORDER_WIDTH,
        )

        text_left = (
            x + self.CARD_PADDING
        )

        text_width = (
            self.CARD_WIDTH
            - self.CARD_PADDING * 2
        )

        name_y = (
            swatch_bottom
            + 14
        )

        if options.show_index:
            badge_text = str(
                index + 1
            ).zfill(
                max(
                    2,
                    len(
                        str(
                            index + 1
                        )
                    ),
                )
            )

            badge_width = 32
            badge_height = 24

            draw.rounded_rectangle(
                (
                    text_left,
                    name_y,
                    text_left + badge_width,
                    name_y + badge_height,
                ),
                radius=8,
                fill=self.INDEX_BACKGROUND,
            )

            draw.text(
                (
                    text_left
                    + badge_width / 2,
                    name_y
                    + badge_height / 2,
                ),
                badge_text,
                fill=self.INDEX_TEXT,
                font=index_font,
                anchor="mm",
            )

            name_x = (
                text_left
                + badge_width
                + 10
            )

            name_width = (
                text_width
                - badge_width
                - 10
            )

        else:
            name_x = text_left
            name_width = text_width

        color_name = (
            color.name
            or f"Color {index + 1}"
        )

        fitted_name = self._fit_text(
            draw=draw,
            text=color_name,
            font=name_font,
            max_width=name_width,
        )

        draw.text(
            (
                name_x,
                name_y + 1,
            ),
            fitted_name,
            fill=self.TEXT_PRIMARY,
            font=name_font,
        )

        values = self._build_value_lines(
            color,
            options,
        )

        name_height = self._font_line_height(
            draw,
            name_font,
        )

        current_y = (
            name_y
            + name_height
            + self.NAME_VALUE_GAP
        )

        value_line_height = (
            self._font_line_height(
                draw,
                value_font,
            )
            + self.VALUE_LINE_GAP
        )

        for label, value in values:
            draw.text(
                (
                    text_left,
                    current_y,
                ),
                f"{label}: {value}",
                fill=self.TEXT_SECONDARY,
                font=value_font,
            )

            current_y += (
                value_line_height
            )

    @staticmethod
    def _build_value_lines(
        color: ColorRecord,
        options: SwatchImageOptions,
    ) -> list[tuple[str, str]]:
        """Build the enabled color-value rows for a swatch card."""
        values: list[tuple[str, str]] = []

        if options.show_hex:
            values.append(
                (
                    "HEX",
                    "#"
                    + color.hex.removeprefix(
                        "#"
                    ).upper(),
                )
            )

        if options.show_rgb:
            r, g, b = color.rgb

            values.append(
                (
                    "RGB",
                    f"{r}, {g}, {b}",
                )
            )

        if options.show_hsl:
            h, s, lightness = color.hsl

            values.append(
                (
                    "HSL",
                    (
                        f"{h:.1f}, "
                        f"{s:.1f}, "
                        f"{lightness:.1f}"
                    ),
                )
            )

        if options.show_lab:
            lightness, a, b = color.lab

            values.append(
                (
                    "Lab",
                    (
                        f"{lightness:.1f}, "
                        f"{a:.1f}, "
                        f"{b:.1f}"
                    ),
                )
            )

        if options.show_lch:
            lightness, chroma, hue = color.lch

            values.append(
                (
                    "LCh",
                    (
                        f"{lightness:.1f}, "
                        f"{chroma:.1f}, "
                        f"{hue:.1f}"
                    ),
                )
            )

        return values

    @staticmethod
    def _value_line_count(
        options: SwatchImageOptions,
    ) -> int:
        """Return the number of enabled color-value rows."""
        return sum(
            (
                options.show_hex,
                options.show_rgb,
                options.show_hsl,
                options.show_lab,
                options.show_lch,
            )
        )

    def _calculate_card_height(
        self,
        value_line_count: int,
    ) -> int:
        """Calculate card height from the enabled information fields."""
        estimated_name_height = (
            self.NAME_FONT_SIZE
            + 4
        )

        estimated_value_height = (
            self.VALUE_FONT_SIZE
            + self.VALUE_LINE_GAP
        )

        values_height = 0

        if value_line_count:
            values_height = (
                self.NAME_VALUE_GAP
                + value_line_count
                * estimated_value_height
            )

        return (
            self.CARD_PADDING
            + self.SWATCH_HEIGHT
            + 14
            + estimated_name_height
            + values_height
            + self.CARD_BOTTOM_PADDING
        )

    def _calculate_columns(self) -> int:
        """Calculate how many cards fit across the default image width."""
        usable_width = (
            self.IMAGE_WIDTH
            - self.OUTER_MARGIN * 2
        )

        return max(
            1,
            (
                usable_width
                + self.CARD_GAP
            )
            // (
                self.CARD_WIDTH
                + self.CARD_GAP
            ),
        )

    def _calculate_header_height(
        self,
        *,
        draw,
        title: str,
        title_font,
        description_lines: list[str],
        description_font,
    ) -> int:
        """Calculate vertical space required by the optional header."""
        if (
            not title
            and not description_lines
        ):
            return 0

        height = 0

        if title:
            height += (
                self._text_height(
                    draw,
                    title,
                    title_font,
                )
                + 16
            )

        if description_lines:
            line_height = (
                self._font_line_height(
                    draw,
                    description_font,
                )
                + 6
            )

            height += (
                len(description_lines)
                * line_height
            )

            height += self.HEADER_GAP

        elif title:
            height += self.HEADER_GAP

        return height

    @staticmethod
    def _fit_text(
        *,
        draw,
        text: str,
        font,
        max_width: int,
    ) -> str:
        """Fit a single line within a maximum rendered width."""
        if not text:
            return ""

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )

        if (
            bbox[2] - bbox[0]
            <= max_width
        ):
            return text

        ellipsis = "…"
        candidate = text

        while candidate:
            candidate = (
                candidate[:-1].rstrip()
            )

            rendered = (
                candidate + ellipsis
            )

            bbox = draw.textbbox(
                (0, 0),
                rendered,
                font=font,
            )

            if (
                bbox[2] - bbox[0]
                <= max_width
            ):
                return rendered

        return ellipsis

    @staticmethod
    def _wrap_text(
        *,
        draw,
        text: str,
        font,
        max_width: int,
    ) -> list[str]:
        """Wrap text to a maximum rendered width."""
        if not text:
            return []

        words = text.split()

        if not words:
            return []

        lines: list[str] = []
        current = words[0]

        for word in words[1:]:
            candidate = (
                f"{current} {word}"
            )

            bbox = draw.textbbox(
                (0, 0),
                candidate,
                font=font,
            )

            if (
                bbox[2] - bbox[0]
                <= max_width
            ):
                current = candidate

            else:
                lines.append(
                    current
                )

                current = word

        lines.append(
            current
        )

        return lines

    @classmethod
    def _load_fonts(
        cls,
        image_font,
    ) -> dict[str, FontType]:
        """
        Load all fonts used by the exporter.

        Pillow's bundled DejaVu fonts are requested directly by filename.
        If they are unavailable, Pillow's default scalable font is used with
        an explicit size.

        Returning every font from one method keeps font selection centralized
        and avoids separate regular/bold/monospace loader paths.
        """
        return {
            "title": cls._create_font(
                image_font=image_font,
                preferred="DejaVuSans-Bold.ttf",
                size=cls.TITLE_FONT_SIZE,
            ),
            "description": cls._create_font(
                image_font=image_font,
                preferred="DejaVuSans.ttf",
                size=cls.DESCRIPTION_FONT_SIZE,
            ),
            "name": cls._create_font(
                image_font=image_font,
                preferred="DejaVuSans.ttf",
                size=cls.NAME_FONT_SIZE,
            ),
            "value": cls._create_font(
                image_font=image_font,
                preferred="DejaVuSansMono.ttf",
                size=cls.VALUE_FONT_SIZE,
            ),
            "index": cls._create_font(
                image_font=image_font,
                preferred="DejaVuSans-Bold.ttf",
                size=cls.INDEX_FONT_SIZE,
            ),
        }

    @staticmethod
    def _create_font(
        *,
        image_font,
        preferred: str,
        size: int,
    ):
        """
        Create a font at the requested size.

        The preferred DejaVu font is used when available. If Pillow cannot
        resolve it, load_default(size=...) supplies Pillow's built-in font at
        the requested size rather than silently falling back to the tiny
        historical default size.
        """
        try:
            return image_font.truetype(
                preferred,
                size,
            )

        except OSError:
            return image_font.load_default(
                size=size
            )

    @staticmethod
    def _text_height(
        draw,
        text: str,
        font,
    ) -> int:
        """Return the rendered height of a specific string."""
        bbox = draw.textbbox(
            (0, 0),
            text or "Ag",
            font=font,
        )

        return (
            bbox[3] - bbox[1]
        )

    @staticmethod
    def _font_line_height(
        draw,
        font,
    ) -> int:
        """Return a practical rendered line height for a font."""
        bbox = draw.textbbox(
            (0, 0),
            "Ag",
            font=font,
        )

        return (
            bbox[3] - bbox[1]
        )
