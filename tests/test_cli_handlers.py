"""
Tests for CLI command handlers.

Covers:
- handle_cvd_command (handlers/cvd.py)
- handle_name_command (handlers/name.py)
- handle_validate_command (handlers/validate.py)
- handle_convert_command (handlers/convert.py)
- handle_color_command (handlers/color.py)
- handle_filament_command (handlers/filament.py)
- handle_image_command (handlers/image.py)

Each handler always calls sys.exit(), so every path uses assertRaises(SystemExit).
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# CVD
# ---------------------------------------------------------------------------

class TestHandleCvdCommand(unittest.TestCase):
    """Tests for handle_cvd_command."""

    def _run(self, args):
        from color_tools.cli_commands.handlers.cvd import handle_cvd_command
        with self.assertRaises(SystemExit) as ctx:
            handle_cvd_command(args)
        return ctx.exception.code

    def _run_capture(self, args):
        from color_tools.cli_commands.handlers.cvd import handle_cvd_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_cvd_command(args)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(value=None, hex=None, mode='simulate', type='protanopia')
        defaults.update(kwargs)
        return Namespace(**defaults)

    # --- success paths ---

    def test_simulate_protanopia_by_value_exits_0(self):
        """Simulate protanopia with --value exits 0."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protanopia')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_simulate_deuteranopia_by_value_exits_0(self):
        """Simulate deuteranopia with --value exits 0."""
        args = self._make_args(value=[100, 200, 50], mode='simulate', type='deuteranopia')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_simulate_tritanopia_by_value_exits_0(self):
        """Simulate tritanopia with --value exits 0."""
        args = self._make_args(value=[50, 150, 250], mode='simulate', type='tritanopia')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_correct_mode_by_hex_exits_0(self):
        """Correct mode with --hex exits 0."""
        args = self._make_args(hex='#FF0000', mode='correct', type='deuteranopia')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_short_alias_protan_exits_0(self):
        """Short alias 'protan' works like 'protanopia'."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protan')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_short_alias_deutan_exits_0(self):
        """Short alias 'deutan' works like 'deuteranopia'."""
        args = self._make_args(value=[100, 200, 50], mode='simulate', type='deutan')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_short_alias_tritan_exits_0(self):
        """Short alias 'tritan' works like 'tritanopia'."""
        args = self._make_args(value=[50, 150, 250], mode='simulate', type='tritan')
        code = self._run(args)
        self.assertEqual(code, 0)

    def test_output_contains_input_rgb(self):
        """Output line 1 contains the input RGB tuple."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protanopia')
        _, output = self._run_capture(args)
        self.assertIn("Input RGB:", output)
        self.assertIn("255", output)

    def test_output_contains_output_rgb(self):
        """Output contains 'Output RGB:' line."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protanopia')
        _, output = self._run_capture(args)
        self.assertIn("Output RGB:", output)

    def test_output_contains_mode(self):
        """Output contains 'Mode:' line."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protanopia')
        _, output = self._run_capture(args)
        self.assertIn("Mode:", output)
        self.assertIn("simulate", output)

    def test_output_contains_type(self):
        """Output contains 'Type:' line with full deficiency name."""
        args = self._make_args(value=[255, 0, 0], mode='simulate', type='protanopia')
        _, output = self._run_capture(args)
        self.assertIn("Type:", output)
        self.assertIn("protanopia", output)

    # --- error paths ---

    def test_both_value_and_hex_exits_2(self):
        """Exits 2 when both --value and --hex are specified."""
        args = self._make_args(value=[255, 0, 0], hex='#FF0000')
        code = self._run(args)
        self.assertEqual(code, 2)

    def test_neither_value_nor_hex_exits_2(self):
        """Exits 2 when neither --value nor --hex is provided."""
        args = self._make_args()
        code = self._run(args)
        self.assertEqual(code, 2)

    def test_invalid_hex_exits_2(self):
        """Exits 2 with invalid hex string."""
        args = self._make_args(hex='GGGGGG')
        code = self._run(args)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Name
# ---------------------------------------------------------------------------

