"""Tests for the quality scoring engine."""

import pytest

from app.engine.quality_scorer import aggregate_quality_scores, compute_quality_scores


# ---------------------------------------------------------------------------
# compute_quality_scores
# ---------------------------------------------------------------------------


def test_perfect_score_no_flags():
    """No quality flags → all dimensions 1.0."""
    scores = compute_quality_scores([])
    assert scores is not None
    assert scores["completeness"] == 1.0
    assert scores["compliance"] == 1.0
    assert scores["coherence"] == 1.0
    assert scores["safety"] == 1.0
    assert scores["overall"] == 1.0


def test_none_flags_returns_none():
    """None quality flags (error request) → None scores."""
    assert compute_quality_scores(None) is None


def test_empty_flag():
    """empty flag → completeness 0.0."""
    scores = compute_quality_scores(["empty"])
    assert scores["completeness"] == 0.0
    assert scores["compliance"] == 1.0
    assert scores["coherence"] == 1.0
    assert scores["safety"] == 1.0


def test_truncated_flag():
    """truncated → completeness 0.5."""
    scores = compute_quality_scores(["truncated"])
    assert scores["completeness"] == 0.5
    assert scores["compliance"] == 1.0


def test_refusal_flag():
    """refusal → safety 0.0."""
    scores = compute_quality_scores(["refusal"])
    assert scores["safety"] == 0.0
    assert scores["completeness"] == 1.0


def test_invalid_json_flag():
    """invalid_json → compliance 0.0."""
    scores = compute_quality_scores(["invalid_json"])
    assert scores["compliance"] == 0.0


def test_format_noncompliant_flag():
    """format_noncompliant → compliance 0.5."""
    scores = compute_quality_scores(["format_noncompliant"])
    assert scores["compliance"] == 0.5


def test_multiple_compliance_flags():
    """Two compliance flags stack penalties (capped at 0.0)."""
    scores = compute_quality_scores(["invalid_json", "length_noncompliant"])
    assert scores["compliance"] == 0.0  # 1.0 - 1.0 - 0.5, capped at 0


def test_coherence_flags():
    """repeated_tokens and wrong_language affect coherence."""
    scores = compute_quality_scores(["repeated_tokens"])
    assert scores["coherence"] == 0.0
    assert scores["completeness"] == 1.0

    scores = compute_quality_scores(["wrong_language"])
    assert scores["coherence"] == 0.0


def test_overall_weighted_average():
    """Overall is a weighted average: completeness 30%, compliance 30%, coherence 20%, safety 20%."""
    scores = compute_quality_scores(["truncated"])
    # completeness=0.5, compliance=1.0, coherence=1.0, safety=1.0
    expected = 0.5 * 0.3 + 1.0 * 0.3 + 1.0 * 0.2 + 1.0 * 0.2
    assert scores["overall"] == round(expected, 4)


def test_multiple_flags_overall():
    """Multiple flags from different dimensions compound the overall score."""
    scores = compute_quality_scores(["truncated", "invalid_json", "refusal"])
    # completeness=0.5, compliance=0.0, coherence=1.0, safety=0.0
    expected = 0.5 * 0.3 + 0.0 * 0.3 + 1.0 * 0.2 + 0.0 * 0.2
    assert scores["overall"] == round(expected, 4)


def test_unknown_flag_ignored():
    """Unknown flags don't affect scores."""
    scores = compute_quality_scores(["some_future_flag"])
    assert scores["overall"] == 1.0


# ---------------------------------------------------------------------------
# aggregate_quality_scores
# ---------------------------------------------------------------------------


def test_aggregate_empty():
    """Empty input → all zeros."""
    result = aggregate_quality_scores([])
    assert result["overall"] == 0.0
    assert result["completeness"] == 0.0


def test_aggregate_single():
    """Single score → same values back."""
    single = compute_quality_scores([])
    result = aggregate_quality_scores([single])
    assert result["overall"] == 1.0
    assert result["completeness"] == 1.0


def test_aggregate_multiple():
    """Average of mixed scores."""
    perfect = compute_quality_scores([])
    truncated = compute_quality_scores(["truncated"])
    result = aggregate_quality_scores([perfect, truncated])
    # completeness: (1.0 + 0.5) / 2 = 0.75
    assert result["completeness"] == 0.75
    assert result["compliance"] == 1.0
    assert result["safety"] == 1.0


def test_aggregate_preserves_precision():
    """Aggregated scores are rounded to 4 decimal places."""
    scores = [compute_quality_scores(["format_noncompliant"]) for _ in range(3)]
    result = aggregate_quality_scores(scores)
    assert result["compliance"] == 0.5  # all identical → 0.5
