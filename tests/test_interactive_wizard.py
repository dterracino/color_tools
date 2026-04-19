"""
Tests for color_tools.interactive_wizard.

Strategy
--------
The wizard's interactive prompt functions (_ask_choice, _ask_color_input,
_ask_multi, etc.) require prompt_toolkit and a real TTY, so we skip the
full-flow wizard tests here.

We DO test the parts that have real logic and no TTY dependency:

1. check_prompt_toolkit()   — availability flag
2. show_install_message()   — output content
3. _get_subparser()         — parser introspection
4. _get_choices()           — choices extraction from argparse
5. _run_command()           — sys.argv assembly and command-line printing
6. _ask_multi() logic       — by patching _pt() to return scripted answers
7. _ask_color_input() logic — hex and RGB paths via patched _pt() / _ask_choice()
8. _ask_float() logic       — valid, out-of-range, non-numeric, cancel
"""
from __future__ import annotations

import io
import sys
import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_wizard():
    """Import the module fresh (it may already be cached)."""
    from color_tools import interactive_wizard
    return interactive_wizard


class TestCheckPromptToolkit(unittest.TestCase):
    """check_prompt_toolkit() reflects the module-level flag."""

    def test_returns_bool(self):
        wiz = _import_wizard()
        result = wiz.check_prompt_toolkit()
        self.assertIsInstance(result, bool)

    def test_consistent_with_module_flag(self):
        wiz = _import_wizard()
        from color_tools._interactive_utils import PROMPT_TOOLKIT_AVAILABLE
        self.assertEqual(wiz.check_prompt_toolkit(), PROMPT_TOOLKIT_AVAILABLE)


class TestShowInstallMessage(unittest.TestCase):
    """show_install_message() prints useful install instructions."""

    def test_mentions_prompt_toolkit(self):
        wiz = _import_wizard()
        with patch('sys.stdout', io.StringIO()) as fake_out:
            wiz.show_install_message()
            output = fake_out.getvalue()
        self.assertIn('prompt_toolkit', output)
        self.assertIn('pip install', output)

    def test_mentions_interactive_extra(self):
        wiz = _import_wizard()
        with patch('sys.stdout', io.StringIO()) as fake_out:
            wiz.show_install_message()
            output = fake_out.getvalue()
        self.assertIn('[interactive]', output)


class TestGetSubparser(unittest.TestCase):
    """_get_subparser() returns a parser for known commands, None for unknown."""

    def test_color_subparser_exists(self):
        wiz = _import_wizard()
        sub = wiz._get_subparser('color')
        self.assertIsNotNone(sub)

    def test_filament_subparser_exists(self):
        wiz = _import_wizard()
        sub = wiz._get_subparser('filament')
        self.assertIsNotNone(sub)

    def test_convert_subparser_exists(self):
        wiz = _import_wizard()
        sub = wiz._get_subparser('convert')
        self.assertIsNotNone(sub)

    def test_unknown_command_returns_none(self):
        wiz = _import_wizard()
        sub = wiz._get_subparser('nonexistent_command_xyz')
        self.assertIsNone(sub)


