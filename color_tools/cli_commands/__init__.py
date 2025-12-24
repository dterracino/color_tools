"""CLI package for color_tools."""

from .handlers import (
    handle_name_command,
    handle_validate_command,
    handle_cvd_command,
    handle_color_command,
    handle_filament_command,
    handle_convert_command,
)
from .utils import (
    validate_color_input_exclusivity,
    get_rgb_from_args,
    parse_hex_or_exit,
    is_valid_lab,
    is_valid_lch,
    get_program_name,
)
from .reporting import (
    show_override_report,
    generate_user_hashes,
    get_available_palettes,
)

__all__ = [
    # Handlers
    "handle_name_command",
    "handle_validate_command",
    "handle_cvd_command",
    "handle_color_command",
    "handle_filament_command",
    "handle_convert_command",
    # Utils
    "validate_color_input_exclusivity",
    "get_rgb_from_args",
    "parse_hex_or_exit",
    "is_valid_lab",
    "is_valid_lch",
    "get_program_name",
    # Reporting
    "show_override_report",
    "generate_user_hashes",
    "get_available_palettes",
]
