"""HueForge-specific filament candidate ranking."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from color_tools.filament_palette import FilamentRecord
from color_tools.reconcilers._string_similarity import (
    HAS_RAPIDFUZZ,
    normalize_identity_text,
    similarity,
)
from color_tools.reconcilers.filament_reconciler import FilamentReconciler
from color_tools.reconcilers.filament_reconciliation_models import (
    FilamentMatchCandidate,
    FilamentMatchKind,
    FilamentReconciliationPolicy,
)


_PRODUCT_BRAND_IDENTITIES: dict[str, tuple[str, str]] = {
    normalize_identity_text("PolyLite"): ("Polymaker", "PolyLite"),
    normalize_identity_text("PolyTerra"): ("Polymaker", "PolyTerra"),
}
_TYPE_IDENTITIES: dict[str, tuple[str, str]] = {
    normalize_identity_text("Silk"): ("PLA", "Silk"),
}


def _signatures(record: FilamentRecord, maker: str) -> tuple[str, ...]:
    """Return identity layouts that account for common finish-field drift."""
    finish = record.finish or ""
    values = (
        f"{maker} {record.type} {finish} {record.color}",
        f"{maker} {finish} {record.type} {record.color}",
        f"{maker} {record.type} {record.color} {finish}",
    )
    return tuple(dict.fromkeys(normalize_identity_text(value) for value in values))


def _contains_normalized_phrase(value: str, phrase: str) -> bool:
    """Return whether a normalized identity contains a complete token phrase."""
    return f" {phrase} " in f" {value} "


@dataclass(frozen=True, slots=True)
class _CatalogIdentity:
    """Precomputed catalog identity used during one reconciliation run."""

    record: FilamentRecord
    makers: frozenset[str]
    signatures: tuple[str, ...]
    normalized_type: str
    normalized_color: str


class HueForgeFilamentReconciler(FilamentReconciler):
    """Reconcile HueForge records despite its free-form product fields.

    Candidate ranking compares multiple identity layouts so finish terms placed
    in HueForge's brand, type, or name fields can still match Color Tools'
    explicit ``finish`` field. Maker synonyms participate in both exact and
    fuzzy comparisons. Hex and TD are supporting evidence, never identities.
    """

    def __init__(
        self,
        catalog: Sequence[FilamentRecord],
        *,
        maker_synonyms: Mapping[str, Sequence[str]] | None = None,
        policy: FilamentReconciliationPolicy | None = None,
    ) -> None:
        super().__init__(catalog, policy=policy)
        self._maker_groups = self._build_maker_groups(maker_synonyms or {})
        self._catalog_identities = tuple(
            self._catalog_identity(record) for record in self._catalog
        )

    @property
    def fuzzy_matching_available(self) -> bool:
        """Return whether RapidFuzz is installed for enhanced matching."""
        return HAS_RAPIDFUZZ

    def _normalize_source_record(self, record: FilamentRecord) -> FilamentRecord:
        """Map HueForge product brands and types to canonical identities."""
        maker = record.maker
        type_name = record.type
        finish = record.finish

        product_identity = _PRODUCT_BRAND_IDENTITIES.get(
            normalize_identity_text(record.maker)
        )
        if product_identity is not None:
            maker, product_finish = product_identity
            finish = finish or product_finish

        type_identity = _TYPE_IDENTITIES.get(normalize_identity_text(record.type))
        if type_identity is not None:
            type_name, finish = type_identity

        if (maker, type_name, finish) == (record.maker, record.type, record.finish):
            return record
        return replace(
            record,
            maker=maker,
            type=type_name,
            finish=finish,
        )

    @staticmethod
    def _build_maker_groups(
        synonyms: Mapping[str, Sequence[str]],
    ) -> dict[str, frozenset[str]]:
        """Build a lookup from every normalized alias to its equivalence group."""
        groups: dict[str, frozenset[str]] = {}
        for canonical, aliases in synonyms.items():
            values = frozenset(
                normalize_identity_text(value) for value in (canonical, *aliases)
            )
            for value in values:
                groups[value] = values
        return groups

    def _maker_forms(self, maker: str) -> frozenset[str]:
        """Return normalized maker text and equivalent aliases with suffixes."""
        normalized = normalize_identity_text(maker)
        exact = self._maker_groups.get(normalized)
        if exact is not None:
            return exact
        matching_aliases = [
            alias
            for alias in self._maker_groups
            if normalized.startswith(f"{alias} ")
        ]
        if matching_aliases:
            alias = max(matching_aliases, key=lambda value: (len(value), value))
            suffix = normalized[len(alias) + 1 :]
            return frozenset(
                f"{value} {suffix}" for value in self._maker_groups[alias]
            )
        return frozenset({normalized})

    def _catalog_identity(self, record: FilamentRecord) -> _CatalogIdentity:
        """Precompute normalized values for one catalog record."""
        makers = self._maker_forms(record.maker)
        return _CatalogIdentity(
            record=record,
            makers=makers,
            signatures=tuple(
                signature
                for maker in makers
                for signature in _signatures(record, maker)
            ),
            normalized_type=normalize_identity_text(record.type),
            normalized_color=normalize_identity_text(record.color),
        )

    @staticmethod
    def _maker_is_contained(
        source_makers: frozenset[str],
        existing_makers: frozenset[str],
    ) -> bool:
        """Return whether an existing maker appears in a free-form brand."""
        return any(
            set(existing.split()) <= set(source.split())
            for source in source_makers
            for existing in existing_makers
        )

    def _plausible_catalog_identities(
        self,
        source_makers: frozenset[str],
    ) -> tuple[_CatalogIdentity, ...]:
        """Restrict expensive product matching to plausible source makers."""
        contained = tuple(
            identity
            for identity in self._catalog_identities
            if self._maker_is_contained(source_makers, identity.makers)
        )
        if contained:
            return contained

        scored_makers: dict[str, float] = {}
        for identity in self._catalog_identities:
            maker = normalize_identity_text(identity.record.maker)
            if maker in scored_makers:
                continue
            scored_makers[maker] = max(
                similarity(source, existing)
                for source in source_makers
                for existing in identity.makers
            )
        if not scored_makers:
            return ()
        best_score = max(scored_makers.values())
        plausible_makers = {
            maker
            for maker, _score in sorted(
                (
                    (maker, score)
                    for maker, score in scored_makers.items()
                    if score >= 65.0 and score >= best_score - 10.0
                ),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        }
        return tuple(
            identity
            for identity in self._catalog_identities
            if normalize_identity_text(identity.record.maker) in plausible_makers
        )

    def _rank_candidates(
        self,
        record: FilamentRecord,
    ) -> Sequence[FilamentMatchCandidate]:
        """Rank plausible catalog records by identity and supporting data."""
        source_makers = self._maker_forms(record.maker)
        source_signatures = tuple(
            signature
            for maker in source_makers
            for signature in _signatures(record, maker)
        )
        identities = self._plausible_catalog_identities(source_makers)
        candidates = [
            self._candidate(record, source_makers, source_signatures, identity)
            for identity in identities
        ]
        definitive = [candidate for candidate in candidates if candidate.kind != "fuzzy"]
        if definitive:
            candidates = definitive
        return sorted(candidates, key=lambda item: (-item.score, item.filament_id))

    def _candidate(
        self,
        source: FilamentRecord,
        source_makers: frozenset[str],
        source_signatures: tuple[str, ...],
        identity: _CatalogIdentity,
    ) -> FilamentMatchCandidate:
        """Score one imported/catalog pair."""
        existing = identity.record
        existing_makers = identity.makers
        maker_equivalent = bool(source_makers & existing_makers)
        used_synonym = maker_equivalent and normalize_identity_text(source.maker) != normalize_identity_text(existing.maker)
        signature_exact = bool(set(source_signatures) & set(identity.signatures))
        type_exact = normalize_identity_text(source.type) == identity.normalized_type
        color_exact = normalize_identity_text(source.color) == identity.normalized_color
        finish_used_as_type = (
            existing.finish is not None
            and normalize_identity_text(source.type)
            == normalize_identity_text(existing.finish)
        )
        source_identity = normalize_identity_text(
            f"{source.maker} {source.type} {source.finish or ''} {source.color}"
        )
        finish_accounted_for = existing.finish is None or _contains_normalized_phrase(
            source_identity,
            normalize_identity_text(existing.finish),
        )

        reasons: list[str] = []
        kind: FilamentMatchKind
        if maker_equivalent and type_exact and color_exact and finish_accounted_for:
            kind = "synonym" if used_synonym else "exact"
            score = 100.0
            reasons.append("structured product identity matches")
        elif maker_equivalent and color_exact and finish_used_as_type:
            kind = "synonym" if used_synonym else "normalized"
            score = 100.0
            reasons.append("finish is stored in the HueForge type field")
        elif maker_equivalent and type_exact and color_exact:
            kind = "synonym" if used_synonym else "normalized"
            score = 90.0
            reasons.append("maker, type, and color match; finish is unavailable")
        elif signature_exact:
            kind = "synonym" if used_synonym else "normalized"
            score = 100.0
            reasons.append("normalized identity matches after finish-field rearrangement")
        else:
            kind = "fuzzy"
            maker_score = max(
                similarity(left, right)
                for left in source_makers
                for right in existing_makers
            )
            type_score = similarity(source.type, existing.type)
            color_score = similarity(source.color, existing.color)
            signature_score = max(
                similarity(left, right)
                for left in source_signatures
                for right in identity.signatures
            )
            score = (
                signature_score * 0.55
                + maker_score * 0.20
                + type_score * 0.125
                + color_score * 0.125
            )
            reasons.extend(
                (
                    f"identity signature {signature_score:.1f}",
                    f"maker {maker_score:.1f}",
                    f"type {type_score:.1f}",
                    f"color {color_score:.1f}",
                )
            )

        if source.rgb_components == existing.rgb_components:
            score += (100.0 - score) * 0.50
            reasons.append("hex color matches")
        if source.td_value is not None and existing.td_value is not None:
            td_difference = abs(source.td_value - existing.td_value)
            if td_difference <= 0.01:
                score += (100.0 - score) * 0.10
                reasons.append("TD matches")
        return FilamentMatchCandidate(
            filament_id=existing.id,
            score=min(score, 100.0),
            kind=kind,
            reasons=tuple(reasons),
        )


__all__ = ["HueForgeFilamentReconciler"]
