"""
Centralized logging configuration for color_tools.

Provides a single-call setup that fans out to both a colorized console handler
(via Rich if available) and an optional rotating file handler — following the
DRY principle: one ``logger.info()`` call reaches every configured destination.

Rich is an optional dependency (``pip install color-match-tools[logging]``).
If Rich is not installed the module falls back to a plain ``StreamHandler``
without raising any import errors.

Quick start::

    from color_tools.logging_config import setup_logging, get_logger

    # Console only (INFO+), no file
    setup_logging()

    # Console (DEBUG+) + rotating file
    from pathlib import Path
    setup_logging(log_file=Path("color_tools.log"), console_level=logging.DEBUG)

    # Module-level logger (inherits handlers from setup_logging)
    logger = get_logger(__name__)
    logger.info("Loaded %d colors", count)

Shortcut functions for the library root logger::

    from color_tools.logging_config import log_info, log_error
    log_info("Processing %d colors", count)
    log_error("Failed to load %s", path)

Security note:
    All log messages are sanitized to strip CR / LF / NUL characters before
    they reach any handler.  This prevents log-injection attacks where an
    attacker-controlled value (e.g. a color name read from a user-supplied
    JSON file) could forge additional log lines.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path
from typing import Any


# ============================================================================
# Public constants — default levels
# ============================================================================

#: Default minimum level written to the rotating *file* (captures everything).
LOG_LEVEL: int = logging.DEBUG

#: Default minimum level written to the *console* (only meaningful events).
CONSOLE_LEVEL: int = logging.INFO

# ============================================================================
# Internal constants
# ============================================================================

#: Maximum size of a single log file before rotation (10 MB).
_LOG_MAX_BYTES: int = 10 * 1_024 * 1_024

#: Number of rotated backup log files to keep.
_LOG_BACKUP_COUNT: int = 5

#: Root name for all color_tools loggers.
_LIBRARY_LOGGER_NAME: str = "color_tools"

# ============================================================================
# Rich availability (graceful optional import)
# ============================================================================

try:
    from rich.logging import RichHandler as _RichHandler  # type: ignore[import]
    _RICH_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _RICH_AVAILABLE = False

# ============================================================================
# OWASP: log-injection prevention
# ============================================================================

# Matches CR, LF, and NUL — the characters used to forge extra log lines.
_INJECTION_RE: re.Pattern[str] = re.compile(r"[\r\n\x00]+")


def _sanitize(value: object) -> object:
    """Return *value* with CR/LF/NUL replaced by a space if it is a string."""
    if isinstance(value, str):
        return _INJECTION_RE.sub(" ", value)
    return value


class _SanitizingFilter(logging.Filter):
    """
    Strip CR / LF / NUL from log messages and their arguments.

    Attaches to the library root logger so every handler receives clean data.
    A crafted string like ``"ok\\nCRITICAL  forged entry"`` becomes
    ``"ok CRITICAL  forged entry"`` — still visible as anomalous, but unable
    to fake a second log entry.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _sanitize(record.msg)

        if isinstance(record.args, tuple):
            record.args = tuple(_sanitize(a) for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: _sanitize(v) for k, v in record.args.items()}
        elif record.args is not None:
            record.args = _sanitize(record.args)  # type: ignore[assignment]

        return True


# ============================================================================
# Formatter factories
# ============================================================================

def _make_console_formatter() -> logging.Formatter:
    """Minimal one-line formatter used when Rich is not available."""
    return logging.Formatter("%(levelname)s: %(message)s")


