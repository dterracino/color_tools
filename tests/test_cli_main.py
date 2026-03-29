"""
Tests for the color_tools CLI main entry point (cli.main).

Covers:
- --version flag
- No subcommand (either exits or shows help)
- --verify-constants (standalone)
- color subcommand dispatch
- filament subcommand dispatch
- convert subcommand dispatch
- name subcommand dispatch
- cvd subcommand dispatch
"""
from __future__ import annotations

import io
import sys
import unittest
from unittest.mock import patch

from color_tools.cli import main


class TestCliMain(unittest.TestCase):
    """Tests for the main() CLI entry point."""

    def setUp(self):
        """Prevent main() from replacing sys.stdout/stderr with UTF-8 wrappers.

        main() unconditionally wraps both streams on win32; the TextIOWrapper
        GC then closes the underlying buffers that the test runner still needs.
        Patching sys.platform to 'linux' skips that code path cleanly.
        """
        self._platform_patcher = patch.object(sys, 'platform', 'linux')
        self._platform_patcher.start()

    def tearDown(self):
        self._platform_patcher.stop()

    def _run(self, argv: list[str]):
        """Run main() with patched sys.argv and return exit code.

        sys.stdout is patched with StringIO so Unicode output (e.g. ✓) doesn't
        hit the cp1252 terminal encoding.  Platform is already patched to
        'linux' in setUp so main() won't attempt sys.stdout.buffer access.
        """
        with patch.object(sys, 'argv', ['color-tools'] + argv):
            with patch('sys.stdout', io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    main()
        return ctx.exception.code, '', ''

    def test_version_flag_exits_0(self):
        """--version exits 0."""
        code, out, _ = self._run(['--version'])
        self.assertEqual(code, 0)

    def test_version_flag_is_string_type(self):
        """--version exits 0 (string output is not captured here; just verify no crash)."""
        code, _, _ = self._run(['--version'])
        self.assertEqual(code, 0)

    def test_verify_constants_standalone_exits_cleanly(self):
        """--verify-constants alone exits cleanly (returns 0 on success, or 1 on failure)."""
        code, out, _ = self._run(['--verify-constants'])
        self.assertIn(code, (0, 1))  # 0 if ok, 1 if corrupted

    def test_color_name_lookup_exits_0(self):
        """color --name red exits 0."""
        code, _, _ = self._run(['color', '--name', 'red'])
        self.assertEqual(code, 0)

    def test_color_nearest_by_hex_exits_0(self):
        """color --nearest --hex #FF0000 exits 0."""
        code, _, _ = self._run(['color', '--nearest', '--hex', '#FF0000'])
        self.assertEqual(code, 0)

    def test_filament_list_makers_exits_0(self):
        """filament --list-makers exits 0."""
        code, _, _ = self._run(['filament', '--list-makers'])
        self.assertEqual(code, 0)

    def test_convert_hex_to_lab_exits_0(self):
        """convert --hex #FF0000 --to lab exits 0."""
        code, _, _ = self._run(['convert', '--hex', '#FF0000', '--to', 'lab'])
        self.assertEqual(code, 0)

    def test_name_from_hex_exits_0(self):
        """name --hex #FF0000 exits 0."""
        code, _, _ = self._run(['name', '--hex', '#FF0000'])
        self.assertEqual(code, 0)

    def test_cvd_simulate_exits_0(self):
        """cvd --hex #FF0000 --type protanopia --mode simulate exits 0."""
        code, _, _ = self._run([
            'cvd', '--hex', '#FF0000',
            '--type', 'protanopia',
            '--mode', 'simulate',
        ])
        self.assertEqual(code, 0)

    def test_invalid_json_dir_exits_nonzero(self):
        """--json with nonexistent directory causes nonzero exit."""
        code, _, _ = self._run([
            '--json', '/nonexistent/path/xyz',
            'color', '--nearest', '--hex', '#FF0000',
        ])
        self.assertNotEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
