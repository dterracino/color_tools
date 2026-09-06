"""Predefined, lazily loaded filament collections.

The collections in this module provide convenient access to commonly used
groups of :class:`~color_tools.filament_palette.FilamentRecord` objects. The
default filament palette is loaded only when a collection is first accessed
and is then shared by every predefined collection.
"""

from functools import lru_cache
from typing import Optional

from .filament_palette import FilamentPalette, FilamentRecord


@lru_cache(maxsize=1)
def _default_palette() -> FilamentPalette:
    """Return the shared default palette used by predefined collections."""
    return FilamentPalette.load_default()


@lru_cache(maxsize=None)
def _resolve_collection(
    maker: Optional[str],
    type_name: Optional[str],
    finishes: tuple[str, ...],
) -> tuple[FilamentRecord, ...]:
    """Resolve and cache one immutable predefined collection."""
    finish = list(finishes) if finishes else None
    records = _default_palette().filter(
        maker=maker,
        type_name=type_name,
        finish=finish,
        owned=False,
    )
    return tuple(records)


class _CollectionDescriptor:
    """Descriptor that resolves a filament collection on first access."""

    def __init__(
        self,
        *,
        maker: Optional[str] = None,
        type_name: Optional[str] = None,
        finishes: tuple[str, ...] = (),
    ) -> None:
        self._maker = maker
        self._type_name = type_name
        self._finishes = finishes

    def __get__(
        self,
        instance: object,
        owner: type[object],
    ) -> tuple[FilamentRecord, ...]:
        return _resolve_collection(self._maker, self._type_name, self._finishes)


class FilamentCollections:
    """Convenient namespace for immutable, predefined filament collections.

    Collection data is loaded lazily. Each attribute returns a cached tuple
    containing all matching records in the default filament database,
    regardless of the user's owned-filament configuration.

    Examples::

        from color_tools import FilamentCollections

        for filament in FilamentCollections.BAMBU_PLA_BASIC:
            print(filament.color, filament.hex)
    """

    BAMBU_PLA_BASIC = _CollectionDescriptor(
        maker="Bambu Lab",
        type_name="PLA",
        finishes=("Basic",),
    )
    """All Bambu Lab PLA Basic filaments.

    :meta hide-value:
    """

    BAMBU_PLA_MATTE = _CollectionDescriptor(
        maker="Bambu Lab",
        type_name="PLA",
        finishes=("Matte",),
    )
    """All Bambu Lab PLA Matte filaments.

    :meta hide-value:
    """

    BAMBU_PLA_BASICMATTE = _CollectionDescriptor(
        maker="Bambu Lab",
        type_name="PLA",
        finishes=("Basic", "Matte"),
    )
    """All Bambu Lab PLA Basic and PLA Matte filaments.

    :meta hide-value:
    """


__all__ = ["FilamentCollections"]
