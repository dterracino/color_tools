"""Focused tests for the portable tools/code_metrics.py utility."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "code_metrics.py"
SPEC = importlib.util.spec_from_file_location("code_metrics_tool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
code_metrics = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = code_metrics
SPEC.loader.exec_module(code_metrics)


def _scan_config(**changes: object):
    values = {
        "target": ".",
        "use_default_exclusions": True,
        "excluded_directory_names": (".venv", ".pytest_cache", ".vercel", ".vscode", "build"),
        "excluded_directory_patterns": ("*.egg-info",),
        "exclude_paths": (),
    }
    values.update(changes)
    return code_metrics.ScanConfig(**values)


def test_analyze_file_counts_structure_and_source_lines(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        '"""module docs"""\n'
        "# comment\n"
        "class Outer:\n"
        "    def method(self):\n"
        "        def helper():\n"
        "            return 1\n"
        "        return helper()  # inline\n"
        "\n"
        "async def work():\n"
        "    return None\n",
        encoding="utf-8",
    )

    metrics = code_metrics.analyze_file(source, tmp_path)

    assert metrics.error is None
    assert metrics.comment_line_count == 2
    assert metrics.code_line_count == 7
    assert [item.qualified_name for item in metrics.classes] == ["Outer"]
    assert [(item.qualified_name, item.kind) for item in metrics.definitions] == [
        ("Outer.method", "method"),
        ("Outer.method.helper", "function"),
        ("work", "function"),
    ]


def test_analyze_file_honors_python_encoding_cookie(tmp_path: Path) -> None:
    source = tmp_path / "latin.py"
    source.write_bytes("# -*- coding: latin-1 -*-\nname = 'caf\xe9'\n".encode("latin-1"))

    metrics = code_metrics.analyze_file(source, tmp_path)

    assert metrics.error is None
    assert metrics.line_count == 2
    assert metrics.char_count == len("# -*- coding: latin-1 -*-\nname = 'café'\n")


def test_syntax_error_is_a_structured_problem(tmp_path: Path) -> None:
    source = tmp_path / "broken.py"
    source.write_text("def broken(:\n", encoding="utf-8")

    metrics = code_metrics.analyze_file(source, tmp_path)
    report = code_metrics.build_report([metrics], code_metrics.Thresholds(500, 500, 1, 100))

    assert metrics.error_category == "parse"
    assert metrics.line_count == 1
    assert report.summary.analysis_errors == 1
    assert report.summary.files_with_problems == 1


def test_discovery_prunes_default_and_wildcard_directories(tmp_path: Path) -> None:
    expected = tmp_path / "src" / "kept.py"
    expected.parent.mkdir()
    expected.write_text("value = 1\n", encoding="utf-8")
    for directory in (".venv", ".pytest_cache", ".vercel", ".vscode", "build", "demo.egg-info"):
        path = tmp_path / directory
        path.mkdir()
        (path / "ignored.py").write_text("value = 1\n", encoding="utf-8")

    found = code_metrics.discover_python_files(tmp_path, tmp_path, _scan_config())

    assert found == [expected]


def test_custom_exclusions_are_root_relative_and_additive(tmp_path: Path) -> None:
    for relative in ("src/keep.py", "generated/drop.py", "tools/private/drop.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    config = _scan_config(exclude_paths=("generated/**", "tools/private"))

    found = code_metrics.discover_python_files(tmp_path, tmp_path, config)

    assert [path.relative_to(tmp_path).as_posix() for path in found] == ["src/keep.py"]


def test_no_default_exclusions_exposes_excluded_target(tmp_path: Path) -> None:
    source = tmp_path / ".venv" / "inside.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")

    hidden = code_metrics.discover_python_files(source.parent, tmp_path, _scan_config())
    visible = code_metrics.discover_python_files(
        source.parent,
        tmp_path,
        _scan_config(use_default_exclusions=False),
    )

    assert hidden == []
    assert visible == [source]


def test_thresholds_and_acceptance_are_evaluated_once(tmp_path: Path) -> None:
    source = tmp_path / "accepted.py"
    source.write_text(
        "# code-metrics: accept classes\n"
        "class One:\n    pass\n"
        "class Two:\n    pass\n"
        "def long():\n    value = 1\n    return value\n",
        encoding="utf-8",
    )
    metrics = code_metrics.analyze_file(source, tmp_path)
    report = code_metrics.build_report([metrics], code_metrics.Thresholds(4, None, 1, 2))

    categories = [(item.category, item.accepted) for item in report.files[0].findings]
    assert ("lines", False) in categories
    assert ("classes", True) in categories
    assert ("monoliths", False) in categories
    assert report.summary.files_with_problems == 1


def test_null_threshold_disables_its_findings(tmp_path: Path) -> None:
    source = tmp_path / "many.py"
    source.write_text("class One: pass\nclass Two: pass\n", encoding="utf-8")
    metrics = code_metrics.analyze_file(source, tmp_path)

    report = code_metrics.build_report([metrics], code_metrics.Thresholds(None, None, None, None))

    assert report.files[0].findings == ()


def test_partial_config_and_cli_override_merge(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.json"
    config_path.write_text(
        json.dumps({"schema_version": 1, "thresholds": {"lines": 700}, "terminal": {"problems_only": True}}),
        encoding="utf-8",
    )
    parser = code_metrics._parser()
    args = parser.parse_args(["--config", str(config_path), "--line-limit", "600", "--all-files"])

    config = code_metrics.load_effective_config(args, parser, tmp_path, tmp_path / "missing.json")

    assert config.thresholds.lines == 600
    assert config.thresholds.code_lines == 500
    assert config.terminal.problems_only is False


def test_unknown_config_key_is_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.json"
    config_path.write_text('{"schema_version": 1, "thresholds": {"typo": 4}}', encoding="utf-8")
    parser = code_metrics._parser()
    args = parser.parse_args(["--config", str(config_path)])

    with pytest.raises(code_metrics.ConfigError, match="thresholds.typo"):
        code_metrics.load_effective_config(args, parser, tmp_path, tmp_path / "missing.json")


def test_markdown_contains_actionable_locations_and_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "candidate.py"
    source.write_text("class A: pass\nclass B: pass\ndef long():\n    x = 1\n    return x\n", encoding="utf-8")
    metrics = code_metrics.analyze_file(source, tmp_path)
    report = code_metrics.build_report([metrics], code_metrics.Thresholds(2, 2, 1, 2))
    config = code_metrics._build_config(code_metrics.copy.deepcopy(code_metrics.DEFAULT_CONFIG), "test config")
    config = code_metrics.EffectiveConfig(config.scan, code_metrics.Thresholds(2, 2, 1, 2), config.terminal, config.report, config.source)

    first = code_metrics.markdown_report(report, config)
    second = code_metrics.markdown_report(report, config)

    assert first == second
    assert "`candidate.py`" in first
    assert "A (line 1)" in first
    assert "function long, lines 3-5" in first
    assert "## Agent handoff constraints" in first


def test_main_resolves_target_from_repo_root_not_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    source = repo / "package" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = code_metrics.main(
        ["package", "--no-config", "--no-color"],
        repo_root=repo,
        default_config_path=repo / "tools" / "code_metrics.json",
    )

    assert result == 0
    assert "package/module.py" in capsys.readouterr().out


def test_report_write_replaces_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "reports" / "metrics.md"
    destination.parent.mkdir()
    destination.write_text("old", encoding="utf-8")

    code_metrics.write_markdown_report(destination, "new\n")

    assert destination.read_text(encoding="utf-8") == "new\n"
    assert not list(destination.parent.glob("*.tmp"))

