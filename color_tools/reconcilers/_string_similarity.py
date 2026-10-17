"""Dependency-optional normalized string similarity helpers."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Callable

try:
    from rapidfuzz import fuzz as _rapidfuzz
except ImportError:
    _rapidfuzz = None


HAS_RAPIDFUZZ = _rapidfuzz is not None


def normalize_identity_text(value: str) -> str:
    """Normalize punctuation, spacing, camel case, and plus notation."""
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    expanded = expanded.casefold().replace("+", " plus ")
    return " ".join(re.findall(r"[a-z0-9]+", expanded))


def _sequence_ratio(left: str, right: str) -> float:
    """Return a standard-library sequence similarity percentage."""
    return SequenceMatcher(None, left, right).ratio() * 100.0


def _fallback_token_set_ratio(left: str, right: str) -> float:
    """Approximate token-set matching without an optional dependency."""
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    intersection = sorted(left_tokens & right_tokens)
    left_remainder = sorted(left_tokens - right_tokens)
    right_remainder = sorted(right_tokens - left_tokens)
    common = " ".join(intersection)
    left_combined = " ".join(intersection + left_remainder)
    right_combined = " ".join(intersection + right_remainder)
    return max(
        _sequence_ratio(common, left_combined),
        _sequence_ratio(common, right_combined),
        _sequence_ratio(left_combined, right_combined),
    )


def similarity(left: str, right: str) -> float:
    """Return the strongest deterministic normalized similarity score."""
    normalized_left = normalize_identity_text(left)
    normalized_right = normalize_identity_text(right)
    if normalized_left == normalized_right:
        return 100.0
    if not normalized_left or not normalized_right:
        return 0.0
    if _rapidfuzz is not None:
        scorers: tuple[Callable[[str, str], float], ...] = (
            _rapidfuzz.ratio,
            _rapidfuzz.token_sort_ratio,
            _rapidfuzz.token_set_ratio,
        )
        return max(float(scorer(normalized_left, normalized_right)) for scorer in scorers)
    compact_left = normalized_left.replace(" ", "")
    compact_right = normalized_right.replace(" ", "")
    sorted_left = " ".join(sorted(normalized_left.split()))
    sorted_right = " ".join(sorted(normalized_right.split()))
    return max(
        _sequence_ratio(normalized_left, normalized_right),
        _sequence_ratio(compact_left, compact_right),
        _sequence_ratio(sorted_left, sorted_right),
        _fallback_token_set_ratio(normalized_left, normalized_right),
    )


__all__ = ["HAS_RAPIDFUZZ", "normalize_identity_text", "similarity"]
