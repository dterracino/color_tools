"""Tests for the guarded Polymaker PolyTerra importer."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tooling import import_polyterra_filaments as importer


def _row(
    sku: str,
    product: str,
    color: str,
    hex_value: str,
    td_value: str = "",
) -> dict[str, str]:
    return {
        "SKU": sku,
        "Product Name": product,
        "Color Name": color,
        "HEX Code": hex_value,
        "TD": td_value,
    }


class TestPolyterraFilamentImport(unittest.TestCase):
    """PolyTerra imports must be bounded, additive, and dry-run safe."""

    def test_parse_rows_filters_normalizes_deduplicates_and_merges_td(self) -> None:
        source = importer._parse_rows(
            [
                _row("OTHER", "PolyLite PLA", "Blue", "#abcdef", "2"),
                _row("PA1", "PolyTerra PLA", " Matte  Blue ", "#abcdef"),
                _row("PA2", "PolyTerra PLA", "Matte Blue", "#ABCDEF", "2"),
                _row(
                    "PA3",
                    "PolyTerra PLA",
                    "Matte Dual",
                    "#112233, #445566",
                ),
                _row("PA4", "PolyTerra Gradient Matte PLA", "Rainbow", ""),
            ]
        )

        self.assertEqual(source.source_rows, 4)
        self.assertEqual(source.duplicate_rows, 1)
        self.assertEqual(len(source.candidates), 2)
        self.assertEqual(source.candidates[0].skus, ("PA1", "PA2"))
        self.assertEqual(source.candidates[0].td_value, 2.0)
        self.assertEqual(source.candidates[1].hex_value, "#112233-#445566")
        self.assertEqual(source.exclusions[0].sku, "PA4")

    def test_parse_rows_rejects_unknown_product_and_duplicate_conflicts(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported PolyTerra product"):
            importer._parse_rows(
                [_row("PA1", "PolyTerra Mystery", "Blue", "#123456")]
            )

        with self.assertRaisesRegex(ValueError, "conflicting hex"):
            importer._parse_rows(
                [
                    _row("PA1", "PolyTerra PLA", "Blue", "#123456"),
                    _row("PA2", "PolyTerra PLA", "Blue", "#654321"),
                ]
            )
        with self.assertRaisesRegex(ValueError, "conflicting TD"):
            importer._parse_rows(
                [
                    _row("PA1", "PolyTerra PLA", "Blue", "#123456", "1"),
                    _row("PA2", "PolyTerra PLA", "Blue", "#123456", "2"),
                ]
            )

    def test_plan_rejects_td_changes_on_an_existing_record(self) -> None:
        candidate = importer._parse_rows(
            [_row("PA1", "PolyTerra PLA", "Matte Blue", "#123456", "2")]
        ).candidates[0]
        record = candidate.to_record()
        record["td_value"] = 3.0

        plan = importer._build_plan([candidate], [record])

        self.assertEqual(plan.unchanged, [])
        self.assertEqual(len(plan.conflicts), 1)
        self.assertIn("has TD 3.0", plan.conflicts[0].reason)

    def test_execute_defaults_to_read_only_and_apply_is_idempotent(self) -> None:
        source = importer._parse_rows(
            [_row("PA1", "PolyTerra PLA+", "Satin Blue", "#123456", "2.5")]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.csv"
            database_path = root / "filaments.json"
            database_path.write_text("[]\n", encoding="utf-8")

            with patch.object(importer, "_load_source", return_value=source):
                self.assertEqual(
                    importer._execute(source_path, database_path, apply=False), 0
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), [])

            with patch.object(importer, "_load_source", return_value=source):
                self.assertEqual(
                    importer._execute(source_path, database_path, apply=True), 0
                )
            applied = json.loads(database_path.read_text(encoding="utf-8"))
            self.assertEqual(len(applied), 1)
            self.assertEqual(applied[0]["id"], "polymaker-pla-plus-polyterra-satin-blue")

            with patch.object(importer, "_load_source", return_value=source):
                self.assertEqual(
                    importer._execute(source_path, database_path, apply=True), 0
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), applied)


if __name__ == "__main__":
    unittest.main()
