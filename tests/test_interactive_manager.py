"""Tests for the interactive filament manager."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from color_tools._interactive_utils import PROMPT_TOOLKIT_AVAILABLE
from color_tools.filament_palette import FilamentPalette
from color_tools.interactive_manager import InteractiveFilamentManager


@unittest.skipUnless(PROMPT_TOOLKIT_AVAILABLE, "prompt_toolkit is not installed")
class TestInteractiveManagerFilterInput(unittest.TestCase):
    """Filter mode treats printable action keys as text."""

    def setUp(self) -> None:
        with patch("color_tools.interactive_manager.Application"):
            self.manager = InteractiveFilamentManager(FilamentPalette([]))
        self.manager.filter_mode = True

    def test_action_letters_are_entered_into_filter(self) -> None:
        action_letters = "qynsrcf"
        for letter in action_letters:
            with self.subTest(letter=letter):
                action_binding = next(
                    binding
                    for binding in self.manager.kb.bindings
                    if binding.keys == (letter,)
                )
                text_binding = next(
                    binding
                    for binding in self.manager.kb.bindings
                    if binding.handler.__name__ == "handle_text_input"
                )

                self.assertFalse(action_binding.filter())
                self.assertTrue(text_binding.filter())
                text_binding.handler(MagicMock(data=letter))

        self.assertEqual(self.manager.filter_maker, action_letters)

    def test_filter_accepts_action_letter_in_basic(self) -> None:
        text_binding = next(
            binding
            for binding in self.manager.kb.bindings
            if binding.handler.__name__ == "handle_text_input"
        )

        for letter in "basic":
            text_binding.handler(MagicMock(data=letter))

        self.assertEqual(self.manager.filter_maker, "basic")

    def test_action_binding_remains_active_outside_filter_mode(self) -> None:
        self.manager.filter_mode = False

        action_binding = next(
            binding
            for binding in self.manager.kb.bindings
            if binding.keys == ("s",)
        )
        text_binding = next(
            binding
            for binding in self.manager.kb.bindings
            if binding.handler.__name__ == "handle_text_input"
        )

        self.assertTrue(action_binding.filter())
        self.assertFalse(text_binding.filter())


if __name__ == "__main__":
    unittest.main()
