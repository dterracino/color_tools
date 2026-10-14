"""Schema and loading tests for bundled and user palette documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
import unittest

from color_tools import load_palette


class TestPaletteDocuments(unittest.TestCase):
    """Validate every checked-in active palette document."""

    data_dir = Path(__file__).parents[1] / "color_tools" / "data"

    def test_all_bundled_palettes_use_schema_version_one(self) -> None:
        """Every bundled palette has valid identity metadata and indexed colors."""
        palette_files = sorted((self.data_dir / "palettes").glob("*.json"))
        self.assertEqual(len(palette_files), 29)

        for path in palette_files:
            with self.subTest(palette=path.stem):
                data: object = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                document = cast(dict[str, object], data)
                self.assertEqual(document.get("schema_version"), 1)

                metadata = document.get("metadata")
                self.assertIsInstance(metadata, dict)
                metadata_fields = cast(dict[str, object], metadata)
                self.assertEqual(metadata_fields.get("id"), path.stem)
                self.assertIsInstance(metadata_fields.get("name"), str)
                self.assertIsInstance(metadata_fields.get("description"), str)

                palette = load_palette(path.stem, self.data_dir)
                self.assertGreater(len(palette.records), 0)

    def test_user_palettes_use_same_document_envelope(self) -> None:
        """Active and example user palettes share the canonical envelope."""
        palette_dir = self.data_dir / "user" / "palettes"
        for path in sorted(palette_dir.glob("user-*.json")):
            with self.subTest(palette=path.stem):
                data: object = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                document = cast(dict[str, object], data)
                self.assertEqual(document.get("schema_version"), 1)
                metadata = cast(dict[str, object], document["metadata"])
                self.assertEqual(metadata["id"], path.stem)

    def test_user_palette_colors_store_only_authored_fields(self) -> None:
        """User colors remain name/hex inputs rather than cached conversions."""
        path = self.data_dir / "user" / "palettes" / "user-6bitrgb.json"
        document = cast(
            dict[str, object],
            json.loads(path.read_text(encoding="utf-8")),
        )
        palette = cast(dict[str, object], document["palette"])
        colors = cast(list[dict[str, object]], palette["colors"])
        self.assertTrue(colors)
        self.assertTrue(all(set(color) == {"name", "hex"} for color in colors))


if __name__ == "__main__":
    unittest.main()
