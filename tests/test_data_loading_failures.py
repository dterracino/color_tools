"""Focused failure-contract tests for JSON color and filament loaders."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable
import unittest

from color_tools.filament_palette import load_filaments
from color_tools.palette import load_colors


def _valid_color() -> dict[str, object]:
    """Return one complete core color record."""
    return {
        "name": "Red",
        "hex": "#FF0000",
        "rgb": [255, 0, 0],
        "hsl": [0.0, 100.0, 50.0],
        "lab": [53.24, 80.09, 67.20],
        "lch": [53.24, 104.55, 40.0],
    }


def _valid_filament() -> dict[str, object]:
    """Return one complete core filament record."""
    return {
        "id": "test-pla-red",
        "maker": "Test",
        "type": "PLA",
        "finish": None,
        "color": "Red",
        "hex": "#FF0000",
        "td_value": 1.0,
    }


class TestDataLoadingFailures(unittest.TestCase):
    """Verify loader errors identify the bad file and record."""

    def _write_json(self, path: Path, data: object) -> None:
        """Create parent directories and write one JSON fixture."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _assert_unchanged_after_failure(
        self,
        path: Path,
        loader: Callable[[Path], object],
        message: str,
    ) -> None:
        """Assert a failed load is read-only and provides focused context."""
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, message):
            loader(path)
        self.assertEqual(path.read_bytes(), original)

    def test_core_color_root_must_be_an_array(self) -> None:
        """Core colors reject an object at the document root."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "colors.json"
            self._write_json(path, {"colors": []})
            self._assert_unchanged_after_failure(path, load_colors, "root level")

    def test_user_color_root_must_be_an_array(self) -> None:
        """User colors use the same root-array contract as core colors."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            self._write_json(data_dir / "colors.json", [_valid_color()])
            user_path = data_dir / "user" / "user-colors.json"
            self._write_json(user_path, {"colors": []})
            self._assert_unchanged_after_failure(
                user_path,
                lambda _path: load_colors(data_dir),
                "user-colors.json",
            )

    def test_core_filament_root_must_be_an_array(self) -> None:
        """Core filaments reject an object at the document root."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "filaments.json"
            self._write_json(path, {"filaments": []})
            self._assert_unchanged_after_failure(path, load_filaments, "root level")

    def test_user_filament_root_must_be_an_array(self) -> None:
        """User filaments use the same root-array contract as core filaments."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            self._write_json(data_dir / "filaments.json", [_valid_filament()])
            user_path = data_dir / "user" / "user-filaments.json"
            self._write_json(user_path, {"filaments": []})
            self._assert_unchanged_after_failure(
                user_path,
                lambda _path: load_filaments(data_dir),
                "user-filaments.json",
            )

    def test_color_missing_each_required_field(self) -> None:
        """Every required core color field produces indexed source context."""
        for field in ("name", "hex", "rgb", "hsl", "lab", "lch"):
            with self.subTest(field=field), TemporaryDirectory() as directory:
                record = _valid_color()
                record.pop(field)
                path = Path(directory) / "colors.json"
                self._write_json(path, [record])
                self._assert_unchanged_after_failure(
                    path,
                    load_colors,
                    rf"Missing required key ['\"]{field}['\"].*index 0.*colors.json",
                )

    def test_color_invalid_coordinate_and_scalar_values(self) -> None:
        """Malformed color values are wrapped with indexed source context."""
        mutations: tuple[tuple[str, object], ...] = (
            ("hex", "#nothex"),
            ("rgb", [256, 0, 0]),
            ("rgb", [255, 0]),
            ("hsl", [0.0, 100.0]),
            ("lab", None),
            ("lch", [53.24, 104.55]),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value), TemporaryDirectory() as directory:
                record = _valid_color()
                record[field] = value
                path = Path(directory) / "colors.json"
                self._write_json(path, [record])
                self._assert_unchanged_after_failure(
                    path,
                    load_colors,
                    r"Invalid color data at index 0.*colors.json",
                )

    def test_filament_missing_each_required_field(self) -> None:
        """Every required filament field produces indexed source context."""
        for field in ("maker", "type", "color", "hex"):
            with self.subTest(field=field), TemporaryDirectory() as directory:
                record = _valid_filament()
                record.pop(field)
                path = Path(directory) / "filaments.json"
                self._write_json(path, [record])
                self._assert_unchanged_after_failure(
                    path,
                    load_filaments,
                    rf"Missing required key ['\"]{field}['\"].*index 0.*filaments.json",
                )

    def test_filament_invalid_hex_has_indexed_source_context(self) -> None:
        """Invalid filament colors are wrapped with their record and filename."""
        with TemporaryDirectory() as directory:
            record = _valid_filament()
            record["hex"] = "#nothex"
            path = Path(directory) / "filaments.json"
            self._write_json(path, [record])
            self._assert_unchanged_after_failure(
                path,
                load_filaments,
                r"Invalid filament data at index 0.*filaments.json",
            )

    def test_removed_hex2_field_is_rejected(self) -> None:
        """Legacy secondary-color fields receive migration guidance."""
        with TemporaryDirectory() as directory:
            record = _valid_filament()
            record["hex2"] = "#0000FF"
            path = Path(directory) / "filaments.json"
            self._write_json(path, [record])
            self._assert_unchanged_after_failure(
                path,
                load_filaments,
                r"hex2 was removed; put all components in hex",
            )

    def test_successful_loads_do_not_rewrite_source_files(self) -> None:
        """Successful color and filament loads are read-only."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            color_path = data_dir / "colors.json"
            filament_path = data_dir / "filaments.json"
            self._write_json(color_path, [_valid_color()])
            self._write_json(filament_path, [_valid_filament()])
            original_colors = color_path.read_bytes()
            original_filaments = filament_path.read_bytes()

            self.assertEqual(len(load_colors(color_path)), 1)
            self.assertEqual(len(load_filaments(filament_path)), 1)

            self.assertEqual(color_path.read_bytes(), original_colors)
            self.assertEqual(filament_path.read_bytes(), original_filaments)
