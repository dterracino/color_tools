"""Tests for predefined filament collections."""

import unittest
from unittest.mock import patch

from color_tools import FilamentCollections
from color_tools.filament_collections import _default_palette, _resolve_collection
from color_tools.filament_palette import FilamentPalette, FilamentRecord


class TestFilamentCollections(unittest.TestCase):
    """Verify predefined collection contents and lazy-loading behavior."""

    def test_bambu_pla_basic_collection(self) -> None:
        records = FilamentCollections.BAMBU_PLA_BASIC

        self.assertIsInstance(records, tuple)
        self.assertTrue(records)
        self.assertTrue(all(isinstance(record, FilamentRecord) for record in records))
        self.assertTrue(all(record.maker == "Bambu Lab" for record in records))
        self.assertTrue(all(record.type == "PLA" for record in records))
        self.assertTrue(all(record.finish == "Basic" for record in records))

    def test_bambu_pla_matte_collection(self) -> None:
        records = FilamentCollections.BAMBU_PLA_MATTE

        self.assertIsInstance(records, tuple)
        self.assertTrue(records)
        self.assertTrue(all(record.maker == "Bambu Lab" for record in records))
        self.assertTrue(all(record.type == "PLA" for record in records))
        self.assertTrue(all(record.finish == "Matte" for record in records))

    def test_bambu_pla_basicmatte_is_union_of_collections(self) -> None:
        basic = FilamentCollections.BAMBU_PLA_BASIC
        matte = FilamentCollections.BAMBU_PLA_MATTE
        combined = FilamentCollections.BAMBU_PLA_BASICMATTE

        self.assertEqual(
            {record.id for record in combined},
            {record.id for record in basic + matte},
        )
        self.assertEqual({record.finish for record in combined}, {"Basic", "Matte"})

    def test_collections_share_lazy_palette_and_cache_results(self) -> None:
        _resolve_collection.cache_clear()
        _default_palette.cache_clear()

        original_load_default = FilamentPalette.load_default
        try:
            with patch.object(
                FilamentPalette,
                "load_default",
                wraps=original_load_default,
            ) as load_default:
                basic_first = FilamentCollections.BAMBU_PLA_BASIC
                basic_second = FilamentCollections.BAMBU_PLA_BASIC
                _ = FilamentCollections.BAMBU_PLA_MATTE

                self.assertIs(basic_first, basic_second)
                load_default.assert_called_once_with()
        finally:
            _resolve_collection.cache_clear()
            _default_palette.cache_clear()
