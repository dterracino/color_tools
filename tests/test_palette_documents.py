"""Schema and loading tests for bundled and user palette documents."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast
import unittest

from color_tools import load_palette
from color_tools._palette_document import parse_indexed_palette_document
from tests.palette_document_fixtures import palette_document


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


class TestPaletteDocumentValidation(unittest.TestCase):
    """Exercise each externally meaningful schema-validation failure."""

    source_file = "broken-palette.json"
    expected_id = "broken-palette"

    def _valid_document(self) -> dict[str, object]:
        """Return an independent valid document for one mutation."""
        return deepcopy(palette_document(self.expected_id, []))

    def _assert_invalid(self, document: object, message: str) -> None:
        """Assert a schema error identifies both its field and source file."""
        with self.assertRaisesRegex(ValueError, message) as context:
            parse_indexed_palette_document(
                document,
                expected_id=self.expected_id,
                source_file=self.source_file,
            )
        self.assertIn(self.source_file, str(context.exception))

    def test_schema_version_validation(self) -> None:
        """Schema versions must be present, integer, and currently supported."""
        cases: tuple[tuple[object, str], ...] = (
            (None, "schema_version"),
            (True, "schema_version"),
            ("1", "schema_version"),
            (2, "Unsupported palette schema version 2"),
        )
        for value, message in cases:
            with self.subTest(value=value):
                document = self._valid_document()
                if value is None:
                    document.pop("schema_version")
                else:
                    document["schema_version"] = value
                self._assert_invalid(document, message)

    def test_required_objects(self) -> None:
        """The document, metadata, and palette containers must be objects."""
        cases: tuple[tuple[str, object, str], ...] = (
            ("document", [], "palette document"),
            ("metadata", None, "metadata"),
            ("palette", [], "palette"),
        )
        for field, value, message in cases:
            with self.subTest(field=field, value=value):
                if field == "document":
                    document = value
                else:
                    document = self._valid_document()
                    document[field] = value
                self._assert_invalid(document, message)

    def test_object_keys_must_be_strings(self) -> None:
        """Direct Python callers cannot bypass string-key validation."""
        document = self._valid_document()
        metadata = cast(dict[object, object], document["metadata"])
        metadata[1] = "not a JSON object key"
        self._assert_invalid(document, "metadata")

    def test_metadata_id_validation(self) -> None:
        """Palette IDs must be nonempty strings matching the filename stem."""
        cases: tuple[tuple[object, str], ...] = (
            (None, "metadata.id"),
            (123, "metadata.id"),
            ("", "metadata.id"),
            ("   ", "metadata.id"),
            ("different-id", "must match filename stem"),
        )
        for value, message in cases:
            with self.subTest(value=value):
                document = self._valid_document()
                metadata = cast(dict[str, object], document["metadata"])
                if value is None:
                    metadata.pop("id")
                else:
                    metadata["id"] = value
                self._assert_invalid(document, message)

    def test_metadata_name_validation(self) -> None:
        """Palette display names must be nonempty, non-whitespace strings."""
        for value in (None, 123, "", "   "):
            with self.subTest(value=value):
                document = self._valid_document()
                metadata = cast(dict[str, object], document["metadata"])
                if value is None:
                    metadata.pop("name")
                else:
                    metadata["name"] = value
                self._assert_invalid(document, "metadata.name")

    def test_optional_description_validation(self) -> None:
        """A supplied description must be a nonempty, non-whitespace string."""
        for value in (123, "", "   "):
            with self.subTest(value=value):
                document = self._valid_document()
                metadata = cast(dict[str, object], document["metadata"])
                metadata["description"] = value
                self._assert_invalid(document, "metadata.description")

    def test_optional_release_year_validation(self) -> None:
        """A supplied release year must be a built-in integer, not a Boolean."""
        for value in (True, 1983.0, "1983"):
            with self.subTest(value=value):
                document = self._valid_document()
                metadata = cast(dict[str, object], document["metadata"])
                metadata["release_year"] = value
                self._assert_invalid(document, "metadata.release_year")

    def test_palette_type_validation(self) -> None:
        """Only an explicitly indexed palette is accepted by schema version 1."""
        for value in (None, 1, "reference"):
            with self.subTest(value=value):
                document = self._valid_document()
                palette = cast(dict[str, object], document["palette"])
                if value is None:
                    palette.pop("type")
                else:
                    palette["type"] = value
                self._assert_invalid(document, "Unsupported palette type")

    def test_palette_colors_validation(self) -> None:
        """Indexed colors must be present as an array."""
        values: tuple[object, ...] = (None, {}, "#000000")
        for value in values:
            with self.subTest(value=value):
                document = self._valid_document()
                palette = cast(dict[str, object], document["palette"])
                if value is None:
                    palette.pop("colors")
                else:
                    palette["colors"] = value
                self._assert_invalid(document, "palette.colors")


if __name__ == "__main__":
    unittest.main()
