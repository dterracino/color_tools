"""
Tests for color_tools.cli_commands.reporting module.

Covers:
- get_available_palettes
- handle_verification_flags (select cases)
- generate_user_hashes
- show_override_report (smoke test)
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from color_tools.cli_commands.reporting import (
    get_available_palettes,
    generate_user_hashes,
    show_override_report,
    handle_verification_flags,
)


class TestGetAvailablePalettes(unittest.TestCase):
    """Tests for get_available_palettes."""

    def test_returns_list_of_tuples(self):
        """Returns a list of (name, count) tuples."""
        result = get_available_palettes()
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_known_palette_included(self):
        """Known core palette 'cga4' is present."""
        result = get_available_palettes()
        names = [name for name, _ in result]
        self.assertIn('cga4', names)

    def test_color_count_positive(self):
        """All successfully-loaded palettes have a positive color count."""
        result = get_available_palettes()
        for name, count in result:
            if count != -1:  # -1 means load error
                self.assertGreater(count, 0, f"Palette '{name}' has {count} colors")

    def test_result_is_sorted(self):
        """Results are sorted alphabetically by palette name."""
        result = get_available_palettes()
        names = [name for name, _ in result]
        self.assertEqual(names, sorted(names))

    def test_cga16_included(self):
        """Known palette 'cga16' is present."""
        result = get_available_palettes()
        names = [name for name, _ in result]
        self.assertIn('cga16', names)

    def test_vga_included(self):
        """Known palette 'vga' is present."""
        result = get_available_palettes()
        names = [name for name, _ in result]
        self.assertIn('vga', names)

    def test_empty_dir_returns_empty_list(self):
        """Non-existent json_path with no palettes returns empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            result = get_available_palettes(tmp)
        self.assertEqual(result, [])

    def test_custom_dir_with_palette_file(self):
        """Custom dir with a palette JSON file returns that palette."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create minimal palettes/ subdir and a palette JSON
            palettes_dir = Path(tmp) / "palettes"
            palettes_dir.mkdir()
            palette_json = palettes_dir / "test_palette.json"
            palette_json.write_text(
                '[{"name": "testred", "hex": "#FF0000", "rgb": [255, 0, 0], '
                '"hsl": [0.0, 100.0, 50.0], "lab": [53.0, 80.0, 67.0], '
                '"lch": [53.0, 104.0, 40.0]}]',
                encoding='utf-8',
            )
            result = get_available_palettes(tmp)
        names = [name for name, _ in result]
        self.assertIn('test_palette', names)


class TestHandleVerificationFlags(unittest.TestCase):
    """Tests for handle_verification_flags."""

    def _make_args(self, **kwargs):
        defaults = dict(
            verify_all=False,
            verify_constants=False,
            verify_data=False,
            verify_matrices=False,
            verify_user_data=False,
            generate_user_hashes=False,
            check_overrides=False,
            json=None,
            command=None,
        )
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_no_flags_returns_false(self):
        """Returns False when no verification flags are set."""
        args = self._make_args()
        result = handle_verification_flags(args)
        self.assertFalse(result)

    def test_verify_constants_succeeds(self):
        """verify_constants=True passes integrity check (returns False — not exit-only)."""
        captured = io.StringIO()
        args = self._make_args(verify_constants=True, command='color')
        with patch('sys.stdout', captured):
            result = handle_verification_flags(args)
        # Should not exit, just verify and continue (has a command)
        self.assertFalse(result)
        self.assertIn('✓', captured.getvalue())

    def test_verify_constants_without_command_returns_true(self):
        """verify_constants=True with no command signals exit (returns True)."""
        captured = io.StringIO()
        args = self._make_args(verify_constants=True)
        with patch('sys.stdout', captured):
            result = handle_verification_flags(args)
        self.assertTrue(result)

    def test_verify_all_expands_to_all_flags(self):
        """verify_all=True sets all individual verify flags."""
        args = self._make_args(verify_all=True, command='color')
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            result = handle_verification_flags(args)
        # After verify_all, individual flags should be set
        self.assertTrue(args.verify_constants)
        self.assertTrue(args.verify_data)
        self.assertTrue(args.verify_matrices)
        self.assertTrue(args.verify_user_data)

    def test_generate_user_hashes_calls_sys_exit(self):
        """generate_user_hashes=True calls sys.exit(0) after generating."""
        captured = io.StringIO()
        args = self._make_args(generate_user_hashes=True)
        with patch('sys.stdout', captured):
            with self.assertRaises(SystemExit) as ctx:
                handle_verification_flags(args)
        self.assertEqual(ctx.exception.code, 0)

    def test_check_overrides_calls_sys_exit(self):
        """check_overrides=True calls sys.exit(0) after showing report."""
        captured = io.StringIO()
        args = self._make_args(check_overrides=True)
        with patch('sys.stdout', captured):
            with self.assertRaises(SystemExit) as ctx:
                handle_verification_flags(args)
        self.assertEqual(ctx.exception.code, 0)


class TestGenerateUserHashes(unittest.TestCase):
    """Tests for generate_user_hashes."""

    def test_no_user_dir_exits_0(self):
        """Exits 0 when data dir exists but has no user/ subdir."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                with self.assertRaises(SystemExit) as ctx:
                    generate_user_hashes(tmp)
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn('No user data directory', captured.getvalue())

    def test_nonexistent_dir_exits_1(self):
        """Exits 1 when the specified directory does not exist."""
        captured_err = io.StringIO()
        with patch('sys.stderr', captured_err):
            with self.assertRaises(SystemExit) as ctx:
                generate_user_hashes('/nonexistent/path/xyz')
        self.assertEqual(ctx.exception.code, 1)

    def test_generates_hash_file_for_user_colors(self):
        """Creates a .sha256 file when user-colors.json is present in user/ dir.

        generate_user_hashes returns normally (no sys.exit) after successfully
        creating hashes; it only calls sys.exit for error/no-user-dir cases.
        """
        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp) / "user"
            user_dir.mkdir()
            user_colors = user_dir / "user-colors.json"
            user_colors.write_text(
                '[{"name": "testred", "hex": "#FF0000", "rgb": [255, 0, 0], '
                '"hsl": [0.0, 100.0, 50.0], "lab": [53.0, 80.0, 67.0], '
                '"lch": [53.0, 104.0, 40.0]}]',
                encoding='utf-8',
            )
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                generate_user_hashes(tmp)  # returns normally on success
            output = captured.getvalue()
            self.assertIn('Generated 1', output)
            # Verify the .sha256 file was actually created
            sha_file = user_dir / 'user-colors.json.sha256'
            self.assertTrue(sha_file.exists())


class TestShowOverrideReport(unittest.TestCase):
    """Smoke tests for show_override_report."""

    def test_runs_without_crashing(self):
        """show_override_report completes without raising (non-error path)."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            show_override_report()  # Uses default data dir; should not crash
        output = captured.getvalue()
        self.assertIn('User Override Report', output)

    def test_output_has_summary_section(self):
        """Output includes a Summary section."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            show_override_report()
        self.assertIn('Summary', captured.getvalue())

    def test_nonexistent_dir_exits_1(self):
        """Exits 1 when the data directory doesn't exist."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            with self.assertRaises(SystemExit) as ctx:
                show_override_report('/nonexistent/dir/xyz')
        self.assertEqual(ctx.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
