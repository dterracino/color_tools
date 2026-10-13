"""Database-wide runtime checks for the bundled filament catalog."""

from __future__ import annotations

from collections import Counter
import math
import struct
from typing import Literal, TypeAlias
import unittest
import zlib

from color_tools import (
    FilamentPalette,
    FilamentRecord,
    MultiColorMode,
    config_context,
    load_filaments,
    rgb_to_hex,
)


_EXPECTED_FILAMENT_COUNT = 1_545
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SwatchMode: TypeAlias = Literal["solid", "blocks", "gradient"]
_MULTI_COLOR_MODES: tuple[MultiColorMode, ...] = ("first", "last", "srgb_mean")
_SWATCH_MODES: tuple[_SwatchMode, ...] = ("solid", "blocks", "gradient")


def _expected_rgb(
    components: tuple[tuple[int, int, int], ...],
    mode: MultiColorMode,
) -> tuple[int, int, int]:
    """Calculate the expected effective RGB independently of FilamentRecord."""
    if mode == "last":
        return components[-1]
    if mode == "srgb_mean":
        count = len(components)
        return (
            round(sum(component[0] for component in components) / count),
            round(sum(component[1] for component in components) / count),
            round(sum(component[2] for component in components) / count),
        )
    return components[0]


def _validate_png(payload: bytes, width: int, height: int) -> None:
    """Validate the structure, checksums, dimensions, and pixel payload of a PNG."""
    if not payload.startswith(_PNG_SIGNATURE):
        raise AssertionError("Swatch does not have a valid PNG signature")

    offset = len(_PNG_SIGNATURE)
    idat = bytearray()
    found_ihdr = False
    found_iend = False
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise AssertionError("PNG contains a truncated chunk header")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(payload):
            raise AssertionError("PNG contains a truncated chunk")

        chunk_data = payload[data_start:data_end]
        expected_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        actual_crc = struct.unpack(">I", payload[data_end:crc_end])[0]
        if actual_crc != expected_crc:
            raise AssertionError(f"PNG chunk {chunk_type!r} has an invalid CRC")

        if chunk_type == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk_data)
            if header != (width, height, 8, 2, 0, 0, 0):
                raise AssertionError(f"Unexpected PNG header: {header!r}")
            found_ihdr = True
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            found_iend = True
            offset = crc_end
            break
        offset = crc_end

    if not found_ihdr or not found_iend or offset != len(payload):
        raise AssertionError("PNG is missing required chunks or has trailing data")
    raw_pixels = zlib.decompress(bytes(idat))
    expected_size = height * (1 + width * 3)
    if len(raw_pixels) != expected_size:
        raise AssertionError(
            f"PNG decoded to {len(raw_pixels)} bytes; expected {expected_size}"
        )


class TestFilamentDatabaseRuntime(unittest.TestCase):
    """Exercise every bundled filament through its public runtime paths."""

    def test_record_identities_are_unique_after_normalization(self) -> None:
        """No records should differ only by identity-field case or whitespace."""
        records = load_filaments()
        identities: dict[tuple[str, str, str, str], str] = {}
        for record in records:
            identity = (
                record.maker.strip().casefold(),
                record.type.strip().casefold(),
                (record.finish or "").strip().casefold(),
                record.color.strip().casefold(),
            )
            self.assertNotIn(
                identity,
                identities,
                f"{record.id!r} duplicates normalized identity of "
                f"{identities.get(identity)!r}",
            )
            identities[identity] = record.id

    def test_every_record_loads_in_each_multi_color_mode(self) -> None:
        """All records should produce valid components, RGB, LAB, and hex values."""
        for mode in _MULTI_COLOR_MODES:
            with self.subTest(mode=mode), config_context(multi_color_mode=mode):
                records = load_filaments()
                self.assertEqual(len(records), _EXPECTED_FILAMENT_COUNT)
                for record in records:
                    with self.subTest(mode=mode, filament_id=record.id):
                        self.assertGreaterEqual(len(record.rgb_components), 1)
                        for component in record.rgb_components:
                            self.assertEqual(len(component), 3)
                            self.assertTrue(all(0 <= channel <= 255 for channel in component))
                        expected_rgb = _expected_rgb(record.rgb_components, mode)
                        self.assertEqual(record.rgb, expected_rgb)
                        self.assertEqual(record.effective_hex, rgb_to_hex(expected_rgb))
                        self.assertEqual(len(record.lab), 3)
                        self.assertTrue(all(math.isfinite(value) for value in record.lab))

    def test_default_palette_indexes_every_record(self) -> None:
        """Every record should round-trip through all applicable public indexes."""
        palette = FilamentPalette.load_default()
        self.assertEqual(len(palette.records), _EXPECTED_FILAMENT_COUNT)

        maker_counts = Counter(record.maker for record in palette.records)
        type_counts = Counter(record.type for record in palette.records)
        finish_counts = Counter(
            record.finish for record in palette.records if record.finish is not None
        )
        for maker, count in maker_counts.items():
            self.assertEqual(len(palette.find_by_maker(maker)), count)
        for type_name, count in type_counts.items():
            self.assertEqual(len(palette.find_by_type(type_name)), count)
        for finish, count in finish_counts.items():
            self.assertEqual(len(palette.find_by_finish(finish)), count)

        for record in palette.records:
            with self.subTest(filament_id=record.id):
                self.assertIs(palette.get_filament_by_id(record.id), record)
                self.assertTrue(
                    any(candidate is record for candidate in palette.find_by_color(record.color))
                )
                self.assertTrue(
                    any(candidate is record for candidate in palette.find_by_rgb(record.rgb))
                )

    def test_every_record_generates_valid_swatch_pngs(self) -> None:
        """All records should render decodable solid, block, and gradient PNGs."""
        records: list[FilamentRecord] = load_filaments()
        width = 7
        height = 3
        for record in records:
            for mode in _SWATCH_MODES:
                with self.subTest(filament_id=record.id, mode=mode):
                    _validate_png(
                        record.to_swatch_png(width=width, height=height, mode=mode),
                        width,
                        height,
                    )


if __name__ == "__main__":
    unittest.main()
