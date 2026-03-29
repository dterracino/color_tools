"""
Tests for color_tools.cli_commands.utils module.

Covers:
- validate_color_input_exclusivity
- get_rgb_from_args
- parse_hex_or_exit
- is_valid_lab
- is_valid_lch
- get_program_name
"""
from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from unittest.mock import patch

from color_tools.cli_commands.utils import (
    get_program_name,
    get_rgb_from_args,
    is_valid_lab,
    is_valid_lch,
    parse_hex_or_exit,
    validate_color_input_exclusivity,
)


class TestValidateColorInputExclusivity(unittest.TestCase):
    """Tests for validate_color_input_exclusivity."""

    def test_both_none_ok(self):
        """No error when both value and hex are None."""
        args = Namespace(value=None, hex=None)
        validate_color_input_exclusivity(args)  # Should not raise

    def test_value_only_ok(self):
        """No error when only value is set."""
        args = Namespace(value=[255, 0, 0], hex=None)
        validate_color_input_exclusivity(args)  # Should not raise

    def test_hex_only_ok(self):
        """No error when only hex is set."""
        args = Namespace(value=None, hex="#FF0000")
        validate_color_input_exclusivity(args)  # Should not raise

    def test_both_set_exits_code_2(self):
        """Exits with code 2 when both value and hex are set."""
        args = Namespace(value=[255, 0, 0], hex="#FF0000")
        with self.assertRaises(SystemExit) as ctx:
            validate_color_input_exclusivity(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_value_attr_ok(self):
        """No error when args has no value attribute (hasattr guard)."""
        args = Namespace(hex="#FF0000")
        validate_color_input_exclusivity(args)  # Should not raise

    def test_missing_hex_attr_ok(self):
        """No error when args has no hex attribute (hasattr guard)."""
        args = Namespace(value=[255, 0, 0])
        validate_color_input_exclusivity(args)  # Should not raise


class TestGetRgbFromArgs(unittest.TestCase):
    """Tests for get_rgb_from_args."""

    def test_value_input_returns_tuple(self):
        """Extracts RGB tuple from --value argument."""
        args = Namespace(value=[255, 128, 64], hex=None)
        result = get_rgb_from_args(args)
        self.assertEqual(result, (255, 128, 64))

    def test_hex_input_with_hash(self):
        """Extracts RGB from hex argument with # prefix."""
        args = Namespace(value=None, hex="#FF8040")
        result = get_rgb_from_args(args)
        self.assertEqual(result, (255, 128, 64))

    def test_hex_input_without_hash(self):
        """Extracts RGB from hex argument without # prefix."""
        args = Namespace(value=None, hex="FF0000")
        result = get_rgb_from_args(args)
        self.assertEqual(result, (255, 0, 0))

    def test_short_hex_input(self):
        """Handles 3-digit shorthand hex."""
        args = Namespace(value=None, hex="#F00")
        result = get_rgb_from_args(args)
        self.assertEqual(result, (255, 0, 0))

    def test_both_none_exits_code_2(self):
        """Exits with code 2 when neither value nor hex is provided."""
        args = Namespace(value=None, hex=None)
        with self.assertRaises(SystemExit) as ctx:
            get_rgb_from_args(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_both_set_exits_code_2(self):
        """Exits with code 2 when both value and hex are set."""
        args = Namespace(value=[255, 0, 0], hex="#FF0000")
        with self.assertRaises(SystemExit) as ctx:
            get_rgb_from_args(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_invalid_hex_exits_code_2(self):
        """Exits with code 2 on invalid hex string."""
        args = Namespace(value=None, hex="GGGGGG")
        with self.assertRaises(SystemExit) as ctx:
            get_rgb_from_args(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_value_black(self):
        """Handles pure black RGB value."""
        args = Namespace(value=[0, 0, 0], hex=None)
        result = get_rgb_from_args(args)
        self.assertEqual(result, (0, 0, 0))

    def test_value_white(self):
        """Handles pure white RGB value."""
        args = Namespace(value=[255, 255, 255], hex=None)
        result = get_rgb_from_args(args)
        self.assertEqual(result, (255, 255, 255))


class TestParseHexOrExit(unittest.TestCase):
    """Tests for parse_hex_or_exit."""

    def test_full_hex_with_hash(self):
        """Parses 6-digit hex with # prefix."""
        result = parse_hex_or_exit("#FF0000")
        self.assertEqual(result, (255, 0, 0))

    def test_full_hex_without_hash(self):
        """Parses 6-digit hex without # prefix."""
        result = parse_hex_or_exit("00FF00")
        self.assertEqual(result, (0, 255, 0))

    def test_short_hex_with_hash(self):
        """Parses 3-digit shorthand hex with # prefix."""
        result = parse_hex_or_exit("#F00")
        self.assertEqual(result, (255, 0, 0))

    def test_short_hex_without_hash(self):
        """Parses 3-digit shorthand hex without # prefix."""
        result = parse_hex_or_exit("0F0")
        self.assertEqual(result, (0, 255, 0))

    def test_lowercase_hex(self):
        """Parses lowercase hex string."""
        result = parse_hex_or_exit("ff8040")
        self.assertEqual(result, (255, 128, 64))

    def test_black(self):
        """Parses #000000 as black."""
        result = parse_hex_or_exit("#000000")
        self.assertEqual(result, (0, 0, 0))

    def test_white(self):
        """Parses #FFFFFF as white."""
        result = parse_hex_or_exit("#FFFFFF")
        self.assertEqual(result, (255, 255, 255))

    def test_invalid_hex_exits_code_2(self):
        """Exits with code 2 on invalid hex string."""
        with self.assertRaises(SystemExit) as ctx:
            parse_hex_or_exit("GGGGGG")
        self.assertEqual(ctx.exception.code, 2)

    def test_empty_string_exits_code_2(self):
        """Exits with code 2 on empty hex string."""
        with self.assertRaises(SystemExit) as ctx:
            parse_hex_or_exit("")
        self.assertEqual(ctx.exception.code, 2)

    def test_returns_int_tuple(self):
        """Returns a 3-tuple of ints."""
        result = parse_hex_or_exit("#AABBCC")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(isinstance(v, int) for v in result))


class TestIsValidLab(unittest.TestCase):
    """Tests for is_valid_lab."""

    def test_valid_neutral_grey(self):
        """Accepts typical valid mid-range LAB values."""
        self.assertTrue(is_valid_lab((50.0, 0.0, 0.0)))

    def test_valid_boundary_L_min(self):
        """Accepts L=0 (inclusive minimum)."""
        self.assertTrue(is_valid_lab((0.0, 0.0, 0.0)))

    def test_valid_boundary_L_max(self):
        """Accepts L=100 (inclusive maximum)."""
        self.assertTrue(is_valid_lab((100.0, 0.0, 0.0)))

    def test_valid_a_min_boundary(self):
        """Accepts a=-128 (inclusive minimum)."""
        self.assertTrue(is_valid_lab((50.0, -128.0, 0.0)))

    def test_valid_a_max_boundary(self):
        """Accepts a=127 (inclusive maximum)."""
        self.assertTrue(is_valid_lab((50.0, 127.0, 0.0)))

    def test_valid_b_min_boundary(self):
        """Accepts b=-128 (inclusive minimum)."""
        self.assertTrue(is_valid_lab((50.0, 0.0, -128.0)))

    def test_valid_b_max_boundary(self):
        """Accepts b=127 (inclusive maximum)."""
        self.assertTrue(is_valid_lab((50.0, 0.0, 127.0)))

    def test_invalid_L_too_high(self):
        """Rejects L > 100."""
        self.assertFalse(is_valid_lab((101.0, 0.0, 0.0)))

    def test_invalid_L_negative(self):
        """Rejects L < 0."""
        self.assertFalse(is_valid_lab((-1.0, 0.0, 0.0)))

    def test_invalid_a_too_low(self):
        """Rejects a < -128."""
        self.assertFalse(is_valid_lab((50.0, -129.0, 0.0)))

    def test_invalid_a_too_high(self):
        """Rejects a > 127."""
        self.assertFalse(is_valid_lab((50.0, 128.0, 0.0)))

    def test_invalid_b_too_low(self):
        """Rejects b < -128."""
        self.assertFalse(is_valid_lab((50.0, 0.0, -129.0)))

    def test_invalid_b_too_high(self):
        """Rejects b > 127."""
        self.assertFalse(is_valid_lab((50.0, 0.0, 128.0)))

    def test_not_a_sequence(self):
        """Rejects non-sequence input."""
        self.assertFalse(is_valid_lab("invalid"))

    def test_wrong_length_too_short(self):
        """Rejects tuple with only 2 elements."""
        self.assertFalse(is_valid_lab((50.0, 0.0)))

    def test_wrong_length_too_long(self):
        """Rejects tuple with 4 elements."""
        self.assertFalse(is_valid_lab((50.0, 0.0, 0.0, 0.0)))

    def test_list_input_ok(self):
        """Accepts list input as well as tuple."""
        self.assertTrue(is_valid_lab([50.0, 0.0, 0.0]))

    def test_non_numeric_values(self):
        """Rejects non-numeric channel values."""
        self.assertFalse(is_valid_lab((50.0, "a", 0.0)))

    def test_integer_values_ok(self):
        """Accepts integer values (ints are valid)."""
        self.assertTrue(is_valid_lab((50, 0, 0)))


class TestIsValidLch(unittest.TestCase):
    """Tests for is_valid_lch."""

    def test_valid_typical_lch(self):
        """Accepts typical valid LCH values."""
        self.assertTrue(is_valid_lch((50.0, 50.0, 180.0)))

    def test_valid_boundary_all_zero(self):
        """Accepts L=0, C=0, h=0 (all inclusive minimums)."""
        self.assertTrue(is_valid_lch((0.0, 0.0, 0.0)))

    def test_valid_L_max(self):
        """Accepts L=100 (inclusive maximum)."""
        self.assertTrue(is_valid_lch((100.0, 50.0, 180.0)))

    def test_valid_h_just_below_360(self):
        """Accepts h just below 360 (exclusive upper bound)."""
        self.assertTrue(is_valid_lch((50.0, 50.0, 359.9)))

    def test_invalid_L_too_high(self):
        """Rejects L > 100."""
        self.assertFalse(is_valid_lch((101.0, 50.0, 180.0)))

    def test_invalid_L_negative(self):
        """Rejects L < 0."""
        self.assertFalse(is_valid_lch((-1.0, 50.0, 180.0)))

    def test_invalid_C_negative(self):
        """Rejects chroma C < 0."""
        self.assertFalse(is_valid_lch((50.0, -1.0, 180.0)))

    def test_invalid_h_equals_360(self):
        """Rejects h == 360 (exclusive upper bound - h=360 is same as h=0)."""
        self.assertFalse(is_valid_lch((50.0, 50.0, 360.0)))

    def test_invalid_h_greater_360(self):
        """Rejects h > 360."""
        self.assertFalse(is_valid_lch((50.0, 50.0, 361.0)))

    def test_not_a_sequence(self):
        """Rejects non-sequence input."""
        self.assertFalse(is_valid_lch("invalid"))

    def test_wrong_length_too_short(self):
        """Rejects tuple with only 2 elements."""
        self.assertFalse(is_valid_lch((50.0, 50.0)))

    def test_list_input_ok(self):
        """Accepts list input as well as tuple."""
        self.assertTrue(is_valid_lch([50.0, 50.0, 180.0]))

    def test_non_numeric_values(self):
        """Rejects non-numeric channel values."""
        self.assertFalse(is_valid_lch((50.0, "x", 180.0)))

    def test_integer_values_ok(self):
        """Accepts integer values."""
        self.assertTrue(is_valid_lch((50, 50, 180)))


class TestGetProgramName(unittest.TestCase):
    """Tests for get_program_name."""

    def test_returns_module_name_when_invoked_as_module(self):
        """Returns 'python -m color_tools' when argv[0] ends with __main__.py."""
        with patch.object(sys, 'argv', ['path/to/__main__.py']):
            result = get_program_name()
        self.assertEqual(result, "python -m color_tools")

    def test_returns_module_name_with_full_path(self):
        """Returns 'python -m color_tools' for any path ending in __main__.py."""
        with patch.object(sys, 'argv', ['C:\\Users\\user\\color_tools\\__main__.py']):
            result = get_program_name()
        self.assertEqual(result, "python -m color_tools")

    def test_returns_script_stem_for_direct_invocation(self):
        """Returns the filename stem when invoked as a script."""
        with patch.object(sys, 'argv', ['/usr/local/bin/color-tools']):
            result = get_program_name()
        self.assertEqual(result, "color-tools")

    def test_returns_fallback_on_empty_argv(self):
        """Returns 'color-tools' fallback when sys.argv is empty."""
        with patch.object(sys, 'argv', []):
            result = get_program_name()
        self.assertEqual(result, "color-tools")

    def test_returns_string(self):
        """Always returns a string."""
        with patch.object(sys, 'argv', ['color-tools']):
            result = get_program_name()
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
