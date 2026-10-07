"""Reusable inclusion and exclusion criteria for filament searches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


_FilterField = str | Iterable[str]


def _freeze_filter_field(value: _FilterField | None) -> _FilterField | None:
    """Materialize iterable inputs so criteria remain stable and hashable."""
    if value is None or isinstance(value, str):
        return value
    return tuple(str(item) for item in value)


def _normalize_filter_field(value: _FilterField | None) -> frozenset[str] | None:
    """Normalize one optional filter field for case-insensitive matching."""
    if value is None:
        return None
    values = (value,) if isinstance(value, str) else value
    normalized = frozenset(str(item).strip().casefold() for item in values)
    return normalized or None


@dataclass(frozen=True, slots=True)
class FilamentFilterCriteria:
    """Case-insensitive maker, type, finish, and color matching criteria.

    Multiple values within one field use OR semantics. Active fields are
    combined with AND semantics.
    """

    maker: _FilterField | None = field(default=None, compare=False)
    type_name: _FilterField | None = field(default=None, compare=False)
    finish: _FilterField | None = field(default=None, compare=False)
    color: _FilterField | None = field(default=None, compare=False)
    _makers: frozenset[str] | None = field(init=False, repr=False)
    _type_names: frozenset[str] | None = field(init=False, repr=False)
    _finishes: frozenset[str] | None = field(init=False, repr=False)
    _colors: frozenset[str] | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Cache normalized values once for repeated record matching."""
        maker = _freeze_filter_field(self.maker)
        type_name = _freeze_filter_field(self.type_name)
        finish = _freeze_filter_field(self.finish)
        color = _freeze_filter_field(self.color)
        object.__setattr__(self, "maker", maker)
        object.__setattr__(self, "type_name", type_name)
        object.__setattr__(self, "finish", finish)
        object.__setattr__(self, "color", color)
        object.__setattr__(self, "_makers", _normalize_filter_field(maker))
        object.__setattr__(self, "_type_names", _normalize_filter_field(type_name))
        object.__setattr__(self, "_finishes", _normalize_filter_field(finish))
        object.__setattr__(self, "_colors", _normalize_filter_field(color))

    @property
    def maker_values(self) -> frozenset[str] | None:
        """Return normalized maker values, if constrained."""
        return self._makers

    @property
    def type_name_values(self) -> frozenset[str] | None:
        """Return normalized filament type values, if constrained."""
        return self._type_names

    @property
    def finish_values(self) -> frozenset[str] | None:
        """Return normalized finish values, if constrained."""
        return self._finishes

    @property
    def color_values(self) -> frozenset[str] | None:
        """Return normalized color values, if constrained."""
        return self._colors

    def matches(
        self,
        maker: str,
        type_name: str,
        finish: str | None,
        color: str,
    ) -> bool:
        """Return whether all active fields match the supplied attributes."""
        if self._makers is not None and maker.strip().casefold() not in self._makers:
            return False
        if self._type_names is not None and type_name.strip().casefold() not in self._type_names:
            return False
        if self._finishes is not None:
            if finish is None or finish.strip().casefold() not in self._finishes:
                return False
        if self._colors is not None and color.strip().casefold() not in self._colors:
            return False
        return True

    @property
    def is_empty(self) -> bool:
        """Return whether no matching conditions are active."""
        return (
            self._makers is None
            and self._type_names is None
            and self._finishes is None
            and self._colors is None
        )