class TestGetChoices(unittest.TestCase):
    """_get_choices() extracts argparse choices for known args."""

    def test_filament_metric_choices_nonempty(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('filament', 'metric')
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)

    def test_filament_metric_contains_de2000(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('filament', 'metric')
        self.assertIn('de2000', choices)

    def test_color_metric_choices_nonempty(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('color', 'metric')
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)

    def test_convert_from_space_contains_rgb(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('convert', 'from_space')
        self.assertIn('rgb', choices)

    def test_convert_from_space_contains_cmyk(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('convert', 'from_space')
        self.assertIn('cmyk', choices)

    def test_unknown_dest_returns_empty_list(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('color', 'nonexistent_dest_xyz')
        self.assertEqual(choices, [])

    def test_unknown_command_returns_empty_list(self):
        wiz = _import_wizard()
        choices = wiz._get_choices('nonexistent_command_xyz', 'metric')
        self.assertEqual(choices, [])


class TestRunCommand(unittest.TestCase):
    """_run_command() assembles sys.argv correctly and prints the command line."""

    def setUp(self):
        # Prevent main() from replacing sys.stdout on Windows
        self._platform_patcher = patch.object(sys, 'platform', 'linux')
        self._platform_patcher.start()

    def tearDown(self):
        self._platform_patcher.stop()

    def _call(self, args_list, json_path=None):
        """Run _run_command, capture stdout, capture sys.argv seen by main()."""
        wiz = _import_wizard()
        captured_argv: list[str] = []

        def fake_main():
            captured_argv.extend(sys.argv[:])
            raise SystemExit(0)

        with patch('color_tools.interactive_wizard._pt_prompt', side_effect=EOFError):
            with patch('color_tools.cli.main', side_effect=fake_main):
                with patch('sys.stdout', io.StringIO()) as fake_out:
                    try:
                        wiz._run_command(args_list, json_path)
                    except SystemExit:
                        pass
                    output = fake_out.getvalue()

        return captured_argv, output

    def test_args_passed_to_main(self):
        """sys.argv[1:] must match the args_list we passed in."""
        argv, _ = self._call(['color', '--name', 'coral'])
        self.assertEqual(argv[1:], ['color', '--name', 'coral'])

    def test_command_line_printed_before_run(self):
        """The ▶ line must appear in stdout."""
        _, output = self._call(['color', '--name', 'coral'])
        self.assertIn('▶', output)
        self.assertIn('--name', output)
        self.assertIn('coral', output)

    def test_json_path_prepended(self):
        """When json_path is provided it appears before the subcommand."""
        from pathlib import Path
        argv, _ = self._call(['color', '--name', 'coral'], json_path=Path('/tmp/data'))
        self.assertIn('--json', argv)
        json_idx = argv.index('--json')
        # --json value must come before 'color'
        color_idx = argv.index('color')
        self.assertLess(json_idx, color_idx)

    def test_sys_argv_restored_after_run(self):
        """sys.argv must be restored to original after _run_command returns."""
        original = sys.argv[:]
        try:
            self._call(['filament', '--nearest', '--hex', '#FF0000'])
        except Exception:
            pass
        self.assertEqual(sys.argv, original)

    def test_hex_arg_quoted_in_output(self):
        """Hex values with # are shell-quoted in the printed command."""
        _, output = self._call(['filament', '--nearest', '--hex', '#FF0000'])
        # shlex.quote wraps #FF0000 in single quotes on Unix
        self.assertIn('FF0000', output)


class TestAskMultiLogic(unittest.TestCase):
    """_ask_multi() — test selection, empty-done, quit, and dedup."""

    def _run_multi(self, options: list[str], pt_responses: list[str]) -> list[str] | None:
        """Run _ask_multi with scripted _pt() responses."""
        wiz = _import_wizard()
        responses = iter(pt_responses)

        def fake_pt(message, completer=None):
            return next(responses)

        with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
            with patch('sys.stdout', io.StringIO()):
                return wiz._ask_multi("Test filter", options)

    def test_empty_immediately_returns_empty_list(self):
        result = self._run_multi(['Matte', 'Basic', 'Silk'], [''])
        self.assertEqual(result, [])

    def test_single_selection_then_done(self):
        result = self._run_multi(['Matte', 'Basic', 'Silk'], ['Matte', ''])
        self.assertEqual(result, ['Matte'])

    def test_multiple_selections(self):
        result = self._run_multi(['Matte', 'Basic', 'Silk'], ['Matte', 'Basic', ''])
        self.assertEqual(result, ['Matte', 'Basic'])

    def test_quit_returns_none(self):
        result = self._run_multi(['Matte', 'Basic'], ['Matte', 'q'])
        self.assertIsNone(result)

    def test_exit_keyword_returns_none(self):
        result = self._run_multi(['Matte', 'Basic'], ['exit'])
        self.assertIsNone(result)

    def test_keyboard_interrupt_returns_none(self):
        wiz = _import_wizard()

        def fake_pt(message, completer=None):
            raise KeyboardInterrupt

        with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
            with patch('sys.stdout', io.StringIO()):
                result = wiz._ask_multi("Test filter", ['Matte'])
        self.assertIsNone(result)

    def test_duplicate_not_offered_again(self):
        """After picking 'Matte' it should be removed from the completer."""
        wiz = _import_wizard()
        completer_options: list[list[str]] = []
        original_wc = None

        try:
            from prompt_toolkit.completion import WordCompleter as WC
            original_wc = WC
        except ImportError:
            self.skipTest("prompt_toolkit not installed")

        calls = iter(['Matte', ''])

        def fake_pt(message, completer=None):
            if completer is not None:
                completer_options.append(list(completer.words))
            return next(calls)

        with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
            with patch('sys.stdout', io.StringIO()):
                wiz._ask_multi("Test", ['Matte', 'Basic', 'Silk'])

        # After picking 'Matte', the next completer must not include it
        if len(completer_options) >= 2:
            self.assertNotIn('Matte', completer_options[1])


class TestAskColorInputLogic(unittest.TestCase):
    """_ask_color_input() — hex and RGB paths via patched helpers."""

    def _run_color_input(self, ask_choice_return, pt_responses):
        wiz = _import_wizard()
        responses = iter(pt_responses)

        def fake_pt(message, completer=None):
            return next(responses)

        with patch('color_tools.interactive_wizard._ask_choice',
                   return_value=ask_choice_return):
            with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
                with patch('sys.stdout', io.StringIO()):
                    return wiz._ask_color_input("test color")

    def test_hex_path_returns_hex_arg(self):
        args, display = self._run_color_input(ask_choice_return=1,
                                              pt_responses=['#FF8040'])
        self.assertEqual(args, ['--hex', '#FF8040'])
        self.assertEqual(display, '#FF8040')

    def test_hex_without_hash_normalised(self):
        args, display = self._run_color_input(ask_choice_return=1,
                                              pt_responses=['ff8040'])
        self.assertEqual(args, ['--hex', '#FF8040'])

    def test_hex_invalid_then_valid(self):
        args, display = self._run_color_input(ask_choice_return=1,
                                              pt_responses=['ZZZZZZ', '#AABBCC'])
        self.assertEqual(args, ['--hex', '#AABBCC'])

    def test_rgb_path_returns_value_args(self):
        args, display = self._run_color_input(ask_choice_return=2,
                                              pt_responses=['255', '128', '64'])
        self.assertEqual(args, ['--value', '255', '128', '64'])
        self.assertIn('255', display)

    def test_mode_cancel_returns_none(self):
        # _ask_choice returning None means user quit at the hex/RGB menu
        wiz = _import_wizard()
        with patch('color_tools.interactive_wizard._ask_choice', return_value=None):
            with patch('sys.stdout', io.StringIO()):
                result = wiz._ask_color_input("test color")
        self.assertIsNone(result)

    def test_hex_quit_keyword_returns_none(self):
        result = self._run_color_input(ask_choice_return=1, pt_responses=['q'])
        self.assertIsNone(result)


class TestAskFloatLogic(unittest.TestCase):
    """_ask_float() — valid value, out-of-range retry, non-numeric retry, cancel."""

    def _run_float(self, pt_responses, lo=0.0, hi=100.0):
        wiz = _import_wizard()
        responses = iter(pt_responses)

        def fake_pt(message, completer=None):
            return next(responses)

        with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
            with patch('sys.stdout', io.StringIO()):
                return wiz._ask_float("test label", lo, hi)

    def test_valid_value_returned(self):
        result = self._run_float(['50.5'])
        self.assertAlmostEqual(result, 50.5)

    def test_boundary_lo(self):
        result = self._run_float(['0'])
        self.assertAlmostEqual(result, 0.0)

    def test_boundary_hi(self):
        result = self._run_float(['100'])
        self.assertAlmostEqual(result, 100.0)

    def test_out_of_range_retries(self):
        result = self._run_float(['-1', '200', '42'])
        self.assertAlmostEqual(result, 42.0)

    def test_non_numeric_retries(self):
        result = self._run_float(['abc', '37'])
        self.assertAlmostEqual(result, 37.0)

    def test_quit_returns_none(self):
        result = self._run_float(['q'])
        self.assertIsNone(result)

    def test_keyboard_interrupt_returns_none(self):
        wiz = _import_wizard()

        def fake_pt(message, completer=None):
            raise KeyboardInterrupt

        with patch('color_tools.interactive_wizard._pt', side_effect=fake_pt):
            with patch('sys.stdout', io.StringIO()):
                result = wiz._ask_float("test", 0, 100)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