def _make_file_formatter() -> logging.Formatter:
    """Detailed formatter with timestamp and source location for file output."""
    return logging.Formatter(
        fmt="%(asctime)s  %(name)-35s  %(levelname)-8s  %(funcName)s:%(lineno)d  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ============================================================================
# NullHandler — library best practice (no output until setup_logging() called)
# ============================================================================

logging.getLogger(_LIBRARY_LOGGER_NAME).addHandler(logging.NullHandler())

# ============================================================================
# Public API
# ============================================================================

def setup_logging(
    log_file: Path | str | None = None,
    log_level: int = LOG_LEVEL,
    console_level: int = CONSOLE_LEVEL,
    *,
    rich: bool | None = None,
) -> logging.Logger:
    """
    Configure the color_tools library logger with console and optional file output.

    **DRY guarantee:** a single ``logger.info("msg")`` call fans out to every
    registered handler automatically.  There is no separate "file logger" to
    call alongside the "console logger".

    Calling this function more than once is safe: existing handlers are removed
    and rebuilt each time, so handler counts never accumulate.

    Args:
        log_file:      Destination for the rotating log file.  Pass ``None``
                       (the default) to disable file logging entirely.
        log_level:     Minimum level for *file* output (default: ``DEBUG``).
        console_level: Minimum level for *console* output (default: ``INFO``).
        rich:          ``True``/``False`` to force-enable/disable Rich.
                       ``None`` (default) uses Rich when it is installed.

    Returns:
        The configured ``logging.Logger`` for the ``color_tools`` namespace.

    Example::

        from pathlib import Path
        import logging
        from color_tools.logging_config import setup_logging

        # INFO+ to console, DEBUG+ to file
        setup_logging(log_file=Path("color_tools.log"))

        # Verbose console mode
        setup_logging(console_level=logging.DEBUG)

        # Force plain output even if Rich is installed
        setup_logging(rich=False)
    """
    use_rich = _RICH_AVAILABLE if rich is None else (bool(rich) and _RICH_AVAILABLE)

    library_logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
    library_logger.setLevel(logging.DEBUG)   # Handlers perform their own filtering.
    library_logger.propagate = False          # Don't double-log via the root logger.

    # Replace any handlers from a previous setup_logging() call (idempotency).
    library_logger.handlers.clear()
    library_logger.filters.clear()

    # Attach the injection-prevention filter once at the logger level so that
    # it runs exactly once per record before fanning out to all handlers.
    library_logger.addFilter(_SanitizingFilter())

    # ------------------------------------------------------------------
    # Console handler — Rich (colorized) or plain StreamHandler
    # ------------------------------------------------------------------
    if use_rich:
        console_handler: logging.Handler = _RichHandler(
            level=console_level,
            rich_tracebacks=True,
            show_path=False,
            # Disable Rich markup parsing on the message text.  Without this a
            # color name like "[bold red]" in user data would be interpreted as
            # markup, producing garbled or unexpected output.
            markup=False,
            highlighter=None,  # Disable automatic token highlighting.
        )
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(_make_console_formatter())

    library_logger.addHandler(console_handler)

    # ------------------------------------------------------------------
    # File handler — rotating, optional
    # ------------------------------------------------------------------
    if log_file is not None:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(_make_file_formatter())
        library_logger.addHandler(file_handler)

    return library_logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger scoped under the ``color_tools`` namespace.

    All such loggers inherit the handlers registered by ``setup_logging()``,
    so no per-module setup is required.

    Args:
        name: Sub-name appended to ``color_tools.``.  Pass ``__name__`` from
              the calling module for automatic hierarchy.  ``None`` returns the
              library root logger.

    Returns:
        A ``logging.Logger`` instance.

    Example::

        # At the top of any module:
        from color_tools.logging_config import get_logger
        logger = get_logger(__name__)  # e.g. "color_tools.conversions"

        # Use with lazy % formatting (no cost when level is disabled):
        logger.debug("Cache hit for key: %s", key)
        logger.info("Loaded %d colors", len(colors))
        logger.error("Unexpected value %r", value, exc_info=True)
    """
    if name is None or name == _LIBRARY_LOGGER_NAME:
        return logging.getLogger(_LIBRARY_LOGGER_NAME)

    # Normalize: ensure the name is rooted under color_tools.
    # This handles both __name__ values ("color_tools.conversions") and bare
    # sub-names ("conversions") without double-prefixing.
    if not name.startswith(_LIBRARY_LOGGER_NAME + "."):
        name = f"{_LIBRARY_LOGGER_NAME}.{name}"

    return logging.getLogger(name)


# ============================================================================
# Shortcut functions — convenience wrappers around the library root logger
# ============================================================================
# Use lazy %-style formatting so the string is only composed when the level is
# actually enabled.  Avoid f-strings here for the same reason.

def log_debug(msg: str, *args: object, **kwargs: Any) -> None:
    """Log a DEBUG-level message on the color_tools root logger."""
    logging.getLogger(_LIBRARY_LOGGER_NAME).debug(msg, *args, **kwargs)


def log_info(msg: str, *args: object, **kwargs: Any) -> None:
    """Log an INFO-level message on the color_tools root logger."""
    logging.getLogger(_LIBRARY_LOGGER_NAME).info(msg, *args, **kwargs)


def log_warning(msg: str, *args: object, **kwargs: Any) -> None:
    """Log a WARNING-level message on the color_tools root logger."""
    logging.getLogger(_LIBRARY_LOGGER_NAME).warning(msg, *args, **kwargs)


def log_error(msg: str, *args: object, **kwargs: Any) -> None:
    """Log an ERROR-level message on the color_tools root logger."""
    logging.getLogger(_LIBRARY_LOGGER_NAME).error(msg, *args, **kwargs)


def log_critical(msg: str, *args: object, **kwargs: Any) -> None:
    """Log a CRITICAL-level message on the color_tools root logger."""
    logging.getLogger(_LIBRARY_LOGGER_NAME).critical(msg, *args, **kwargs)
