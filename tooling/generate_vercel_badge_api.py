"""Generate Vercel-only API entrypoints for badge deployments."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
BADGES_DIR = ROOT / "badges"
BADGE_MODULES = ("color_of_day", "filament_of_day")
REQUIREMENTS_SOURCE = BADGES_DIR / "requirements.txt"


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _build_wrapper(module_name: str) -> str:
    return (
        '"""Generated for Vercel badge deployment. Do not commit."""\n\n'
        f"from badges.{module_name} import handler\n"
    )


def main() -> None:
    generated_paths: list[Path] = []

    for module_name in BADGE_MODULES:
        wrapper_path = API_DIR / f"{module_name}.py"
        _write_if_changed(wrapper_path, _build_wrapper(module_name))
        generated_paths.append(wrapper_path)

    requirements_content = REQUIREMENTS_SOURCE.read_text(encoding="utf-8")
    requirements_path = API_DIR / "requirements.txt"
    _write_if_changed(requirements_path, requirements_content)
    generated_paths.append(requirements_path)

    print("Generated Vercel badge entrypoints:")
    for path in generated_paths:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
