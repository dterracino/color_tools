"""Canonical RGB/hex contracts and multi-component filament regressions."""

from __future__ import annotations

import csv
from dataclasses import FrozenInstanceError, asdict, replace
import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from color_tools import config_context, hex_to_rgb, parse_hex_colors, rgb_to_hex, validate_rgb
from color_tools.conversions import rgb_to_lab
from color_tools.exporters.autoforge_exporter import AutoForgeExporter
from color_tools.exporters.csv_exporter import CSVExporter
from color_tools.exporters.json_exporter import JSONExporter
from color_tools.exporters.python_exporter import PythonExportOptions
from color_tools.exporters.registry import get_exporter
from color_tools.filament_palette import FilamentRecord, load_filaments
from color_tools.palette import ColorRecord, Palette, load_colors


def _record(hex_code: str) -> FilamentRecord:
    return FilamentRecord(
        id="probe", maker="probe", type="PLA", finish=None,
        color="probe", hex=hex_code,
    )


class TestColorInputs(unittest.TestCase):
    """Input errors must not become clipped colors or black placeholders."""

    def test_rgba_byte_order_and_alpha_discard(self) -> None:
        for value in ("1234", "#1234", "11223344", "#11223344", "#11223300"):
            with self.subTest(value=value):
                self.assertEqual(hex_to_rgb(value), (17, 34, 51))
        self.assertEqual(hex_to_rgb("#f000"), (255, 0, 0))
        self.assertEqual(ColorRecord.from_hex("#1234").hex, "#112233")

    def test_strict_hex_types_and_syntax(self) -> None:
        for value in (
            None, 123, b"fff", "", "#", "##fff", " fff", "fff ",
            "0xfff", "１２３", "#12G4", "#112233G0", "f-f-f", "12",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                hex_to_rgb(cast(str, value))

    def test_rgb_types_bounds_and_immutable_storage(self) -> None:
        class Integer(int):
            pass

        for value in (
            None, "123", (1, 2), (1, 2, 3, 4), (True, 2, 3),
            (1.0, 2, 3), (Integer(1), 2, 3), (-1, 2, 3), (256, 2, 3),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rgb(value)
            with self.assertRaises(ValueError):
                rgb_to_hex(cast(tuple[int, int, int], value))
        values = [0, 128, 255]
        record = ColorRecord.from_rgb(values)
        palette = Palette.from_rgb([values])
        values[0] = 255
        self.assertEqual(record.rgb, (0, 128, 255))
        self.assertEqual(palette.records[0].rgb, record.rgb)
        self.assertEqual(rgb_to_hex(record.rgb), "#0080FF")

    def test_compound_separators_and_duplicates(self) -> None:
        expected = ((255, 0, 0), (0, 255, 0), (255, 0, 0))
        for separator in ("-", " ", ",", "_", "/", ":", ";", " , "):
            text = separator.join(("#f00", "0f0f", "#FF000080"))
            with self.subTest(separator=separator):
                self.assertEqual(parse_hex_colors(text), expected)
        self.assertEqual(
            parse_hex_colors(" #f00-0f0 / 00f;fff:000_abc,123 "),
            ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255),
             (0, 0, 0), (170, 187, 204), (17, 34, 51)),
        )
        for text in ("", "-", "f00-", "-f00", "f00,,00f", "f00/ /00f", "f00-badhex"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                _record(text)

    def test_modes_source_capture_and_rounding(self) -> None:
        source = " #010305 , #020406 / #000000 "
        with config_context(multi_color_mode="first"):
            first = _record(source)
        with config_context(multi_color_mode="last"):
            last = _record(source)
        with config_context(multi_color_mode="srgb_mean"):
            mean = _record(source)
            self.assertEqual(_record("000000-010305").rgb, (0, 2, 2))
            self.assertEqual(_record("1234").rgb, (17, 34, 51))
        self.assertEqual(first.hex, source)
        self.assertEqual(first.rgb, (1, 3, 5))
        self.assertEqual(last.rgb, (0, 0, 0))
        self.assertEqual(mean.rgb, (1, 2, 4))
        self.assertEqual(mean.lab, rgb_to_lab(mean.rgb))
        self.assertEqual(mean.effective_hex, "#010204")
        self.assertEqual(first.rgb_components, ((1, 3, 5), (2, 4, 6), (0, 0, 0)))
        with self.assertRaises(FrozenInstanceError):
            setattr(first, "rgb_components", ())
        self.assertFalse(hasattr(first, "hex2"))

    def test_loader_identifies_invalid_later_component(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "filaments.json"
            path.write_text(json.dumps([{
                "maker": "probe", "type": "PLA", "color": "probe", "hex": "#f00-INVALID",
            }]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index 0.*filaments.json"):
                load_filaments(directory)

    def test_loader_rejects_removed_hex2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "filaments.json"
            path.write_text(json.dumps([{
                "maker": "probe", "type": "PLA", "color": "probe",
                "hex": "#f00", "hex2": "#00f",
            }]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index 0.*hex2 was removed"):
                load_filaments(path)

    def test_color_loader_rejects_rgb_coercion_with_source_context(self) -> None:
        data = asdict(ColorRecord.from_rgb((1, 2, 3)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.json"
            for rgb in ([True, 2, 3], [1.0, 2, 3], [-1, 2, 3], [256, 2, 3],
                        [1, 2, 3, 4], "123"):
                data["rgb"] = rgb
                path.write_text(json.dumps([data]), encoding="utf-8")
                with self.subTest(rgb=rgb), self.assertRaisesRegex(
                    ValueError, "index 0.*colors.json",
                ):
                    load_colors(path)

    def test_color_loader_validates_hex_with_source_context(self) -> None:
        data = asdict(ColorRecord.from_rgb((1, 2, 3)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.json"
            for hex_code in (None, "", "#12G4", "#112233GG"):
                data["hex"] = hex_code
                path.write_text(json.dumps([data]), encoding="utf-8")
                with self.subTest(hex=hex_code), self.assertRaisesRegex(
                    ValueError, "index 0.*colors.json",
                ):
                    load_colors(path)

    def test_bundled_compound_records_keep_source_and_identity(self) -> None:
        with config_context(multi_color_mode="first"):
            first = next(record for record in load_filaments() if "-" in record.hex)
        components = first.rgb_components
        self.assertGreater(len(components), 1)
        self.assertEqual(first.rgb, components[0])
        self.assertNotEqual(first.rgb, (0, 0, 0))
        for mode in ("last", "srgb_mean"):
            with config_context(multi_color_mode=mode):
                record = next(
                    item for item in load_filaments()
                    if item.id == first.id and item.hex == first.hex
                )
            self.assertEqual(record.rgb_components, components)
            self.assertEqual(record.id, first.id)
            self.assertEqual(record.source, first.source)
            expected = components[-1] if mode == "last" else tuple(
                round(sum(color[channel] for color in components) / len(components))
                for channel in range(3)
            )
            self.assertEqual(record.rgb, expected)

    def test_single_color_export_formats_use_normalized_rgb(self) -> None:
        color = replace(ColorRecord.from_hex("#1234", name="probe"), hex="#1234")
        expected = {
            "paintnet": "FF112233", "css": "#112233", "hex": "112233",
            "lospec": "112233", "scribus": "#112233", "soc": "#112233",
        }
        with tempfile.TemporaryDirectory() as directory:
            for format_name, payload in expected.items():
                with self.subTest(format=format_name):
                    path = Path(directory) / f"palette.{format_name}"
                    get_exporter(format_name).export_colors([color], path)
                    content = path.read_text(encoding="utf-8")
                    self.assertIn(payload, content)
                    self.assertNotIn("#1234", content)

    def test_exports_distinguish_source_and_effective_color(self) -> None:
        with config_context(multi_color_mode="last"):
            record = _record("#f00-#00f")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "filaments.json"
            JSONExporter().export_filaments([record], json_path)
            exported = json.loads(json_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(exported["hex"], record.hex)
            self.assertEqual(exported["effective_hex"], "#0000FF")
            self.assertEqual(exported["rgb_components"], [[255, 0, 0], [0, 0, 255]])
            self.assertNotIn("hex2", exported)
            csv_path = root / "filaments.csv"
            CSVExporter().export_filaments([record], csv_path)
            with csv_path.open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["hex"], record.hex)
            self.assertEqual(row["effective_hex"], "#0000FF")
            autoforge_path = root / "autoforge.csv"
            AutoForgeExporter().export_filaments([record], autoforge_path)
            with autoforge_path.open(encoding="utf-8", newline="") as stream:
                self.assertEqual(next(csv.DictReader(stream))["Color"], "#0000FF")

    def test_python_hex_export_uses_rgb_not_source_rgba(self) -> None:
        color = replace(ColorRecord.from_rgb((17, 34, 51), name="probe"), hex="#1230")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "palette.py"
            get_exporter("python").export_colors(
                [color], path, options=PythonExportOptions(value_format="hex"),
            )
            content = path.read_text(encoding="utf-8")
        self.assertIn("#112233", content)
        self.assertNotIn("#1230", content)

    def test_color_of_day_swatch_uses_rgb_not_source_rgba(self) -> None:
        from api.color_of_day import _build_svg

        color = replace(ColorRecord.from_rgb((17, 34, 51), name="probe"), hex="#1230")
        svg = _build_svg(color)
        self.assertIn('fill="#112233"', svg)
        self.assertNotIn("#1230", svg)
