"""Tests for the guarded IEMAI filament importer."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tooling import import_iemai_filaments as importer
from tooling import preview_iemai_filaments as previewer


def _candidate(color: str, hex_value: str, row_number: int) -> previewer._Candidate:
    return previewer._Candidate(
        "PLA+/Pro",
        "Basic",
        color,
        hex_value,
        hex_value,
        "Approximation - test",
        "https://example.com/source",
        row_number,
    )


class TestIemaiFilamentImport(unittest.TestCase):
    """IEMAI imports must be additive, guarded, and idempotent."""

    def test_candidate_record_preserves_approved_type_and_multicolor(self) -> None:
        record = _candidate("Rainbow", "#112233-#445566", 2).to_record()

        self.assertEqual(record["type"], "PLA+/Pro")
        self.assertEqual(record["hex"], "#112233-#445566")
        self.assertIsNone(record["td_value"])

    def test_execute_defaults_to_read_only_and_apply_is_idempotent(self) -> None:
        candidates = [_candidate("Blue", "#123456", 2)]
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "filaments.json"
            database_path.write_text("[]\n", encoding="utf-8")

            with patch.object(importer, "_load_candidates", return_value=candidates):
                self.assertEqual(
                    importer._execute(
                        Path("source.csv"),
                        Path("source.txt"),
                        database_path,
                        apply=False,
                    ),
                    0,
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), [])

            with patch.object(importer, "_load_candidates", return_value=candidates):
                self.assertEqual(
                    importer._execute(
                        Path("source.csv"),
                        Path("source.txt"),
                        database_path,
                        apply=True,
                    ),
                    0,
                )
            applied = json.loads(database_path.read_text(encoding="utf-8"))
            self.assertEqual(len(applied), 1)

            with patch.object(importer, "_load_candidates", return_value=candidates):
                self.assertEqual(
                    importer._execute(
                        Path("source.csv"),
                        Path("source.txt"),
                        database_path,
                        apply=True,
                    ),
                    0,
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), applied)


if __name__ == "__main__":
    unittest.main()
