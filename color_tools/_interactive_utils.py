"""
Shared utilities for interactive modules.

Provides the prompt_toolkit availability flag, the guard function, and the
install hint message used by both ``interactive_manager`` and
``interactive_wizard``.  Having them here means the check and the message
stay in sync automatically.
"""

from __future__ import annotations

try:
    import prompt_toolkit as _pt  # noqa: F401
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

__all__ = [
    "PROMPT_TOOLKIT_AVAILABLE",
    "check_prompt_toolkit",
    "show_install_message",
]


def check_prompt_toolkit() -> bool:
    """Return ``True`` if prompt_toolkit is installed."""
    return PROMPT_TOOLKIT_AVAILABLE


def show_install_message() -> None:
    """Print a helpful install hint when prompt_toolkit is not available."""
    print("\n❌ Interactive mode requires prompt_toolkit.")
    print("\nInstall with:")
    print("  pip install color-match-tools[interactive]")
    print("\nOr install prompt_toolkit directly:")
    print("  pip install prompt_toolkit>=3.0.0")
    print()