class TestHandleNameCommand(unittest.TestCase):
    """Tests for handle_name_command."""

    def _run_capture(self, args):
        from color_tools.cli_commands.handlers.name import handle_name_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_name_command(args)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(value=None, hex=None, threshold=25, show_type=False)
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_name_from_value_exits_0(self):
        """Generates name from --value, exits 0."""
        args = self._make_args(value=[255, 0, 0])
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_name_from_hex_exits_0(self):
        """Generates name from --hex, exits 0."""
        args = self._make_args(hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_output_contains_name(self):
        """Output contains a non-empty color name."""
        args = self._make_args(value=[255, 0, 0])
        code, output = self._run_capture(args)
        self.assertEqual(code, 0)
        self.assertTrue(len(output.strip()) > 0)

    def test_show_type_includes_match_type(self):
        """With show_type=True, output includes match type in parentheses."""
        args = self._make_args(value=[255, 0, 0], show_type=True)
        code, output = self._run_capture(args)
        self.assertEqual(code, 0)
        self.assertIn('(', output)
        self.assertIn(')', output)

    def test_no_show_type_has_no_parentheses(self):
        """Without show_type, output has no parentheses."""
        args = self._make_args(value=[255, 0, 0], show_type=False)
        code, output = self._run_capture(args)
        self.assertEqual(code, 0)
        self.assertNotIn('(', output)

    def test_both_value_and_hex_exits_2(self):
        """Exits 2 when both --value and --hex are specified."""
        args = self._make_args(value=[255, 0, 0], hex='#FF0000')
        from color_tools.cli_commands.handlers.name import handle_name_command
        with self.assertRaises(SystemExit) as ctx:
            handle_name_command(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_neither_value_nor_hex_exits_2(self):
        """Exits 2 when neither --value nor --hex is provided."""
        args = self._make_args()
        from color_tools.cli_commands.handlers.name import handle_name_command
        with self.assertRaises(SystemExit) as ctx:
            handle_name_command(args)
        self.assertEqual(ctx.exception.code, 2)

    def test_invalid_hex_exits_2(self):
        """Exits 2 with invalid hex string."""
        args = self._make_args(hex='GGGGGG')
        from color_tools.cli_commands.handlers.name import handle_name_command
        with self.assertRaises(SystemExit) as ctx:
            handle_name_command(args)
        self.assertEqual(ctx.exception.code, 2)


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

class TestHandleValidateCommand(unittest.TestCase):
    """Tests for handle_validate_command."""

    def _run_capture(self, args):
        from color_tools.cli_commands.handlers.validate import handle_validate_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_validate_command(args)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, name='red', hex_val='#FF0000', threshold=10.0, json_output=False):
        return Namespace(name=name, hex=hex_val, threshold=threshold, json_output=json_output)

    def test_matching_color_exits_0(self):
        """Exact color match exits 0."""
        args = self._make_args(name='red', hex_val='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_non_matching_color_exits_1(self):
        """Non-matching color exits 1."""
        args = self._make_args(name='red', hex_val='#0000FF', threshold=1.0)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_match_output_contains_checkmark(self):
        """Match output contains checkmark symbol."""
        args = self._make_args(name='red', hex_val='#FF0000')
        code, output = self._run_capture(args)
        self.assertEqual(code, 0)
        self.assertIn('✓', output)

    def test_no_match_output_contains_cross(self):
        """No-match output contains cross symbol."""
        args = self._make_args(name='red', hex_val='#0000FF', threshold=1.0)
        code, output = self._run_capture(args)
        self.assertEqual(code, 1)
        self.assertIn('✗', output)

    def test_json_output_is_valid_json(self):
        """JSON output mode produces valid JSON."""
        args = self._make_args(name='red', hex_val='#FF0000', json_output=True)
        code, output = self._run_capture(args)
        data = json.loads(output)
        self.assertIsInstance(data, dict)

    def test_json_output_has_required_keys(self):
        """JSON output has all required keys."""
        args = self._make_args(name='red', hex_val='#FF0000', json_output=True)
        _, output = self._run_capture(args)
        data = json.loads(output)
        required_keys = {'is_match', 'name_match', 'name_confidence', 'hex_value',
                         'suggested_hex', 'delta_e', 'message'}
        self.assertEqual(required_keys, set(data.keys()))

    def test_json_output_is_match_true_for_exact(self):
        """JSON is_match is True for exact match."""
        args = self._make_args(name='red', hex_val='#FF0000', json_output=True)
        _, output = self._run_capture(args)
        data = json.loads(output)
        self.assertTrue(data['is_match'])

    def test_json_output_is_match_false_for_mismatch(self):
        """JSON is_match is False for non-matching color."""
        args = self._make_args(name='red', hex_val='#0000FF', threshold=1.0, json_output=True)
        _, output = self._run_capture(args)
        data = json.loads(output)
        self.assertFalse(data['is_match'])


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------

class TestHandleConvertCommand(unittest.TestCase):
    """Tests for handle_convert_command."""

    def _run_capture(self, args):
        from color_tools.cli_commands.handlers.convert import handle_convert_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_convert_command(args)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(
            value=None, hex=None,
            check_gamut=False, from_space=None, to_space=None,
        )
        defaults.update(kwargs)
        return Namespace(**defaults)

    # --- --check-gamut branch ---

    def test_check_gamut_by_hex_exits_0(self):
        """Gamut check with --hex exits 0."""
        args = self._make_args(hex='#FF0000', check_gamut=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_check_gamut_by_value_exits_0(self):
        """Gamut check with --value (LAB space) exits 0."""
        args = self._make_args(value=[50.0, 0.0, 0.0], check_gamut=True, from_space='lab')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_check_gamut_output_contains_in_or_out(self):
        """Gamut check output contains 'IN' or 'OUT OF'."""
        args = self._make_args(hex='#FF0000', check_gamut=True)
        _, output = self._run_capture(args)
        self.assertTrue('IN' in output or 'OUT OF' in output)

    def test_check_gamut_both_inputs_exits_2(self):
        """Gamut check with both --value and --hex exits 2."""
        args = self._make_args(value=[50.0, 0.0, 0.0], hex='#FF0000', check_gamut=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_check_gamut_no_input_exits_2(self):
        """Gamut check with no --value or --hex exits 2."""
        args = self._make_args(check_gamut=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_check_gamut_lch_input_exits_0(self):
        """Gamut check with LCH space input exits 0."""
        args = self._make_args(value=[50.0, 30.0, 120.0], check_gamut=True, from_space='lch')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    # --- --to (conversion) branch ---

    def test_rgb_to_lab_conversion_exits_0(self):
        """RGB to LAB conversion exits 0."""
        args = self._make_args(hex='#FF0000', to_space='lab')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_rgb_to_hsl_conversion_exits_0(self):
        """RGB to HSL conversion exits 0."""
        args = self._make_args(hex='#FF0000', to_space='hsl')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_rgb_to_lch_conversion_exits_0(self):
        """RGB to LCH conversion exits 0."""
        args = self._make_args(hex='#00FF00', to_space='lch')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_lab_to_rgb_conversion_exits_0(self):
        """LAB to RGB conversion exits 0."""
        args = self._make_args(value=[53.23, 80.1, 67.2], from_space='lab', to_space='rgb')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_conversion_output_contains_arrow(self):
        """Conversion output contains '->' arrow."""
        args = self._make_args(hex='#FF0000', to_space='lab')
        _, output = self._run_capture(args)
        self.assertIn('->', output)

    def test_conversion_value_requires_from_space(self):
        """Conversion with --value and no --from exits 2."""
        args = self._make_args(value=[255.0, 0.0, 0.0], to_space='lab')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_conversion_both_inputs_exits_2(self):
        """Conversion with both --value and --hex exits 2."""
        args = self._make_args(value=[255.0, 0.0, 0.0], hex='#FF0000', to_space='lab')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_no_operation_exits_2(self):
        """Exits 2 when neither --check-gamut nor --to is specified."""
        args = self._make_args(hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_hsl_to_rgb_by_value_exits_0(self):
        """HSL to RGB conversion by --value exits 0."""
        args = self._make_args(value=[0.0, 100.0, 50.0], from_space='hsl', to_space='rgb')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

class TestHandleColorCommand(unittest.TestCase):
    """Tests for handle_color_command."""

    def _run_capture(self, args, json_path=None):
        from color_tools.cli_commands.handlers.color import handle_color_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_color_command(args, json_path)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(
            value=None, hex=None,
            name=None, nearest=False, export=None, output=None,
            palette=None, list_export_formats=False,
            space='rgb', metric='de2000', count=1,
            cmc_l=2.0, cmc_c=1.0,
        )
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_name_lookup_existing_exits_0(self):
        """Looking up an existing color by name exits 0."""
        args = self._make_args(name='red')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_name_lookup_output_contains_hex(self):
        """Name lookup output contains hex value."""
        args = self._make_args(name='red')
        _, output = self._run_capture(args)
        self.assertIn('Hex:', output)

    def test_name_lookup_output_contains_rgb(self):
        """Name lookup output contains RGB values."""
        args = self._make_args(name='red')
        _, output = self._run_capture(args)
        self.assertIn('RGB:', output)

    def test_name_lookup_missing_color_exits_1(self):
        """Looking up a non-existent color name exits 1."""
        args = self._make_args(name='notacolorthatexists_xyz')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_nearest_by_hex_exits_0(self):
        """--nearest with --hex exits 0."""
        args = self._make_args(nearest=True, hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_by_value_exits_0(self):
        """--nearest with --value exits 0."""
        args = self._make_args(nearest=True, value=[255, 0, 0])
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_output_contains_distance(self):
        """--nearest output contains 'distance='."""
        args = self._make_args(nearest=True, hex='#FF0000')
        _, output = self._run_capture(args)
        self.assertIn('distance=', output)

    def test_nearest_no_input_exits_2(self):
        """--nearest with no color input exits 2."""
        args = self._make_args(nearest=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_both_inputs_exits_2(self):
        """--nearest with both --value and --hex exits 2."""
        args = self._make_args(nearest=True, value=[255, 0, 0], hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_out_of_range_lab_exits_2(self):
        """--nearest with out-of-range LAB values exits 2."""
        args = self._make_args(nearest=True, value=[200.0, 0.0, 0.0], space='lab')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_out_of_range_lch_exits_2(self):
        """--nearest with out-of-range LCH values exits 2."""
        args = self._make_args(nearest=True, value=[50.0, 50.0, 400.0], space='lch')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_list_export_formats_exits_0(self):
        """--list-export-formats exits 0."""
        args = self._make_args(list_export_formats=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_palette_list_exits_0(self):
        """--palette list exits 0."""
        args = self._make_args(palette='list')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_palette_invalid_exits_1(self):
        """--palette with non-existent palette name exits 1."""
        args = self._make_args(palette='notapalette_xyz')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_no_operation_exits_2(self):
        """Exits 2 when no operation is specified."""
        args = self._make_args()
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_count_multiple_has_enumeration(self):
        """--nearest with count>1 shows enumerated results."""
        args = self._make_args(nearest=True, hex='#FF0000', count=3)
        _, output = self._run_capture(args)
        self.assertIn('1.', output)
        self.assertIn('2.', output)


# ---------------------------------------------------------------------------
# Filament
# ---------------------------------------------------------------------------

class TestHandleFilamentCommand(unittest.TestCase):
    """Tests for handle_filament_command."""

    def _run_capture(self, args, json_path=None):
        from color_tools.cli_commands.handlers.filament import handle_filament_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_filament_command(args, json_path)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(
            value=None, hex=None,
            nearest=False, maker=None, type=None, finish=None, color=None,
            list_makers=False, list_types=False, list_finishes=False,
            list_export_formats=False, export=None, output=None,
            metric='de2000', count=1, cmc_l=2.0, cmc_c=1.0,
            all_filaments=True,   # Always search all to avoid owned-file side effects
            dual_color_mode='first',
            manage=False,
            list_owned=False, add_owned=None, remove_owned=None,
        )
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_list_makers_exits_0(self):
        """--list-makers exits 0."""
        args = self._make_args(list_makers=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_list_makers_output_has_makers(self):
        """--list-makers output lists maker names."""
        args = self._make_args(list_makers=True)
        _, output = self._run_capture(args)
        self.assertIn('Available makers', output)

    def test_list_types_exits_0(self):
        """--list-types exits 0."""
        args = self._make_args(list_types=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_list_finishes_exits_0(self):
        """--list-finishes exits 0."""
        args = self._make_args(list_finishes=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_list_export_formats_exits_0(self):
        """--list-export-formats exits 0."""
        args = self._make_args(list_export_formats=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_by_hex_exits_0(self):
        """--nearest with --hex exits 0."""
        args = self._make_args(nearest=True, hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_by_value_exits_0(self):
        """--nearest with --value exits 0."""
        args = self._make_args(nearest=True, value=[255, 0, 0])
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_output_contains_distance(self):
        """--nearest output contains 'distance='."""
        args = self._make_args(nearest=True, hex='#FF0000')
        _, output = self._run_capture(args)
        self.assertIn('distance=', output)

    def test_nearest_no_input_exits_2(self):
        """--nearest with no color input exits 2."""
        args = self._make_args(nearest=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_both_inputs_exits_2(self):
        """--nearest with both --value and --hex exits 2."""
        args = self._make_args(nearest=True, value=[255, 0, 0], hex='#FF0000')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_filter_by_maker_pla_exits_0(self):
        """Filter by maker and type exits 0 when results exist."""
        args = self._make_args(maker='Bambu Lab', type='PLA')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_filter_no_results_exits_1(self):
        """Filter with impossible criteria exits 1."""
        args = self._make_args(maker='NonExistentMakerXYZ999')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_no_operation_exits_2(self):
        """Exits 2 when no operation is specified."""
        args = self._make_args()
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_nearest_multiple_results_exits_0(self):
        """--nearest with count>1 exits 0."""
        args = self._make_args(nearest=True, hex='#FF0000', count=3)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_nearest_invalid_hex_exits_2(self):
        """--nearest with invalid hex exits 2."""
        args = self._make_args(nearest=True, hex='GGGGGG')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 2)

    def test_add_owned_invalid_id_exits_1(self):
        """--add-owned with invalid filament ID exits 1."""
        args = self._make_args(add_owned='nonexistent-filament-id-xyz')
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

class TestHandleImageCommand(unittest.TestCase):
    """Tests for handle_image_command."""

    def _run_capture(self, args):
        from color_tools.cli_commands.handlers.image import handle_image_command
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch('sys.stdout', captured):
                handle_image_command(args)
        return ctx.exception.code, captured.getvalue()

    def _make_args(self, **kwargs):
        defaults = dict(
            file=None, output=None,
            list_palettes=False,
            redistribute_luminance=False,
            cvd_simulate=None, cvd_correct=None,
            quantize_palette=None, dither=False,
            watermark=False,
            watermark_text=None, watermark_image=None, watermark_svg=None,
            watermark_color='255,255,255',
            watermark_stroke_color=None,
            convert=None,
            colors=8, metric='de2000',
        )
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_image_not_available_exits_1(self):
        """Exits 1 with helpful message when Pillow is not installed."""
        import color_tools.cli_commands.handlers.image as img_mod
        with patch.object(img_mod, 'IMAGE_AVAILABLE', False):
            args = self._make_args()
            code, output = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_image_not_available_mentions_pillow(self):
        """Error message when Pillow missing mentions Pillow."""
        import color_tools.cli_commands.handlers.image as img_mod
        captured_err = io.StringIO()
        with patch.object(img_mod, 'IMAGE_AVAILABLE', False):
            with patch('sys.stderr', captured_err):
                args = self._make_args()
                with self.assertRaises(SystemExit):
                    img_mod.handle_image_command(args)
        self.assertIn('Pillow', captured_err.getvalue())

    def test_list_palettes_exits_0(self):
        """--list-palettes exits 0 without needing a file."""
        args = self._make_args(list_palettes=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 0)

    def test_list_palettes_output_has_palettes(self):
        """--list-palettes output lists palette names."""
        args = self._make_args(list_palettes=True)
        _, output = self._run_capture(args)
        self.assertTrue(len(output.strip()) > 0)

    def test_no_file_exits_1(self):
        """Exits 1 when --file is not provided (and not list-palettes)."""
        args = self._make_args(redistribute_luminance=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_file_not_found_exits_1(self):
        """Exits 1 when the image file does not exist."""
        args = self._make_args(file='/nonexistent/image_xyz.png', redistribute_luminance=True)
        code, _ = self._run_capture(args)
        self.assertEqual(code, 1)

    def test_no_operation_exits_1(self):
        """Exits 1 when a file is given but no operation is specified."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            tmp_path = f.name
        try:
            args = self._make_args(file=tmp_path)
            code, _ = self._run_capture(args)
            self.assertEqual(code, 1)
        finally:
            os.unlink(tmp_path)

    def test_multiple_operations_exits_1(self):
        """Exits 1 when more than one operation is specified."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            tmp_path = f.name
        try:
            args = self._make_args(
                file=tmp_path,
                redistribute_luminance=True,
                cvd_simulate='protanopia',
            )
            code, _ = self._run_capture(args)
            self.assertEqual(code, 1)
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
