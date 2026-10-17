"""Tests for shared and HueForge-specific filament reconciliation."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from dataclasses import replace
import tempfile
from pathlib import Path
from unittest.mock import patch

from color_tools.exporters import FilamentExportData, FilamentMetadata, get_exporter
from color_tools.filament_palette import FilamentRecord
from color_tools.importers import import_filaments
from color_tools.reconcilers import (
    FilamentMatchCandidate,
    FilamentReconciler,
    FilamentReconciliationPlan,
    FilamentReconciliationPolicy,
    HueForgeFilamentReconciler,
    ImportNew,
    Skip,
    UseExisting,
)
from color_tools.reconcilers._string_similarity import similarity


def _record(
    filament_id: str,
    *,
    maker: str = "Bambu Lab",
    type_name: str = "PLA",
    finish: str | None = None,
    color: str = "White",
    hex_value: str = "#FFFFFF",
    td: float = 5.0,
) -> FilamentRecord:
    """Build a compact reconciliation fixture record."""
    return FilamentRecord(
        id=filament_id,
        maker=maker,
        type=type_name,
        finish=finish,
        color=color,
        hex=hex_value,
        td_value=td,
        source="fixture.json",
    )


class _FixedReconciler(FilamentReconciler):
    """Test reconciler returning candidates keyed by provisional ID."""

    def __init__(
        self,
        catalog: Sequence[FilamentRecord],
        candidates: dict[str, tuple[FilamentMatchCandidate, ...]],
    ) -> None:
        super().__init__(catalog)
        self._candidates = candidates

    def _rank_candidates(
        self,
        record: FilamentRecord,
    ) -> Sequence[FilamentMatchCandidate]:
        return self._candidates.get(record.id, ())


class TestFilamentReconcilerBase(unittest.TestCase):
    def setUp(self) -> None:
        self.existing = _record("maker-pla-white", maker="Maker")

    def test_matched_and_new_defaults_remap_owned_ids(self) -> None:
        matched = _record("provisional-match", maker="Maker")
        new = _record("provisional-new", maker="Custom", color="Ocean")
        data = FilamentExportData(
            [matched, new],
            FilamentMetadata(owned_filament_ids=(matched.id, new.id)),
        )
        candidate = FilamentMatchCandidate(
            self.existing.id,
            100.0,
            "exact",
        )
        reconciler = _FixedReconciler(
            [self.existing],
            {matched.id: (candidate,)},
        )

        plan = reconciler.plan(data)
        result = reconciler.resolve(plan)

        self.assertEqual([entry.status for entry in plan.entries], ["matched", "new"])
        self.assertEqual([record.id for record in result.data.filaments], ["custom-pla-ocean"])
        self.assertEqual(
            result.data.metadata.owned_filament_ids,
            ("maker-pla-white", "custom-pla-ocean"),
        )
        self.assertEqual(result.count("use_existing"), 1)
        self.assertEqual(result.count("import_new"), 1)

    def test_proposed_ids_reserve_suffixes_across_one_plan(self) -> None:
        records = [
            _record("first", maker="Custom", color="Ocean"),
            _record("second", maker="Custom", color="Ocean"),
        ]
        plan = _FixedReconciler([], {}).plan(FilamentExportData(records))

        self.assertEqual(
            [entry.proposed_filament_id for entry in plan.entries],
            ["custom-pla-ocean", "custom-pla-ocean-2"],
        )

    def test_ambiguous_match_requires_explicit_resolution(self) -> None:
        source = _record("source", maker="Maker")
        second = _record("maker-pla-off-white", maker="Maker", color="Off White")
        candidates = (
            FilamentMatchCandidate(self.existing.id, 90.0, "fuzzy"),
            FilamentMatchCandidate(second.id, 88.0, "fuzzy"),
        )
        reconciler = _FixedReconciler(
            [self.existing, second],
            {source.id: candidates},
        )
        plan = reconciler.plan(FilamentExportData([source]))

        self.assertEqual(plan.unresolved_count, 1)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            reconciler.resolve(plan)
        result = reconciler.resolve(plan, {0: UseExisting(second.id)})
        self.assertEqual(result.mappings[0].final_filament_id, second.id)

    def test_caller_can_import_or_skip_regardless_of_default(self) -> None:
        source = _record("source", maker="Maker")
        candidate = FilamentMatchCandidate(self.existing.id, 100.0, "exact")
        reconciler = _FixedReconciler(
            [self.existing],
            {source.id: (candidate,)},
        )
        plan = reconciler.plan(FilamentExportData([source]))

        imported = reconciler.resolve(plan, {0: ImportNew()})
        skipped = reconciler.resolve(plan, {0: Skip()})

        self.assertEqual(len(imported.data.filaments), 1)
        self.assertEqual(skipped.count("skip"), 1)
        self.assertEqual(skipped.data.filaments, [])

    def test_use_existing_validates_catalog_id(self) -> None:
        source = _record("source", maker="Custom")
        reconciler = _FixedReconciler([self.existing], {})
        plan = reconciler.plan(FilamentExportData([source]))

        with self.assertRaisesRegex(ValueError, "unknown existing filament ID"):
            reconciler.resolve(plan, {0: UseExisting("missing-id")})

    def test_rejects_duplicate_catalog_ids_and_foreign_plan(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate filament IDs"):
            _FixedReconciler([self.existing, self.existing], {})

        source = FilamentExportData([_record("source", maker="Custom")])
        first = _FixedReconciler([self.existing], {})
        other_record = _record("other-pla-white", maker="Other")
        second = _FixedReconciler([other_record], {})
        with self.assertRaisesRegex(ValueError, "different catalog"):
            second.resolve(first.plan(source))

    def test_rejects_resolution_for_unknown_source_index(self) -> None:
        reconciler = _FixedReconciler([], {})
        plan = reconciler.plan(
            FilamentExportData([_record("source", maker="Custom")])
        )

        with self.assertRaisesRegex(ValueError, "unknown source index"):
            reconciler.resolve(plan, {9: Skip()})

    def test_explicit_skipped_status_defaults_to_skip(self) -> None:
        reconciler = _FixedReconciler([], {})
        original = reconciler.plan(
            FilamentExportData([_record("source", maker="Custom")])
        )
        skipped_entry = replace(original.entries[0], status="skipped")
        plan = FilamentReconciliationPlan(
            source=original.source,
            catalog=original.catalog,
            entries=(skipped_entry,),
            fuzzy_matching_available=original.fuzzy_matching_available,
        )

        result = reconciler.resolve(plan)

        self.assertEqual(result.count("skip"), 1)
        self.assertEqual(plan.count("skipped"), 1)

    def test_policy_and_candidate_scores_are_validated(self) -> None:
        invalid_policies = (
            {"candidate_score": -1.0},
            {"automatic_score": 101.0},
            {"candidate_score": 90.0, "automatic_score": 80.0},
            {"automatic_margin": -1.0},
        )
        for values in invalid_policies:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    FilamentReconciliationPolicy(**values)
        with self.assertRaisesRegex(ValueError, "candidate score"):
            FilamentMatchCandidate("id", 101.0, "fuzzy")


class TestHueForgeFilamentReconciler(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = [
            _record("bambu-lab-pla-matte-white", finish="Matte"),
            _record("bambu-lab-pla-basic-white", finish="Basic"),
            _record("bambu-lab-pla-silk-white", finish="Silk"),
        ]

    def _plan(self, source: FilamentRecord):
        return HueForgeFilamentReconciler(self.catalog).plan(
            FilamentExportData([source])
        )

    def test_matches_finish_embedded_in_brand(self) -> None:
        entry = self._plan(
            _record("source", maker="BambuLab Matte")
        ).entries[0]

        self.assertEqual(entry.status, "matched")
        self.assertEqual(entry.automatic_filament_id, "bambu-lab-pla-matte-white")
        self.assertEqual(entry.candidates[0].kind, "normalized")

    def test_matches_finish_embedded_in_color_name(self) -> None:
        entry = self._plan(
            _record("source", color="Matte White")
        ).entries[0]

        self.assertEqual(entry.automatic_filament_id, "bambu-lab-pla-matte-white")

    def test_fuzzy_fallback_matches_finish_used_as_hueforge_type(self) -> None:
        entry = self._plan(
            _record("source", type_name="Silk")
        ).entries[0]

        self.assertEqual(entry.status, "matched")
        self.assertEqual(entry.automatic_filament_id, "bambu-lab-pla-silk-white")
        self.assertEqual(entry.candidates[0].kind, "fuzzy")

    def test_maker_synonym_can_produce_automatic_match(self) -> None:
        source = _record("source", maker="BBL", finish="Matte")
        entry = HueForgeFilamentReconciler(
            self.catalog,
            maker_synonyms={"Bambu Lab": ["BBL"]},
        ).plan(FilamentExportData([source])).entries[0]

        self.assertEqual(entry.status, "matched")
        self.assertEqual(entry.automatic_filament_id, "bambu-lab-pla-matte-white")
        self.assertEqual(entry.candidates[0].kind, "synonym")

    def test_candidate_order_is_deterministic_when_scores_tie(self) -> None:
        first = _record("z-id", maker="Other", color="Red", hex_value="#FF0000")
        second = _record("a-id", maker="Other", color="Red", hex_value="#FF0000")
        source = _record("source", maker="Other", color="Red", hex_value="#FF0000")

        entry = HueForgeFilamentReconciler([first, second]).plan(
            FilamentExportData([source])
        ).entries[0]

        self.assertEqual(entry.status, "ambiguous")
        self.assertEqual(
            [candidate.filament_id for candidate in entry.candidates[:2]],
            ["a-id", "z-id"],
        )

    def test_standard_library_fallback_remains_available_without_rapidfuzz(self) -> None:
        with patch(
            "color_tools.reconcilers._string_similarity._rapidfuzz",
            None,
        ):
            score = similarity("Bambu Matte", "Bambu Lab Matte")

        self.assertGreater(score, 80.0)
        with patch(
            "color_tools.reconcilers._string_similarity._rapidfuzz",
            None,
        ):
            self.assertEqual(similarity("", "Bambu"), 0.0)

    def test_hueforge_export_import_reconciles_to_original_catalog_id(self) -> None:
        existing = _record("maker-pla-white", maker="Maker")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            get_exporter("hueforge").export_filaments([existing], path)
            source = import_filaments(path, format_name="hueforge")

        reconciler = HueForgeFilamentReconciler([existing])
        result = reconciler.resolve(reconciler.plan(source))

        self.assertEqual(result.data.filaments, [])
        self.assertEqual(result.data.metadata.owned_filament_ids, (existing.id,))


if __name__ == "__main__":
    unittest.main()
