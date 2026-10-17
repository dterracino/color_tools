"""HueForge-specific filament candidate ranking."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

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


def _signatures(record: FilamentRecord, maker: str) -> tuple[str, ...]:
    """Return identity layouts that account for common finish-field drift."""
    finish = record.finish or ""
    values = (
        f"{maker} {record.type} {finish} {record.color}",
        f"{maker} {finish} {record.type} {record.color}",
        f"{maker} {record.type} {finish} {record.color}",
        f"{maker} {record.type} {record.color} {finish}",
    )
    return tuple(dict.fromkeys(normalize_identity_text(value) for value in values))


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

    @property
    def fuzzy_matching_available(self) -> bool:
        """Return whether RapidFuzz is installed for enhanced matching."""
        return HAS_RAPIDFUZZ

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
        """Return normalized maker text and all known equivalent aliases."""
        normalized = normalize_identity_text(maker)
        return self._maker_groups.get(normalized, frozenset({normalized}))

    def _rank_candidates(
        self,
        record: FilamentRecord,
    ) -> Sequence[FilamentMatchCandidate]:
        """Rank every plausible catalog record by identity and supporting data."""
        candidates = [self._candidate(record, existing) for existing in self._catalog]
        return sorted(candidates, key=lambda item: (-item.score, item.filament_id))

    def _candidate(
        self,
        source: FilamentRecord,
        existing: FilamentRecord,
    ) -> FilamentMatchCandidate:
        """Score one imported/catalog pair."""
        source_makers = self._maker_forms(source.maker)
        existing_makers = self._maker_forms(existing.maker)
        maker_equivalent = bool(source_makers & existing_makers)
        used_synonym = maker_equivalent and normalize_identity_text(source.maker) != normalize_identity_text(existing.maker)

        source_signatures = tuple(
            signature
            for maker in source_makers
            for signature in _signatures(source, maker)
        )
        existing_signatures = tuple(
            signature
            for maker in existing_makers
            for signature in _signatures(existing, maker)
        )
        signature_exact = bool(set(source_signatures) & set(existing_signatures))
        type_exact = normalize_identity_text(source.type) == normalize_identity_text(existing.type)
        color_exact = normalize_identity_text(source.color) == normalize_identity_text(existing.color)
        finish_accounted_for = (
            existing.finish is None
            or normalize_identity_text(existing.finish)
            in normalize_identity_text(
                f"{source.maker} {source.type} {source.finish or ''} {source.color}"
            ).split()
        )

        reasons: list[str] = []
        kind: FilamentMatchKind
        if maker_equivalent and type_exact and color_exact and finish_accounted_for:
            kind = "synonym" if used_synonym else "exact"
            score = 100.0
            reasons.append("structured product identity matches")
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
                for right in existing_signatures
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
            score += (100.0 - score) * 0.20
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
