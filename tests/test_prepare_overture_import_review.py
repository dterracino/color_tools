"""Tests for Overture type/finish review preparation."""

from __future__ import annotations

import unittest

from tooling import prepare_overture_import_review as preparer


class TestOvertureImportReviewPreparation(unittest.TestCase):
    """Product headings must map to database columns without data loss."""

    def test_appearance_products_become_finishes(self) -> None:
        self.assertEqual(preparer._map_product("Matte PLA"), ("PLA", "Matte"))
        self.assertEqual(preparer._map_product("Silk PLA"), ("PLA", "Silk"))
        self.assertEqual(preparer._map_product("Rock PLA"), ("PLA", "Rock"))

    def test_functional_product_grades_remain_types(self) -> None:
        self.assertEqual(
            preparer._map_product("Super PLA+"), ("Super PLA+", None)
        )
        self.assertEqual(preparer._map_product("Air PLA"), ("Air PLA", None))
        self.assertEqual(
            preparer._map_product("High Speed TPU"), ("High Speed TPU", None)
        )
        self.assertEqual(
            preparer._map_product("PC Professional"),
            ("PC Professional", None),
        )

    def test_preparation_canonicalizes_ordered_compound_hex(self) -> None:
        source = preparer._ReviewedRow(
            5,
            "Matte PLA",
            "Matte Black-White",
            "#000000 / #FFFFFF",
            "OK",
        )

        prepared = preparer._prepare_rows([source])

        self.assertEqual(prepared[0].type_name, "PLA")
        self.assertEqual(prepared[0].finish, "Matte")
        self.assertEqual(prepared[0].hex_value, "#000000-#FFFFFF")

    def test_unmapped_product_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unmapped Overture product"):
            preparer._map_product("Mystery PLA")


if __name__ == "__main__":
    unittest.main()
