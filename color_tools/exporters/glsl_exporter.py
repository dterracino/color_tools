"""GLSL source-code palette exporter.

Exports ordered palettes as ``vec3`` or ``vec4`` shader definitions. Colors
may be emitted as a constant array, named constants, or preprocessor defines.
RGB channels are normalized to 0.0-1.0 by default; raw output preserves the
0-255 range while still emitting floating-point literals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.exporters.palette_export_data import PaletteExportData
    from color_tools.exporters.palette_metadata import PaletteMetadata
    from color_tools.palette import ColorRecord


GLSLRepresentation = Literal[
    "array",
    "constants",
    "defines",
]


_GLSL_KEYWORDS = {
    "attribute",
    "bool",
    "break",
    "buffer",
    "case",
    "centroid",
    "coherent",
    "const",
    "continue",
    "default",
    "discard",
    "do",
    "double",
    "else",
    "false",
    "flat",
    "float",
    "for",
    "if",
    "in",
    "inout",
    "int",
    "invariant",
    "layout",
    "mat2",
    "mat3",
    "mat4",
    "noperspective",
    "out",
    "patch",
    "precise",
    "readonly",
    "restrict",
    "return",
    "sample",
    "shared",
    "smooth",
    "struct",
    "subroutine",
    "switch",
    "true",
    "uint",
    "uniform",
    "varying",
    "vec2",
    "vec3",
    "vec4",
    "void",
    "volatile",
    "while",
    "writeonly",
}


@dataclass(slots=True)
class GLSLExportOptions(ExportOptionsBase):
    """Configuration for GLSL source-code palette export.

    Attributes:
        representation:
            ``"array"`` emits one indexed constant array, ``"constants"``
            emits named ``const`` values, and ``"defines"`` emits named
            preprocessor definitions.
        normalized:
            Divide RGB channels by 255 and emit values in the 0.0-1.0 range.
            When false, raw 0-255 channels are emitted with a ``.0`` suffix.
        include_alpha:
            Emit ``vec4`` values with an opaque alpha channel instead of
            ``vec3`` values.
        include_metadata:
            Include available palette metadata as leading line comments.
        include_names_as_comments:
            Add color names after entries in the array representation.
        variable_name:
            GLSL identifier used for the array and its optional size constant.
        identifier_prefix:
            Prefix applied to generated constant and macro identifiers.
        precision:
            Decimal places used for normalized channels. Must be at least one.
        include_size_constant:
            Emit ``<variable_name>_SIZE`` with the number of colors.
        include_version:
            Emit a ``#version`` directive as the first line.
        version:
            Version directive value, such as ``"330 core"`` or ``"300 es"``.
    """

    representation: GLSLRepresentation = "array"
    normalized: bool = True
    include_alpha: bool = False
    include_metadata: bool = True
    include_names_as_comments: bool = True
    variable_name: str = "PALETTE"
    identifier_prefix: str = ""
    precision: int = 6
    include_size_constant: bool = True
    include_version: bool = False
    version: str = "330 core"

    def __post_init__(self) -> None:
        """Validate GLSL export options."""
        if self.representation not in {"array", "constants", "defines"}:
            raise ValueError(
                f"Unsupported GLSL representation: {self.representation!r}"
            )

        self._validate_identifier(self.variable_name, "variable_name")

        if self.identifier_prefix:
            self._validate_identifier(
                self.identifier_prefix,
                "identifier_prefix",
            )

        if self.precision < 1:
            raise ValueError("GLSL precision must be at least one")

        if not re.fullmatch(
            r"[1-9][0-9]{2}(?:\s+(?:core|compatibility|es))?",
            self.version,
        ):
            raise ValueError(
                "GLSL version must look like '330 core', '300 es', or '460'"
            )

    @staticmethod
    def _validate_identifier(
        value: str,
        field_name: str,
    ) -> None:
        """Validate a user-supplied GLSL identifier or identifier prefix."""
        if not value or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) is None:
            raise ValueError(f"Invalid GLSL {field_name}: {value!r}")

        lowered = value.lower()
        if lowered.startswith("gl_"):
            raise ValueError(
                f"GLSL {field_name} must not use the reserved 'gl_' prefix"
            )
        if lowered in _GLSL_KEYWORDS:
            raise ValueError(
                f"GLSL {field_name} must not be a reserved keyword: {value!r}"
            )


@register_exporter
class GLSLExporter(PaletteExporter):
    """Export palettes as reusable GLSL ``vec3`` or ``vec4`` definitions."""

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the GLSL exporter."""
        return ExporterMetadata(
            name="glsl",
            description="GLSL shader source-code palette",
            file_extension="glsl",
            supports_colors=True,
            supports_filaments=False,
            supports_palette_metadata=True,
            is_binary=False,
            options_type=GLSLExportOptions,
        )

    def _export_colors_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
    ) -> str:
        """Export colors with default GLSL options."""
        return self._export(
            colors=colors,
            metadata=None,
            output_path=output_path,
            options=GLSLExportOptions(),
        )

    def _export_colors_with_options_impl(
        self,
        colors: list[ColorRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export colors with explicit GLSL options."""
        return self._export(
            colors=colors,
            metadata=None,
            output_path=output_path,
            options=cast(GLSLExportOptions, options),
        )

    def _export_palette_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
    ) -> str:
        """Export a metadata-aware palette with default GLSL options."""
        return self._export(
            colors=palette.colors,
            metadata=palette.metadata,
            output_path=output_path,
            options=GLSLExportOptions(),
        )

    def _export_palette_with_options_impl(
        self,
        palette: PaletteExportData,
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export a metadata-aware palette with explicit GLSL options."""
        return self._export(
            colors=palette.colors,
            metadata=palette.metadata,
            output_path=output_path,
            options=cast(GLSLExportOptions, options),
        )

    def _export(
        self,
        *,
        colors: list[ColorRecord],
        metadata: PaletteMetadata | None,
        output_path: Path | str | None,
        options: GLSLExportOptions,
    ) -> str:
        """Write one complete GLSL palette source file."""
        if not colors:
            raise ValueError("GLSL export requires at least one color")

        if output_path is None:
            output_path = self.generate_filename("colors")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._build_source(
                colors=colors,
                metadata=metadata,
                options=options,
            ),
            encoding="utf-8",
            newline="\n",
        )
        return str(path)

    def _build_source(
        self,
        *,
        colors: list[ColorRecord],
        metadata: PaletteMetadata | None,
        options: GLSLExportOptions,
    ) -> str:
        """Build complete GLSL palette source."""
        sections: list[str] = []

        if options.include_version:
            sections.append(f"#version {options.version}")

        sections.append(
            self._build_header(
                metadata=metadata,
                include_metadata=options.include_metadata,
            )
        )

        if options.representation == "array":
            sections.append(self._build_array(colors=colors, options=options))
        elif options.representation == "constants":
            sections.append(
                self._build_named_values(
                    colors=colors,
                    options=options,
                    defines=False,
                )
            )
        elif options.representation == "defines":
            sections.append(
                self._build_named_values(
                    colors=colors,
                    options=options,
                    defines=True,
                )
            )
        else:  # pragma: no cover - options validation prevents this
            raise ValueError(
                f"Unsupported GLSL representation: {options.representation!r}"
            )

        return "\n\n".join(sections) + "\n"

    def _build_header(
        self,
        *,
        metadata: PaletteMetadata | None,
        include_metadata: bool,
    ) -> str:
        """Build generated-file and optional palette metadata comments."""
        lines = ["// Palette generated by color_tools."]
        if metadata is None or not include_metadata:
            return "\n".join(lines)

        fields = (
            ("Name", metadata.name),
            ("Author", metadata.author),
            ("Description", metadata.description),
        )
        for label, value in fields:
            clean_value = self._sanitize_comment(value)
            if clean_value:
                lines.append(f"// {label}: {clean_value}")

        if metadata.tags:
            lines.append(f"// Tags: {', '.join(metadata.tags)}")

        return "\n".join(lines)

    def _build_array(
        self,
        *,
        colors: list[ColorRecord],
        options: GLSLExportOptions,
    ) -> str:
        """Build an indexed GLSL constant array."""
        count = len(colors)
        vector_type = self._vector_type(options)
        lines: list[str] = []

        if options.include_size_constant:
            lines.append(f"const int {options.variable_name}_SIZE = {count};")
            lines.append("")

        lines.append(
            f"const {vector_type} {options.variable_name}[{count}] = "
            f"{vector_type}[{count}]("
        )

        for index, color in enumerate(colors):
            value = self._format_color(color=color, options=options)
            comma = "," if index < count - 1 else ""
            line = f"    {value}{comma}"
            if options.include_names_as_comments and color.name.strip():
                line += f"  // {self._sanitize_comment(color.name)}"
            lines.append(line)

        lines.append(");")
        return "\n".join(lines)

    def _build_named_values(
        self,
        *,
        colors: list[ColorRecord],
        options: GLSLExportOptions,
        defines: bool,
    ) -> str:
        """Build named GLSL constants or preprocessor definitions."""
        lines: list[str] = []
        size_name = f"{options.variable_name}_SIZE"

        if options.include_size_constant:
            if defines:
                lines.append(f"#define {size_name} {len(colors)}")
            else:
                lines.append(f"const int {size_name} = {len(colors)};")

        identifiers = self._make_identifiers(
            colors=colors,
            prefix=options.identifier_prefix,
        )
        vector_type = self._vector_type(options)

        for color, identifier in zip(colors, identifiers):
            value = self._format_color(color=color, options=options)
            if defines:
                lines.append(f"#define {identifier} {value}")
            else:
                lines.append(f"const {vector_type} {identifier} = {value};")

        return "\n".join(lines)

    @staticmethod
    def _vector_type(options: GLSLExportOptions) -> str:
        """Return the GLSL vector type selected by the alpha option."""
        return "vec4" if options.include_alpha else "vec3"

    def _format_color(
        self,
        *,
        color: ColorRecord,
        options: GLSLExportOptions,
    ) -> str:
        """Format one RGB or RGBA value as a GLSL vector constructor."""
        if options.normalized:
            values = [
                f"{channel / 255.0:.{options.precision}f}"
                for channel in color.rgb
            ]
            if options.include_alpha:
                values.append(f"{1.0:.{options.precision}f}")
        else:
            values = [f"{channel}.0" for channel in color.rgb]
            if options.include_alpha:
                values.append("255.0")

        return f"{self._vector_type(options)}({', '.join(values)})"

    @classmethod
    def _make_identifiers(
        cls,
        *,
        colors: list[ColorRecord],
        prefix: str,
    ) -> list[str]:
        """Create deterministic, unique GLSL identifiers for colors."""
        used: set[str] = set()
        result: list[str] = []
        normalized_prefix = prefix.upper()

        for color in colors:
            identifier = cls._to_identifier(color.name or color.hex)
            if normalized_prefix.endswith("_") and identifier.startswith("_"):
                identifier = identifier.lstrip("_")
            base = normalized_prefix + identifier
            candidate = base
            suffix = 2
            while candidate in used:
                candidate = f"{base}_{suffix}"
                suffix += 1
            used.add(candidate)
            result.append(candidate)

        return result

    @staticmethod
    def _to_identifier(value: str) -> str:
        """Convert a color name to a legal uppercase GLSL identifier."""
        identifier = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
        identifier = re.sub(r"_+", "_", identifier).strip("_").upper()
        if not identifier:
            identifier = "COLOR"
        if identifier[0].isdigit():
            identifier = "_" + identifier
        if identifier.lower().startswith("gl_") or identifier.lower() in _GLSL_KEYWORDS:
            identifier = "COLOR_" + identifier
        return identifier

    @staticmethod
    def _sanitize_comment(value: str) -> str:
        """Collapse arbitrary text into one safe GLSL line comment."""
        return " ".join(value.splitlines()).strip()
