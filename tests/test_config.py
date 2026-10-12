"""Configuration validation, snapshot, and execution-context regressions."""

from __future__ import annotations

import asyncio
from contextlib import redirect_stderr
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from contextvars import copy_context
from typing import cast
import unittest
from unittest.mock import patch

from color_tools import (
    ColorConfig, MultiColorMode, config_context, get_config, reset_config, set_config,
)
from color_tools.filament_palette import FilamentRecord
from color_tools.cli import build_parser
from color_tools.gamut import find_nearest_in_gamut, is_in_srgb_gamut
import color_tools.config as config_module


class TestConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.scope = config_context()
        self.scope.__enter__()
        reset_config()

    def tearDown(self) -> None:
        self.scope.__exit__(None, None, None)

    def test_defaults_and_snapshot_identity(self) -> None:
        original = get_config()
        self.assertEqual(original, ColorConfig())
        self.assertIs(original, get_config())
        set_config(multi_color_mode="last")
        self.assertEqual(original.multi_color_mode, "first")
        self.assertEqual(get_config().multi_color_mode, "last")
        self.assertIsNot(original, get_config())
        with self.assertRaises(FrozenInstanceError):
            setattr(original, "multi_color_mode", "last")

    def test_supported_and_future_modes(self) -> None:
        for mode in ("first", "last", "srgb_mean"):
            set_config(multi_color_mode=mode)
            self.assertEqual(get_config().multi_color_mode, mode)
        for mode in ("mix", "second", "FIRST", "lab_mean", "representative", ""):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                set_config(multi_color_mode=cast(MultiColorMode, mode))
        with self.assertRaises(TypeError):
            ColorConfig(multi_color_mode=cast(MultiColorMode, 1))

    def test_atomic_invalid_updates(self) -> None:
        snapshot = get_config()
        for value in (-1.0, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                set_config(multi_color_mode="last", gamut_tolerance=value)
            self.assertIs(get_config(), snapshot)
        for value in (True, "0.1"):
            with self.assertRaises(TypeError):
                set_config(gamut_tolerance=cast(float, value))
        for value in (0, -1):
            with self.assertRaises(ValueError):
                set_config(gamut_max_iterations=value)
        for value in (True, 1.5, "20"):
            with self.assertRaises(TypeError):
                set_config(gamut_max_iterations=cast(int, value))
        self.assertIs(get_config(), snapshot)

    def test_partial_updates_and_reset(self) -> None:
        set_config(gamut_tolerance=0, gamut_max_iterations=1000)
        set_config(multi_color_mode="srgb_mean")
        self.assertEqual(get_config(), ColorConfig("srgb_mean", 0, 1000))
        reset_config()
        self.assertEqual(get_config(), ColorConfig())

    def test_nested_context_and_exception_restoration(self) -> None:
        original = get_config()
        with config_context(multi_color_mode="last"):
            outer = get_config()
            with self.assertRaisesRegex(RuntimeError, "probe"):
                with config_context(gamut_tolerance=0.5):
                    self.assertEqual(get_config().multi_color_mode, "last")
                    reset_config()
                    set_config(gamut_max_iterations=1000)
                    raise RuntimeError("probe")
            self.assertIs(get_config(), outer)
        self.assertIs(get_config(), original)
        with self.assertRaises(ValueError):
            with config_context(gamut_tolerance=-1):
                self.fail("Invalid context must not enter")
        self.assertIs(get_config(), original)

    def test_thread_scope_and_explicit_propagation(self) -> None:
        set_config(multi_color_mode="last")
        context = copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual(pool.submit(get_config).result().multi_color_mode, "first")
            inherited = pool.submit(context.run, get_config).result()
            self.assertIs(inherited, get_config())
            self.assertEqual(pool.submit(get_config).result().multi_color_mode, "first")
        self.assertEqual(get_config().multi_color_mode, "last")

    def test_async_tasks_inherit_but_do_not_share_updates(self) -> None:
        set_config(multi_color_mode="last")

        async def probe() -> None:
            ready = asyncio.Event()

            async def writer() -> None:
                self.assertEqual(get_config().multi_color_mode, "last")
                set_config(multi_color_mode="srgb_mean")
                ready.set()
                await asyncio.sleep(0)
                self.assertEqual(get_config().multi_color_mode, "srgb_mean")

            async def reader() -> None:
                await ready.wait()
                self.assertEqual(get_config().multi_color_mode, "last")

            await asyncio.gather(writer(), reader())

        asyncio.run(probe())
        self.assertEqual(get_config().multi_color_mode, "last")

    def test_legacy_api_removed(self) -> None:
        for name in ("set_dual_color_mode", "get_dual_color_mode",
                     "set_gamut_tolerance", "get_gamut_tolerance",
                     "set_gamut_max_iterations", "get_gamut_max_iterations"):
            self.assertFalse(hasattr(config_module, name))

    def test_cli_mode_choices_and_context_preserving_default(self) -> None:
        parser = build_parser()
        self.assertIsNone(parser.parse_args(["filament"]).multi_color_mode)
        for mode in ("first", "last", "srgb_mean"):
            args = parser.parse_args(["filament", "--multi-color-mode", mode])
            self.assertEqual(args.multi_color_mode, mode)
        for option, mode in (
            ("--dual-color-mode", "first"),
            ("--multi-color-mode", "mix"),
            ("--multi-color-mode", "representative"),
        ):
            with self.subTest(option=option, mode=mode):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    parser.parse_args(["filament", option, mode])
                self.assertEqual(error.exception.code, 2)

    def test_existing_record_uses_new_settings_at_construction_only(self) -> None:
        def record() -> FilamentRecord:
            return FilamentRecord(
                id="probe", maker="probe", type="PLA", finish=None,
                color="probe", hex="#FF0000", hex2="#0000FF",
            )

        first = record()
        with config_context(multi_color_mode="last"):
            self.assertEqual(record().rgb, (0, 0, 255))
        with config_context(multi_color_mode="srgb_mean"):
            self.assertEqual(record().rgb, (128, 0, 128))
        self.assertEqual(first.rgb, (255, 0, 0))

    def test_gamut_overrides_validate_and_stop_at_convergence(self) -> None:
        with config_context(gamut_max_iterations=1000):
            with patch("color_tools.gamut.is_in_srgb_gamut", wraps=is_in_srgb_gamut) as check:
                find_nearest_in_gamut((50.0, 100.0, 80.0))
                self.assertLess(check.call_count, 1000)
                for call in check.call_args_list:
                    self.assertEqual(call.kwargs["tolerance"], 0.01)
        with self.assertRaises(ValueError):
            is_in_srgb_gamut((50.0, 0.0, 0.0), tolerance=-1)
        with self.assertRaises(ValueError):
            find_nearest_in_gamut((50.0, 0.0, 0.0), max_iterations=0)


if __name__ == "__main__":
    unittest.main()
