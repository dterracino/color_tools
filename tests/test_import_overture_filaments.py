"""Tests for the guarded Overture review importer."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tooling import import_overture_filaments as importer
from tooling._filament_import_utils import _build_reconciling_import_plan


def _candidate(hex_value: str = "#112233") -> importer._Candidate:
    return importer._Candidate(3, "PLA", None, "Black", hex_value)


def _existing(hex_value: str = "#000000") -> dict[str, object]:
    return {
        "id": "stable-overture-black",
        "maker": "Overture",
        "type": "PLA",
        "finish": None,
        "color": "Black",
        "hex": hex_value,
        "td_value": 0.6,
        "owned": True,
    }


class TestOvertureFilamentImport(unittest.TestCase):
    """Reviewed corrections must preserve identity and unrelated metadata."""

    def test_parse_candidate_requires_database_shaped_canonical_data(self) -> None:
        candidate = importer._parse_candidate(
            "3 | Overture | PLA | Matte | Black | #112233-#445566 | null | OK",
            9,
        )

        self.assertEqual(candidate.type_name, "PLA")
        self.assertEqual(candidate.finish, "Matte")
        self.assertEqual(candidate.hex_value, "#112233-#445566")

    def test_reviewed_hex_difference_is_a_correction(self) -> None:
        plan = _build_reconciling_import_plan([_candidate()], [_existing()])

        self.assertEqual(plan.additions, [])
        self.assertEqual(plan.conflicts, [])
        self.assertEqual(len(plan.corrections), 1)
        self.assertEqual(plan.corrections[0].existing_id, "stable-overture-black")

    def test_replacement_preserves_id_td_and_unrelated_metadata(self) -> None:
        database = [_existing()]
        plan = _build_reconciling_import_plan([_candidate()], database)

        replacement = importer._build_replacements(plan, database)[
            "stable-overture-black"
        ]

        self.assertEqual(replacement["id"], "stable-overture-black")
        self.assertEqual(replacement["td_value"], 0.6)
        self.assertIs(replacement["owned"], True)
        self.assertEqual(replacement["hex"], "#112233")

    def test_execute_is_read_only_by_default_and_idempotent_after_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "filaments.json"
            database_path.write_text(
                json.dumps([_existing()], indent=2) + "\n", encoding="utf-8"
            )
            with patch.object(importer, "_load_candidates", return_value=[_candidate()]):
                self.assertEqual(
                    importer._execute(Path("review.txt"), database_path, apply=False),
                    0,
                )
            original = json.loads(database_path.read_text(encoding="utf-8"))
            self.assertEqual(original[0]["hex"], "#000000")

            with patch.object(importer, "_load_candidates", return_value=[_candidate()]):
                self.assertEqual(
                    importer._execute(Path("review.txt"), database_path, apply=True),
                    0,
                )
            applied = json.loads(database_path.read_text(encoding="utf-8"))
            self.assertEqual(applied[0]["hex"], "#112233")
            self.assertEqual(applied[0]["td_value"], 0.6)

            with patch.object(importer, "_load_candidates", return_value=[_candidate()]):
                self.assertEqual(
                    importer._execute(Path("review.txt"), database_path, apply=True),
                    0,
                )
            self.assertEqual(json.loads(database_path.read_text(encoding="utf-8")), applied)


if __name__ == "__main__":
    unittest.main()
