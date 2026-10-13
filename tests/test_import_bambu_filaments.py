"""Tests for the bounded Bambu Lab PDF importer."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tooling import import_bambu_filaments as importer


class TestBambuFilamentImport(unittest.TestCase):
    """Bambu imports must be deterministic, additive, and dry-run safe."""

    def setUp(self) -> None:
        self.spec = importer._SourceSpec(
            "source.pdf", "PETG", "Matte", "PETG Matte", 2
        )
        self.source_text = (
            "Bambu Lab\nFilament Hex Code Table\nPETG Matte\n"
            "Black\nHex:#000000\nPink\nHex:#fabbcb\n"
        )

    def test_parse_source_text_validates_and_normalizes_rows(self) -> None:
        candidates = importer._parse_source_text(self.source_text, self.spec)

        self.assertEqual([candidate.color for candidate in candidates], ["Black", "Pink"])
        self.assertEqual(
            [candidate.hex_value for candidate in candidates],
            ["#000000", "#FABBCB"],
        )

    def test_parse_source_text_rejects_wrong_product_or_row_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "product label"):
            importer._parse_source_text(
                self.source_text.replace("PETG Matte", "PLA Basic"), self.spec
            )
        with self.assertRaisesRegex(ValueError, "extracted 2 colors; expected 3"):
            importer._parse_source_text(
                self.source_text,
                importer._SourceSpec("source.pdf", "PETG", "Matte", "PETG Matte", 3),
            )

    def test_plan_separates_additions_unchanged_and_conflicts(self) -> None:
        candidates = importer._parse_source_text(self.source_text, self.spec)
        database: list[dict[str, object]] = [
            {
                "id": "bambu-lab-petg-matte-black",
                "maker": "Bambu Lab",
                "type": "PETG",
                "finish": "Matte",
                "color": "Black",
                "hex": "#000000",
                "td_value": None,
            }
        ]
        plan = importer._build_plan(candidates, database)
        self.assertEqual([item.color for item in plan.unchanged], ["Black"])
        self.assertEqual([item.color for item in plan.additions], ["Pink"])
        self.assertEqual(plan.conflicts, [])

        database[0]["hex"] = "#010101"
        conflict_plan = importer._build_plan(candidates, database)
        self.assertEqual([item.color for item in conflict_plan.additions], ["Pink"])
        self.assertEqual(len(conflict_plan.conflicts), 1)
        self.assertIn("source has #000000", conflict_plan.conflicts[0].reason)

    def test_execute_defaults_to_read_only_and_apply_is_idempotent(self) -> None:
        candidates = importer._parse_source_text(self.source_text, self.spec)
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "filaments.json"
            database_path.write_text("[]\n", encoding="utf-8")

            with patch.object(importer, "_extract_sources", return_value=candidates):
                self.assertEqual(
                    importer._execute(Path(directory), database_path, apply=False), 0
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), [])

            with patch.object(importer, "_extract_sources", return_value=candidates):
                self.assertEqual(
                    importer._execute(Path(directory), database_path, apply=True), 0
                )
            applied = json.loads(database_path.read_text(encoding="utf-8"))
            self.assertEqual(len(applied), 2)

            with patch.object(importer, "_extract_sources", return_value=candidates):
                self.assertEqual(
                    importer._execute(Path(directory), database_path, apply=True), 0
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), applied)


if __name__ == "__main__":
    unittest.main()
