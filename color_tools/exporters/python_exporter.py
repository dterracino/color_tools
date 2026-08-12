"""
Python source-code palette exporter.

Exports palettes as directly usable Python source code.

Supported representations:

    dict
        PALETTE = {
            "Medium Blue": (53, 105, 184),
            "Muted Violet": (128, 88, 166),
        }

    list
        PALETTE = [
            (53, 105, 184),  # Medium Blue
            (128, 88, 166),  # Muted Violet
        ]

    tuple
        PALETTE = (
            (53, 105, 184),  # Medium Blue
            (128, 88, 166),  # Muted Violet
        )

    constants
        MEDIUM_BLUE = (53, 105, 184)
        MUTED_VIOLET = (128, 88, 166)

RGB values may be emitted either as standard 0-255 integers or normalized
0.0-1.0 floating-point values. Hexadecimal strings are also supported.

Palette metadata may optionally be emitted as a separate Python dictionary.

Example:

    >>> from color_tools.exporters import get_exporter
    >>> from color_tools.exporters.python_exporter import PythonExportOptions
    >>>
    >>> exporter = get_exporter("python")
    >>> exporter.export_palette(
    ...     palette,
    ...     "palette.py",
    ...     options=PythonExportOptions(
    ...         representation="dict",
    ...         normalized=True,
    ...     ),
    ... )
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from color_tools.exporters.base import (
    ExporterMetadata,
    PaletteExporter,
)
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.exporters.palette_metadata import PaletteMetadata
    from color_tools.palette import ColorRecord


Representation = Literal[
    "dict",
    "list",
    "tuple",
    "constants",
]

ValueFormat = Literal[
    "rgb",
    "hex",
]


@dataclass(slots=True)
class PythonExportOptions(ExportOptionsBase):
    """
    Per-export configuration for Python source-code palettes.

    Attributes:
        representation:
            Python structure used to represent the palette.

            Supported values:

                - ``"dict"``
                - ``"list"``
                - ``"tuple"``
                - ``"constants"``

        value_format:
            Color representation.

            ``"rgb"`` produces tuples such as ``(53, 105, 184)``.

            ``"hex"`` produces strings such as ``"#3569B8"``.

        normalized:
            Emit RGB channels as normalized floating-point values in the
            range 0.0-1.0 instead of integers in the range 0-255.

            Only valid with ``value_format="rgb"``.

        include_alpha:
            Add a fully opaque alpha channel to RGB values.

            Integer output uses 255.

            Normalized output uses 1.0.

            Only valid with ``value_format="rgb"``.

        include_metadata:
            When exporting PaletteExportData, emit palette metadata as a
            separate dictionary.

        include_names_as_comments:
            Include color names as trailing comments for list and tuple
            representations.

        variable_name:
            Python variable used for dict, list, and tuple representations.

            The metadata variable is derived from this name by appending
            ``_METADATA``.

            For example:

                variable_name="UI_COLORS"

            produces:

                UI_COLORS_METADATA = {...}
                UI_COLORS = {...}

        precision:
            Decimal precision used for normalized floating-point channels.
    """

    representation: Representation = "dict"
    value_format: ValueFormat = "rgb"

    normalized: bool = False
    include_alpha: bool = False

    include_metadata: bool = True
    include_names_as_comments: bool = True

    variable_name: str = "PALETTE"

    precision: int = 6

    def __post_init__(self) -> None:
        """Validate Python exporter options."""
        if self.representation not in {
            "dict",
            "list",
            "tuple",
            "constants",
        }:
            raise ValueError(
                f"Unsupported Python representation: "
                f"{self.representation!r}"
            )

        if self.value_format not in {
            "rgb",
            "hex",
        }:
            raise ValueError(
                f"Unsupported Python value format: "
                f"{self.value_format!r}"
            )

        if not self.variable_name:
            raise ValueError(
                "Python variable_name must not be empty"
            )

        if not self.variable_name.isidentifier():
            raise ValueError(
                f"Invalid Python variable name: "
                f"{self.variable_name!r}"
            )

        if keyword.iskeyword(
            self.variable_name
        ):
            raise ValueError(
                f"Python variable name must not be a keyword: "
                f"{self.variable_name!r}"
            )

        if self.precision < 0:
            raise ValueError(
                "Python precision must be zero or greater"
            )

        if (
            self.value_format == "hex"
            and self.normalized
        ):
            raise ValueError(
                "normalized=True is not valid with "
                "value_format='hex'"
            )

        if (
            self.value_format == "hex"
            and self.include_alpha
        ):
            raise ValueError(
                "include_alpha=True is not valid with "
                "value_format='hex'"
            )


@register_exporter
class PythonExporter(PaletteExporter):
    """
    Export palettes as Python source code.

    This exporter is intended to produce source that can be dropped directly
    into Python applications, games, tools, and rendering code.

    Several output structures are available through PythonExportOptions:

        - Dictionary
        - List
        - Tuple
        - Named constants

    RGB values may be emitted as 0-255 integers or normalized floating-point
    values. Hexadecimal strings are also supported.

    Example:

        >>> exporter = get_exporter("python")
        >>> exporter.export_palette(
        ...     palette,
        ...     "palette.py",
        ...     options=PythonExportOptions(
        ...         representation="dict",
        ...         normalized=True,
        ...         variable_name="GAME_COLORS",
        ...     ),
        ... )

    Result:

        GAME_COLORS_METADATA = {
            ...
        }

        GAME_COLORS = {
            "Medium Blue": (0.207843, 0.411765, 0.721569),
            ...
        }

    The generated structure is intentionally predictable so a future
    color_tools Python importer can safely parse canonical exporter output
    using Python's AST without executing the source file.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the Python exporter."""
        return ExporterMetadata(
            name="python",
            description="Python source-code palette",
            file_extension="py",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=False,
            options_type=PythonExportOptions,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """Export colors using the default Python options."""
        return self._export_colors(
            colors=colors,
            output_path=output_path,
            options=PythonExportOptions(),
        )

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export colors using explicitly supplied Python options."""
        return self._export_colors(
            colors=colors,
            output_path=output_path,
            options=cast(
                PythonExportOptions,
                options,
            ),
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """Export a palette using the default Python options."""
        return self._export_palette(
            palette=palette,
            output_path=output_path,
            options=PythonExportOptions(),
        )

    def _export_palette_with_options_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export a palette using explicitly supplied Python options."""
        return self._export_palette(
            palette=palette,
            output_path=output_path,
            options=cast(
                PythonExportOptions,
                options,
            ),
        )

    def _export_colors(
        self,
        *,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: PythonExportOptions,
    ) -> str:
        """Shared implementation for color-only Python export."""
        path = self._resolve_output_path(
            output_path
        )

        content = self._build_module(
            colors=colors,
            metadata=None,
            options=options,
        )

        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )

        return str(
            path
        )

    def _export_palette(
        self,
        *,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: PythonExportOptions,
    ) -> str:
        """Shared implementation for metadata-aware Python export."""
        path = self._resolve_output_path(
            output_path
        )

        content = self._build_module(
            colors=palette.colors,
            metadata=palette.metadata,
            options=options,
        )

        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )

        return str(
            path
        )

    def _resolve_output_path(
        self,
        output_path: Path | str | None,
    ) -> Path:
        """Resolve and prepare the output path."""
        if output_path is None:
            output_path = self.generate_filename(
                "colors"
            )

        path = Path(
            output_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path

    def _build_module(
        self,
        *,
        colors: list[ColorRecord],
        metadata: PaletteMetadata | None,
        options: PythonExportOptions,
    ) -> str:
        """Build complete Python module source."""
        sections = [
            '"""Palette generated by color_tools."""',
        ]

        if (
            metadata is not None
            and options.include_metadata
            and metadata.has_metadata
        ):
            sections.append(
                self._build_metadata(
                    metadata=metadata,
                    variable_name=(
                        f"{options.variable_name}_METADATA"
                    ),
                )
            )

        sections.append(
            self._build_palette(
                colors=colors,
                options=options,
            )
        )

        return (
            "\n\n".join(
                sections
            )
            + "\n"
        )

    def _build_palette(
        self,
        *,
        colors: list[ColorRecord],
        options: PythonExportOptions,
    ) -> str:
        """Build the palette portion of the generated module."""
        if options.representation == "dict":
            return self._build_dict(
                colors=colors,
                options=options,
            )

        if options.representation == "list":
            return self._build_sequence(
                colors=colors,
                options=options,
                opening="[",
                closing="]",
            )

        if options.representation == "tuple":
            return self._build_sequence(
                colors=colors,
                options=options,
                opening="(",
                closing=")",
            )

        if options.representation == "constants":
            return self._build_constants(
                colors=colors,
                options=options,
            )

        raise ValueError(
            f"Unsupported Python representation: "
            f"{options.representation!r}"
        )

    def _build_dict(
        self,
        *,
        colors: list[ColorRecord],
        options: PythonExportOptions,
    ) -> str:
        """Build a dictionary representation."""
        lines = [
            f"{options.variable_name} = {{",
        ]

        names = self._make_unique_names(
            colors
        )

        for color, name in zip(
            colors,
            names,
        ):
            value = self._format_color_value(
                color=color,
                options=options,
            )

            lines.append(
                f"    {name!r}: {value},"
            )

        lines.append(
            "}"
        )

        return "\n".join(
            lines
        )

    def _build_sequence(
        self,
        *,
        colors: list[ColorRecord],
        options: PythonExportOptions,
        opening: str,
        closing: str,
    ) -> str:
        """Build a list or tuple representation."""
        lines = [
            f"{options.variable_name} = {opening}",
        ]

        for color in colors:
            value = self._format_color_value(
                color=color,
                options=options,
            )

            line = (
                f"    {value},"
            )

            if (
                options.include_names_as_comments
                and color.name.strip()
            ):
                line += (
                    f"  # {self._sanitize_comment(color.name)}"
                )

            lines.append(
                line
            )

        lines.append(
            closing
        )

        return "\n".join(
            lines
        )

    def _build_constants(
        self,
        *,
        colors: list[ColorRecord],
        options: PythonExportOptions,
    ) -> str:
        """Build named Python constants."""
        identifiers = (
            self._make_constant_identifiers(
                colors
            )
        )

        lines = []

        for color, identifier in zip(
            colors,
            identifiers,
        ):
            value = self._format_color_value(
                color=color,
                options=options,
            )

            lines.append(
                f"{identifier} = {value}"
            )

        return "\n".join(
            lines
        )

    def _build_metadata(
        self,
        *,
        metadata: PaletteMetadata,
        variable_name: str,
    ) -> str:
        """Build the palette metadata dictionary."""
        lines = [
            f"{variable_name} = {{",
            f'    "name": {metadata.name!r},',
            f'    "author": {metadata.author!r},',
            f'    "description": {metadata.description!r},',
            f'    "columns": {metadata.columns!r},',
            f'    "tags": {metadata.tags!r},',
            f'    "properties": {metadata.properties!r},',
            "}",
        ]

        return "\n".join(
            lines
        )

    def _format_color_value(
        self,
        *,
        color: ColorRecord,
        options: PythonExportOptions,
    ) -> str:
        """Format one color according to the selected value options."""
        if options.value_format == "hex":
            return repr(
                color.hex.upper()
            )

        if options.value_format == "rgb":
            return self._format_rgb(
                rgb=color.rgb,
                options=options,
            )

        raise ValueError(
            f"Unsupported Python value format: "
            f"{options.value_format!r}"
        )

    @staticmethod
    def _format_rgb(
        *,
        rgb: tuple[int, int, int],
        options: PythonExportOptions,
    ) -> str:
        """Format RGB or RGBA as a Python tuple."""
        if options.normalized:
            values: list[str] = [
                f"{channel / 255.0:.{options.precision}f}"
                for channel in rgb
            ]

            if options.include_alpha:
                values.append(
                    f"{1.0:.{options.precision}f}"
                )

        else:
            values = [
                str(
                    channel
                )
                for channel in rgb
            ]

            if options.include_alpha:
                values.append(
                    "255"
                )

        return (
            "("
            + ", ".join(values)
            + ")"
        )

    @staticmethod
    def _make_unique_names(
        colors: list[ColorRecord],
    ) -> list[str]:
        """
        Produce unique dictionary keys without dropping duplicate colors.

        A missing name falls back to the hexadecimal value. Duplicate names
        receive a numeric suffix.

        Example:

            Blue
            Blue
            Blue

        becomes:

            Blue
            Blue 2
            Blue 3
        """
        counts: dict[str, int] = {}
        result: list[str] = []

        for color in colors:
            base_name = (
                color.name.strip()
                or color.hex.upper()
            )

            count = (
                counts.get(
                    base_name,
                    0,
                )
                + 1
            )

            counts[
                base_name
            ] = count

            if count == 1:
                result.append(
                    base_name
                )

            else:
                result.append(
                    f"{base_name} {count}"
                )

        return result

    @classmethod
    def _make_constant_identifiers(
        cls,
        colors: list[ColorRecord],
    ) -> list[str]:
        """Create unique legal Python identifiers for constant output."""
        used: dict[str, int] = {}
        result: list[str] = []

        for color in colors:
            identifier = (
                cls._to_constant_identifier(
                    color.name
                    or color.hex
                )
            )

            count = (
                used.get(
                    identifier,
                    0,
                )
                + 1
            )

            used[
                identifier
            ] = count

            if count > 1:
                identifier = (
                    f"{identifier}_{count}"
                )

            result.append(
                identifier
            )

        return result

    @staticmethod
    def _to_constant_identifier(
        name: str,
    ) -> str:
        """
        Convert a color name into a legal uppercase Python identifier.

        Examples:

            Medium Blue
                -> MEDIUM_BLUE

            Blue / Violet
                -> BLUE_VIOLET

            80's Neon!
                -> _80_S_NEON
        """
        identifier = re.sub(
            r"[^A-Za-z0-9_]+",
            "_",
            name.strip(),
        )

        identifier = re.sub(
            r"_+",
            "_",
            identifier,
        ).strip(
            "_"
        )

        if not identifier:
            identifier = "COLOR"

        identifier = (
            identifier.upper()
        )

        if identifier[0].isdigit():
            identifier = (
                "_"
                + identifier
            )

        if keyword.iskeyword(
            identifier.lower()
        ):
            identifier = (
                "_"
                + identifier
            )

        return identifier

    @staticmethod
    def _sanitize_comment(
        value: str,
    ) -> str:
        """Collapse a color name to a safe single-line Python comment."""
        return " ".join(
            value.splitlines()
        ).strip()