"""HueForge filament-library JSON exporter.

HueForge requires a transmission-distance value for every filament. Filter
records before exporting when a source collection may contain missing values::

    with_td = [record for record in filaments if record.td_value is not None]
    export_filaments(with_td, "hueforge", "personal_library.json")
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from color_tools.exporters.base import ExporterMetadata, PaletteExporter
from color_tools.exporters.export_options_base import ExportOptionsBase
from color_tools.exporters.registry import register_exporter

if TYPE_CHECKING:
    from color_tools.filament_palette import FilamentRecord


class _HueForgeFilament(TypedDict):
    """Serialized HueForge filament entry."""

    Brand: str
    Color: str
    Name: str
    Owned: bool
    Transmissivity: float
    Type: str
    uuid: str


@dataclass(slots=True)
class HueForgeExportOptions(ExportOptionsBase):
    """Configure whether exported filaments are marked as owned.

    ``owned`` defaults to true because a generated HueForge library normally
    represents the caller's available filament collection. Set it to false to
    create entries that HueForge should not initially mark as owned.
    """

    owned: bool = True

    def __post_init__(self) -> None:
        """Validate HueForge export options."""
        if type(self.owned) is not bool:
            raise TypeError("owned must be a bool")


@register_exporter
class HueForgeExporter(PaletteExporter):
    """Export filament records as a HueForge filament-library document.

    Every record must have a TD value and a nonempty, unique Color Tools ID.
    Stable HueForge UUIDs are derived from those IDs with UUIDv5, so repeated
    exports of the same records retain their identities.

    The exporter raises ``ValueError`` rather than silently omitting records
    without TD values. Callers can prefilter with
    ``FilamentFilterCriteria(has_td=True)`` or use the CLI's ``--has-td``
    option.
    """

    @property
    def metadata(self) -> ExporterMetadata:
        """Return metadata describing the HueForge exporter."""
        return ExporterMetadata(
            name="hueforge",
            description="HueForge filament library JSON format",
            file_extension="json",
            supports_colors=False,
            supports_filaments=True,
            options_type=HueForgeExportOptions,
        )

    def _export_filaments_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
    ) -> str:
        """Export filaments using the default owned state."""
        return self._write_filaments(
            filaments,
            output_path,
            owned=HueForgeExportOptions().owned,
        )

    def _export_filaments_with_options_impl(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
        options: ExportOptionsBase,
    ) -> str:
        """Export filaments using validated HueForge options."""
        hueforge_options = cast(HueForgeExportOptions, options)
        return self._write_filaments(
            filaments,
            output_path,
            owned=hueforge_options.owned,
        )

    def _write_filaments(
        self,
        filaments: list[FilamentRecord],
        output_path: Path | str | None,
        *,
        owned: bool,
    ) -> str:
        """Validate and write one HueForge filament-library document."""
        filament_ids = [filament.id.strip() for filament in filaments]
        missing_id_count = filament_ids.count("")
        if missing_id_count:
            raise ValueError(
                "HueForge requires a non-empty ID for every filament so UUIDs "
                f"remain unique; {missing_id_count} selected filament(s) have no ID"
            )

        duplicate_ids = sorted(
            filament_id
            for filament_id, count in Counter(filament_ids).items()
            if count > 1
        )
        if duplicate_ids:
            preview = ", ".join(duplicate_ids[:3])
            if len(duplicate_ids) > 3:
                preview += ", ..."
            raise ValueError(
                "HueForge requires unique filament IDs so UUIDs remain unique; "
                f"found {len(duplicate_ids)} duplicate ID(s): {preview}"
            )

        missing_td = [
            filament.id
            for filament in filaments
            if filament.td_value is None
        ]
        if missing_td:
            preview = ", ".join(missing_td[:3])
            if len(missing_td) > 3:
                preview += ", ..."
            raise ValueError(
                "HueForge requires Transmissivity for every filament; "
                f"{len(missing_td)} selected filament(s) have no TD value: {preview}"
            )

        records = [
            self._serialize_filament(filament, owned=owned)
            for filament in filaments
        ]
        path = Path(output_path or self.generate_filename("filaments"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump({"Filaments": records}, file, indent=4, ensure_ascii=False)
            file.write("\n")
        return str(path)

    @staticmethod
    def _serialize_filament(
        filament: FilamentRecord,
        *,
        owned: bool,
    ) -> _HueForgeFilament:
        """Convert one validated filament to HueForge field names."""
        td_value = cast(float, filament.td_value)
        filament_uuid = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"color-tools:filament:{filament.id}",
        )
        return {
            "Brand": filament.maker,
            "Color": filament.effective_hex,
            "Name": filament.color,
            "Owned": owned,
            "Transmissivity": td_value,
            "Type": filament.type,
            "uuid": f"{{{filament_uuid}}}",
        }
