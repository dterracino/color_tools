"""Focused Phase 6 coverage for the conversion CLI handler."""

from __future__ import annotations

import io
import unittest
from argparse import Namespace
from unittest.mock import patch


class TestConvertCLIPhase6(unittest.TestCase):
    """Cover the complete supported conversion and gamut route matrix."""

    def _args(self, **overrides: object) -> Namespace:
        values: dict[str, object] = {
            "value": None,
            "hex": None,
            "check_gamut": False,
            "from_space": None,
            "to_space": None,
        }
        values.update(overrides)
        return Namespace(**values)

    def _run(self, args: Namespace) -> tuple[object, str, str]:
        from color_tools.cli_commands.handlers.convert import handle_convert_command

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            handle_convert_command(args)
        return raised.exception.code, stdout.getvalue(), stderr.getvalue()

    def test_gamut_rejects_both_missing_and_wrong_component_count(self) -> None:
        cases = (
            self._args(
                check_gamut=True,
                value=[50.0, 0.0, 0.0],
                hex="#808080",
            ),
            self._args(check_gamut=True),
            self._args(check_gamut=True, value=[50.0, 0.0]),
        )
        for args in cases:
            with self.subTest(args=vars(args)):
                code, _stdout, stderr = self._run(args)
                self.assertEqual(code, 2)
                self.assertIn("Error:", stderr)

    def test_invalid_hex_reaches_cli_error_boundary_for_both_routes(self) -> None:
        for operation in (
            {"check_gamut": True},
            {"to_space": "lab"},
        ):
            with self.subTest(operation=operation):
                code, _stdout, stderr = self._run(
                    self._args(hex="not-hex", **operation)
                )
                self.assertEqual(code, 2)
                self.assertIn("Invalid hex color code", stderr)

    def test_lch_gamut_input_is_converted_to_lab(self) -> None:
        with (
            patch(
                "color_tools.cli_commands.handlers.convert.lch_to_lab",
                return_value=(40.0, 5.0, -3.0),
            ) as convert,
            patch(
                "color_tools.cli_commands.handlers.convert.is_in_srgb_gamut",
                return_value=True,
            ) as check,
        ):
            code, stdout, _stderr = self._run(self._args(
                check_gamut=True,
                from_space="lch",
                value=[50.0, 20.0, 120.0],
            ))
        self.assertEqual(code, 0)
        convert.assert_called_once_with((50.0, 20.0, 120.0))
        check.assert_called_once_with((40.0, 5.0, -3.0))
        self.assertIn("LAB(40.00, 5.00, -3.00)", stdout)

    def test_out_of_gamut_output_contains_nearest_lab_and_rgb(self) -> None:
        with (
            patch(
                "color_tools.cli_commands.handlers.convert.is_in_srgb_gamut",
                return_value=False,
            ),
            patch(
                "color_tools.cli_commands.handlers.convert.find_nearest_in_gamut",
                return_value=(50.0, 1.0, 2.0),
            ),
            patch(
                "color_tools.cli_commands.handlers.convert.lab_to_rgb",
                return_value=(120, 121, 122),
            ),
        ):
            code, stdout, _stderr = self._run(self._args(
                check_gamut=True,
                from_space="lab",
                value=[50.0, 200.0, 200.0],
            ))
        self.assertEqual(code, 0)
        self.assertIn("OUT OF sRGB gamut", stdout)
        self.assertIn("LAB: (50.00, 1.00, 2.00)", stdout)
        self.assertIn("RGB: (120, 121, 122)", stdout)

    def test_every_supported_source_space_reaches_conversion(self) -> None:
        cases: tuple[tuple[str, list[float]], ...] = (
            ("rgb", [255.0, 0.0, 0.0]),
            ("hsl", [0.0, 100.0, 50.0]),
            ("lab", [50.0, 0.0, 0.0]),
            ("lch", [50.0, 0.0, 0.0]),
            ("cmy", [0.0, 100.0, 100.0]),
            ("cmyk", [0.0, 100.0, 100.0, 0.0]),
        )
        for source, value in cases:
            with self.subTest(source=source):
                code, stdout, stderr = self._run(self._args(
                    value=value,
                    from_space=source,
                    to_space="rgb",
                ))
                self.assertEqual(code, 0)
                self.assertEqual(stderr, "")
                self.assertIn(f"Converted {source.upper()}", stdout)
                self.assertIn("-> RGB", stdout)

    def test_every_supported_target_space_reaches_conversion(self) -> None:
        for target in ("rgb", "hsl", "lab", "lch", "cmy", "cmyk"):
            with self.subTest(target=target):
                code, stdout, stderr = self._run(self._args(
                    hex="#336699",
                    to_space=target,
                ))
                self.assertEqual(code, 0)
                self.assertEqual(stderr, "")
                self.assertIn("Converted RGB", stdout)
                self.assertIn(f"-> {target.upper()}", stdout)

    def test_invalid_cmy_and_cmyk_ranges_report_stderr(self) -> None:
        cases: tuple[tuple[str, list[float]], ...] = (
            ("cmy", [-1.0, 0.0, 0.0]),
            ("cmyk", [0.0, 0.0, 0.0, 101.0]),
        )
        for source, value in cases:
            with self.subTest(source=source):
                code, _stdout, stderr = self._run(self._args(
                    value=value,
                    from_space=source,
                    to_space="rgb",
                ))
                self.assertEqual(code, 2)
                self.assertIn(f"{source.upper()} component", stderr)

    def test_conversion_input_contract_failures_exit_two(self) -> None:
        cases = (
            self._args(value=[1.0, 2.0, 3.0], to_space="rgb"),
            self._args(to_space="rgb"),
            self._args(value=[1.0, 2.0], from_space="rgb", to_space="lab"),
            self._args(
                value=[1.0, 2.0, 3.0],
                from_space="cmyk",
                to_space="rgb",
            ),
        )
        for args in cases:
            with self.subTest(args=vars(args)):
                code, _stdout, stderr = self._run(args)
                self.assertEqual(code, 2)
                self.assertIn("Error:", stderr)


if __name__ == "__main__":
    unittest.main()
