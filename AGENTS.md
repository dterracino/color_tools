# AGENTS.md

## Development Principles

All new or modified code should follow these principles:

* **SoC — Separation of Concerns:** Keep responsibilities clearly separated. Modules, classes, and functions should have focused purposes.
* **DRY — Don't Repeat Yourself:** Avoid duplicated logic. Extract shared behavior when duplication is real and meaningful.
* **YAGNI — You Aren't Gonna Need It:** Do not introduce abstractions, extension points, configuration, dependencies, or infrastructure for hypothetical future requirements. Implement the simplest design that cleanly satisfies the current task.
* **Avoid monolithic functions:** A function should have one clear responsibility. When a function contains multiple distinct responsibilities or independently understandable phases, extract those parts into focused helpers. Do not split simple cohesive logic into unnecessary wrappers merely to reduce function size.
* Classes should have a single clear responsibility and follow the principles outlined above.
* Each class should have its own file, named after the class it contains, except for tightly coupled classes or specific circumstances (e.g. a file that consists solely of a group of schema-related classes).
* Each code file should not run over 500 lines of code. If a file approaches this limit, consider refactoring it into smaller, more focused modules.
* When refactoring, attempt to do so in such a way that imports remain the same if possible.

## Python Quality Requirements

* Code must produce zero errors and warnings under Pyright in the mode configured in this repository's pyrightconfig.json / pyproject.toml (currently: strict).
* Library included py.typed file to indicate it supports PEP 561 type checking.
* All public interfaces (functions, methods, classes, and modules) must have complete and accurate type annotations.
* Do not suppress type-checking errors with `# type: ignore`, `# pyright: ignore`, or equivalent workarounds.
* Fix typing problems at their source.
* Use explicit, accurate type annotations where they improve correctness and maintainability.
* Avoid unnecessary `Any` usage when a concrete type can reasonably be expressed.
* **Private/internal functions and methods must use a single leading underscore**, following standard Python/PEP 8 conventions, for example `_calculate_value()`.
* All documentation should be kept in Markdown files, and should be clear, accurate, and kept up-to-date.
* There should be no problems listed in the Problems panel for source code, including Pyright and Markdown.

## General Expectations

Prefer simple, readable implementations over clever abstractions.

Keep functions and classes focused.

Do not introduce new dependencies unless they provide clear value for the current requirement.

When modifying existing code, preserve established project structure and conventions unless there is a concrete reason to change them.

These principles apply to new and modified code. Do not refactor pre-existing code that violates them unless the task explicitly asks for it or the violation is in the lines you are already changing.
