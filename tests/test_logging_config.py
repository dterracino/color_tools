"""Unit tests for color_tools.logging_config module."""

from __future__ import annotations

import logging
import logging.handlers
import sys
import tempfile
import unittest
from pathlib import Path

# ── path setup (same pattern as other test files in this project) ─────────────
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.logging_config import (
    CONSOLE_LEVEL,
    LOG_LEVEL,
    _SanitizingFilter,
    get_logger,
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
    setup_logging,
)

_LIBRARY_LOGGER_NAME = "color_tools"


# ── shared helpers ─────────────────────────────────────────────────────────────


def _reset_library_logger() -> None:
    """Close and remove all handlers and filters from the library root logger.

    Called in tearDown to prevent test pollution across test methods.
    """
    logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
    for handler in logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
    logger.handlers.clear()
    logger.filters.clear()


class _CapturingHandler(logging.Handler):
    """Stores every emitted LogRecord for assertion in tests."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# ── TestConstants ──────────────────────────────────────────────────────────────


class TestConstants(unittest.TestCase):
    """Verify the public default-level constants are the correct logging levels."""

    def test_log_level_equals_debug(self):
        """LOG_LEVEL must be DEBUG so files capture everything."""
        self.assertEqual(LOG_LEVEL, logging.DEBUG)

    def test_console_level_equals_info(self):
        """CONSOLE_LEVEL must be INFO so only meaningful events appear."""
        self.assertEqual(CONSOLE_LEVEL, logging.INFO)

    def test_log_level_is_int(self):
        self.assertIsInstance(LOG_LEVEL, int)

    def test_console_level_is_int(self):
        self.assertIsInstance(CONSOLE_LEVEL, int)

    def test_log_level_less_than_console_level(self):
        """File threshold is lower than console threshold (DEBUG < INFO)."""
        self.assertLess(LOG_LEVEL, CONSOLE_LEVEL)


# ── TestSanitizingFilter ───────────────────────────────────────────────────────


class TestSanitizingFilter(unittest.TestCase):
    """Test _SanitizingFilter directly for all sanitization paths."""

    def setUp(self) -> None:
        self.f = _SanitizingFilter()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _record(self, msg: object, args: object = None) -> logging.LogRecord:
        return logging.LogRecord(
            name=_LIBRARY_LOGGER_NAME,
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=msg,
            args=args,  # type: ignore[arg-type]
            exc_info=None,
        )

    # ── msg field ─────────────────────────────────────────────────────────────

    def test_cr_in_msg_replaced_with_space(self):
        r = self._record("line1\rline2")
        self.f.filter(r)
        self.assertNotIn("\r", r.msg)
        self.assertIn(" ", r.msg)

    def test_lf_in_msg_replaced_with_space(self):
        r = self._record("line1\nline2")
        self.f.filter(r)
        self.assertNotIn("\n", r.msg)
        self.assertIn(" ", r.msg)

    def test_nul_in_msg_replaced_with_space(self):
        r = self._record("line1\x00line2")
        self.f.filter(r)
        self.assertNotIn("\x00", r.msg)
        self.assertIn(" ", r.msg)

    def test_all_injection_chars_replaced_in_single_msg(self):
        r = self._record("a\r\nb\x00c")
        self.f.filter(r)
        self.assertNotIn("\r", r.msg)
        self.assertNotIn("\n", r.msg)
        self.assertNotIn("\x00", r.msg)

    def test_clean_msg_passes_through_untouched(self):
        r = self._record("This is a clean message.")
        self.f.filter(r)
        self.assertEqual(r.msg, "This is a clean message.")

    def test_non_string_msg_passes_through_unchanged(self):
        r = self._record(42)
        self.f.filter(r)
        self.assertEqual(r.msg, 42)

    def test_none_msg_passes_through_unchanged(self):
        r = self._record(None)
        self.f.filter(r)
        self.assertIsNone(r.msg)

    # ── args – tuple ──────────────────────────────────────────────────────────

    def test_tuple_args_sanitized_element_by_element(self):
        r = self._record("msg %s %s", ("clean", "evil\nline"))
        self.f.filter(r)
        self.assertEqual(r.args, ("clean", "evil line"))

    def test_tuple_args_clean_pass_through_untouched(self):
        r = self._record("msg %s", ("value",))
        self.f.filter(r)
        self.assertEqual(r.args, ("value",))

    def test_tuple_args_non_string_element_unchanged(self):
        r = self._record("msg %s %d", ("text", 99))
        self.f.filter(r)
        self.assertEqual(r.args, ("text", 99))

    # ── args – dict ───────────────────────────────────────────────────────────

    def test_dict_args_values_are_sanitized(self):
        # Set args after construction: passing a raw dict to LogRecord() in
        # Python 3.12 triggers an internal args[0] access that raises KeyError.
        r = self._record("%(a)s %(b)s")
        r.args = {"a": "ok", "b": "bad\x00val"}
        self.f.filter(r)
        self.assertIsInstance(r.args, dict)
        self.assertEqual(r.args["b"], "bad val")  # type: ignore[index]
        self.assertEqual(r.args["a"], "ok")        # type: ignore[index]

    def test_dict_args_clean_values_pass_through(self):
        r = self._record("%(k)s")
        r.args = {"k": "clean"}
        self.f.filter(r)
        self.assertEqual(r.args, {"k": "clean"})  # type: ignore[comparison-overlap]

    # ── args – plain non-tuple non-dict ───────────────────────────────────────

    def test_plain_string_args_are_sanitized(self):
        """A bare string passed as record.args is also sanitized."""
        r = self._record("msg")
        r.args = "bad\narg"
        self.f.filter(r)
        self.assertEqual(r.args, "bad arg")

    def test_none_args_passes_through_unchanged(self):
        r = self._record("msg", None)
        self.f.filter(r)
        self.assertIsNone(r.args)

    # ── return value ──────────────────────────────────────────────────────────

    def test_filter_always_returns_true_for_clean_record(self):
        """filter() must always let the record through (return True)."""
        r = self._record("clean message")
        self.assertTrue(self.f.filter(r))

    def test_filter_always_returns_true_for_dirty_record(self):
        """Even malicious records are not suppressed, just sanitized."""
        r = self._record("dirty\nevil\x00message")
        self.assertTrue(self.f.filter(r))


# ── TestSetupLogging ───────────────────────────────────────────────────────────


class TestSetupLogging(unittest.TestCase):
    """Test setup_logging() handler wiring, idempotency, and parameter effects."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        _reset_library_logger()
        self._tmpdir.cleanup()

    # ── return value ──────────────────────────────────────────────────────────

    def test_returns_logger_instance(self):
        result = setup_logging()
        self.assertIsInstance(result, logging.Logger)

    def test_returned_logger_name_is_color_tools(self):
        result = setup_logging()
        self.assertEqual(result.name, _LIBRARY_LOGGER_NAME)

    # ── handler counts ────────────────────────────────────────────────────────

    def test_console_only_produces_exactly_one_handler(self):
        setup_logging()
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        self.assertEqual(len(logger.handlers), 1)

    def test_file_logging_produces_exactly_two_handlers(self):
        setup_logging(log_file=self.tmpdir / "test.log")
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        self.assertEqual(len(logger.handlers), 2)

    def test_file_handler_is_rotating_file_handler(self):
        setup_logging(log_file=self.tmpdir / "test.log")
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        rotating = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        self.assertEqual(len(rotating), 1)

    def test_file_handler_uses_utf8_encoding(self):
        log_path = self.tmpdir / "enc.log"
        setup_logging(log_file=log_path)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        fh = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        self.assertEqual(fh.encoding, "utf-8")

    # ── idempotency ───────────────────────────────────────────────────────────

    def test_repeated_console_setup_does_not_accumulate_handlers(self):
        setup_logging()
        setup_logging()
        setup_logging()
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        self.assertEqual(len(logger.handlers), 1)

    def test_repeated_file_setup_does_not_accumulate_handlers(self):
        log_path = self.tmpdir / "test.log"
        setup_logging(log_file=log_path)
        setup_logging(log_file=log_path)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        self.assertEqual(len(logger.handlers), 2)

    # ── level parameters ──────────────────────────────────────────────────────

    def test_log_level_controls_file_handler_level(self):
        log_path = self.tmpdir / "test.log"
        setup_logging(log_file=log_path, log_level=logging.WARNING)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        fh = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        self.assertEqual(fh.level, logging.WARNING)

    def test_log_level_default_is_debug_on_file_handler(self):
        log_path = self.tmpdir / "test.log"
        setup_logging(log_file=log_path)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        fh = next(
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        self.assertEqual(fh.level, logging.DEBUG)

    def test_console_level_controls_console_handler_level(self):
        # Use rich=False to get a plain StreamHandler with a predictable .level
        setup_logging(console_level=logging.DEBUG, rich=False)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        ch = next(
            h for h in logger.handlers
            if not isinstance(h, logging.handlers.RotatingFileHandler)
        )
        self.assertEqual(ch.level, logging.DEBUG)

    def test_console_level_default_is_info_on_stream_handler(self):
        setup_logging(rich=False)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        ch = next(
            h for h in logger.handlers
            if not isinstance(h, logging.handlers.RotatingFileHandler)
        )
        self.assertEqual(ch.level, logging.INFO)

    def test_logger_level_is_always_debug_regardless_of_console_level(self):
        """Root logger level is always DEBUG; handlers perform their own filtering."""
        setup_logging(console_level=logging.ERROR)
        self.assertEqual(logging.getLogger(_LIBRARY_LOGGER_NAME).level, logging.DEBUG)

    # ── rich parameter ────────────────────────────────────────────────────────

    def test_rich_false_forces_plain_stream_handler(self):
        """rich=False must yield a StreamHandler even when Rich is installed."""
        setup_logging(rich=False)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        ch = logger.handlers[0]
        self.assertIsInstance(ch, logging.StreamHandler)
        try:
            from rich.logging import RichHandler  # type: ignore[import]
            self.assertNotIsInstance(ch, RichHandler)
        except ImportError:
            pass  # Rich not installed; any StreamHandler is correct

    # ── propagation ───────────────────────────────────────────────────────────

    def test_propagate_is_false(self):
        """Prevent double-logging through the root logging hierarchy."""
        setup_logging()
        self.assertFalse(logging.getLogger(_LIBRARY_LOGGER_NAME).propagate)

    # ── sanitizing filter ─────────────────────────────────────────────────────

    def test_sanitizing_filter_is_attached_to_logger(self):
        setup_logging()
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        filter_classes = [type(f) for f in logger.filters]
        self.assertIn(_SanitizingFilter, filter_classes)

    # ── directory creation ────────────────────────────────────────────────────

    def test_log_file_parent_directories_are_created_automatically(self):
        nested = self.tmpdir / "a" / "b" / "c" / "color_tools.log"
        self.assertFalse(nested.parent.exists())
        setup_logging(log_file=nested)
        self.assertTrue(nested.parent.exists())

    def test_log_file_as_plain_string_is_accepted(self):
        log_path = str(self.tmpdir / "str_path.log")
        result = setup_logging(log_file=log_path)
        self.assertIsInstance(result, logging.Logger)
        logger = logging.getLogger(_LIBRARY_LOGGER_NAME)
        rotating = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        self.assertEqual(len(rotating), 1)


# ── TestGetLogger ──────────────────────────────────────────────────────────────


class TestGetLogger(unittest.TestCase):
    """Test get_logger() name-normalisation and hierarchy rules."""

    def tearDown(self) -> None:
        _reset_library_logger()

    def test_none_returns_root_logger(self):
        self.assertEqual(get_logger(None).name, _LIBRARY_LOGGER_NAME)

    def test_color_tools_string_returns_root_logger(self):
        self.assertEqual(get_logger(_LIBRARY_LOGGER_NAME).name, _LIBRARY_LOGGER_NAME)

    def test_bare_name_is_prefixed(self):
        self.assertEqual(get_logger("conversions").name, "color_tools.conversions")

    def test_fully_qualified_name_is_not_double_prefixed(self):
        self.assertEqual(
            get_logger("color_tools.conversions").name, "color_tools.conversions"
        )

    def test_dunder_main_is_prefixed(self):
        """'__main__' does not start with 'color_tools.' so it must be prefixed."""
        self.assertEqual(get_logger("__main__").name, "color_tools.__main__")

    def test_nested_sub_name_is_prefixed_once(self):
        self.assertEqual(
            get_logger("image.analysis").name, "color_tools.image.analysis"
        )

    def test_bare_and_prefixed_yield_same_logger_instance(self):
        """logging.getLogger is idempotent; same name → same object."""
        bare = get_logger("palette")
        prefixed = get_logger("color_tools.palette")
        self.assertIs(bare, prefixed)

    def test_returns_logger_instance(self):
        self.assertIsInstance(get_logger("naming"), logging.Logger)

    def test_sub_logger_is_child_of_root_library_logger(self):
        """Child loggers inherit handlers from their parent when propagation is on."""
        child = get_logger("distance")
        self.assertTrue(child.name.startswith(_LIBRARY_LOGGER_NAME + "."))


# ── TestShortcutFunctions ──────────────────────────────────────────────────────


class TestShortcutFunctions(unittest.TestCase):
    """Test log_debug / log_info / log_warning / log_error / log_critical."""

    def setUp(self) -> None:
        setup_logging()
        self._handler = _CapturingHandler()
        logging.getLogger(_LIBRARY_LOGGER_NAME).addHandler(self._handler)

    def tearDown(self) -> None:
        _reset_library_logger()

    def _latest(self) -> logging.LogRecord:
        return self._handler.records[-1]

    # ── log_debug ─────────────────────────────────────────────────────────────

    def test_log_debug_does_not_raise(self):
        log_debug("debug message")

    def test_log_debug_emits_debug_level(self):
        log_debug("debug %s", "value")
        self.assertEqual(self._latest().levelno, logging.DEBUG)

    # ── log_info ──────────────────────────────────────────────────────────────

    def test_log_info_does_not_raise(self):
        log_info("info message")

    def test_log_info_emits_info_level(self):
        log_info("info %s", "value")
        self.assertEqual(self._latest().levelno, logging.INFO)

    # ── log_warning ───────────────────────────────────────────────────────────

    def test_log_warning_does_not_raise(self):
        log_warning("warning message")

    def test_log_warning_emits_warning_level(self):
        log_warning("warning message")
        self.assertEqual(self._latest().levelno, logging.WARNING)

    # ── log_error ─────────────────────────────────────────────────────────────

    def test_log_error_does_not_raise(self):
        log_error("error message")

    def test_log_error_emits_error_level(self):
        log_error("error %s", "value")
        self.assertEqual(self._latest().levelno, logging.ERROR)

    # ── log_critical ──────────────────────────────────────────────────────────

    def test_log_critical_does_not_raise(self):
        log_critical("critical message")

    def test_log_critical_emits_critical_level(self):
        log_critical("critical message")
        self.assertEqual(self._latest().levelno, logging.CRITICAL)

    # ── routing and formatting ─────────────────────────────────────────────────

    def test_all_shortcuts_route_through_color_tools_logger(self):
        log_info("routing check")
        self.assertEqual(self._latest().name, _LIBRARY_LOGGER_NAME)

    def test_log_info_formats_integer_arg_correctly(self):
        log_info("loaded %d colors", 42)
        self.assertIn("42", self._latest().getMessage())

    def test_log_warning_formats_multiple_string_args(self):
        log_warning("key=%s val=%s", "name", "coral")
        msg = self._latest().getMessage()
        self.assertIn("name", msg)
        self.assertIn("coral", msg)

    def test_levels_are_ordered_correctly(self):
        """Emit one record per level and verify ordering is DEBUG < INFO < … < CRITICAL."""
        log_debug("d")
        log_info("i")
        log_warning("w")
        log_error("e")
        log_critical("c")
        levels = [r.levelno for r in self._handler.records]
        self.assertEqual(levels, sorted(levels))


# ── TestLogInjectionPrevention ─────────────────────────────────────────────────


class TestLogInjectionPrevention(unittest.TestCase):
    """End-to-end: verify CR/LF/NUL injection cannot forge second log lines."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        _reset_library_logger()
        self._tmpdir.cleanup()

    def _flush(self) -> None:
        for handler in logging.getLogger(_LIBRARY_LOGGER_NAME).handlers:
            handler.flush()

    def _lines(self, path: Path) -> list[str]:
        return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # ── LF ────────────────────────────────────────────────────────────────────

    def test_lf_in_arg_does_not_produce_second_log_line(self):
        """Primary log-injection vector: newline in a user-supplied value."""
        log_path = self.tmpdir / "lf_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("benign %s", "value\nCRITICAL  forged entry")
        self._flush()

        lines = self._lines(log_path)
        self.assertEqual(len(lines), 1, f"Expected 1 line, got: {lines}")
        self.assertIn("value CRITICAL  forged entry", lines[0])

    # ── CR ────────────────────────────────────────────────────────────────────

    def test_cr_in_arg_does_not_produce_second_log_line(self):
        log_path = self.tmpdir / "cr_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("benign %s", "value\rforged entry")
        self._flush()

        lines = self._lines(log_path)
        self.assertEqual(len(lines), 1, f"Expected 1 line, got: {lines}")
        self.assertIn("value forged entry", lines[0])

    # ── NUL ───────────────────────────────────────────────────────────────────

    def test_nul_in_arg_is_replaced_and_absent_from_file(self):
        log_path = self.tmpdir / "nul_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("data: %s", "abc\x00def")
        self._flush()

        content = log_path.read_text(encoding="utf-8")
        self.assertNotIn("\x00", content)
        self.assertIn("abc def", content)

    # ── injection in msg template ─────────────────────────────────────────────

    def test_lf_in_msg_template_does_not_produce_second_log_line(self):
        """Injection chars in the msg string itself (not just args) are sanitized."""
        log_path = self.tmpdir / "msg_inject_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("line1\nline2 message")
        self._flush()

        lines = self._lines(log_path)
        self.assertEqual(len(lines), 1, f"Expected 1 line, got: {lines}")
        self.assertIn("line1 line2 message", lines[0])

    # ── sanitized content is still visible ───────────────────────────────────

    def test_sanitized_content_is_still_present_in_log(self):
        """Sanitization replaces control chars; it does not silently discard data."""
        log_path = self.tmpdir / "visible_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("start %s end", "middle\ninjected")
        self._flush()

        content = log_path.read_text(encoding="utf-8")
        self.assertIn("middle injected", content)

    def test_multiple_records_each_on_own_line(self):
        """Separate log calls must remain separate lines; sanitization must not merge them."""
        log_path = self.tmpdir / "multi_test.log"
        setup_logging(log_file=log_path, console_level=logging.CRITICAL)

        log_info("first record")
        log_info("second record")
        self._flush()

        lines = self._lines(log_path)
        self.assertEqual(len(lines), 2, f"Expected 2 lines, got: {lines}")


if __name__ == "__main__":
    unittest.main()
