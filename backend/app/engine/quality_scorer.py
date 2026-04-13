"""Quality scoring engine.

Computes per-request dimension scores (0.0–1.0) from quality flags.

Dimensions:
- completeness: penalised by empty / truncated
- compliance: penalised by invalid_json / format_noncompliant / length_noncompliant
- coherence: penalised by repeated_tokens / wrong_language
- safety: penalised by refusal

Overall = weighted average (completeness 30%, compliance 30%, coherence 20%, safety 20%).
"""

from __future__ import annotations

DIMENSION_WEIGHTS = {
    "completeness": 0.30,
    "compliance": 0.30,
    "coherence": 0.20,
    "safety": 0.20,
}

# Maps each flag to (dimension, penalty).
# A request with that flag gets its dimension score reduced by the penalty.
_FLAG_PENALTIES: dict[str, tuple[str, float]] = {
    "empty": ("completeness", 1.0),
    "truncated": ("completeness", 0.5),
    "invalid_json": ("compliance", 1.0),
    "format_noncompliant": ("compliance", 0.5),
    "length_noncompliant": ("compliance", 0.5),
    "repeated_tokens": ("coherence", 1.0),
    "wrong_language": ("coherence", 1.0),
    "refusal": ("safety", 1.0),
}


def compute_quality_scores(quality_flags: list[str] | None) -> dict[str, float] | None:
    """Compute per-request quality dimension scores from quality flags.

    Returns None when quality_flags is None (error requests).
    Returns dict with keys: completeness, compliance, coherence, safety, overall.
    """
    if quality_flags is None:
        return None

    # Start each dimension at 1.0
    scores: dict[str, float] = {
        "completeness": 1.0,
        "compliance": 1.0,
        "coherence": 1.0,
        "safety": 1.0,
    }

    for flag in quality_flags:
        if flag in _FLAG_PENALTIES:
            dimension, penalty = _FLAG_PENALTIES[flag]
            scores[dimension] = max(0.0, scores[dimension] - penalty)

    # Overall weighted average
    overall = sum(scores[dim] * weight for dim, weight in DIMENSION_WEIGHTS.items())
    scores["overall"] = round(overall, 4)

    # Round dimensions too
    for dim in list(scores):
        scores[dim] = round(scores[dim], 4)

    return scores


def aggregate_quality_scores(
    all_scores: list[dict[str, float]],
) -> dict[str, float]:
    """Average quality scores across multiple requests.

    Returns dict with averaged dimension scores. Empty input returns all zeros.
    """
    if not all_scores:
        return {
            "completeness": 0.0,
            "compliance": 0.0,
            "coherence": 0.0,
            "safety": 0.0,
            "overall": 0.0,
        }

    dimensions = ["completeness", "compliance", "coherence", "safety", "overall"]
    n = len(all_scores)
    return {
        dim: round(sum(s.get(dim, 0.0) for s in all_scores) / n, 4)
        for dim in dimensions
    }
