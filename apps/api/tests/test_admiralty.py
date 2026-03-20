"""Admiralty grading system tests."""

from nexus.utils.admiralty import (
    compute_reliability_grade,
    compute_credibility_grade,
    compute_confidence_score,
    admiralty_to_label,
)


def test_reliability_grade_a():
    assert compute_reliability_grade("api", 0.98) == "A"


def test_reliability_grade_b():
    assert compute_reliability_grade("api", 0.85) == "B"


def test_reliability_grade_f():
    assert compute_reliability_grade("unknown", 0.1) == "F"


def test_credibility_grade_confirmed():
    assert compute_credibility_grade(cross_source_count=3, consistency=0.95, recency_hours=1) == "1"


def test_credibility_grade_probably():
    assert compute_credibility_grade(cross_source_count=2, consistency=0.8, recency_hours=10) == "2"


def test_confidence_score_range():
    score = compute_confidence_score(
        source_reliability=0.8,
        cross_corroboration=0.7,
        recency_factor=0.9,
        consistency=0.85,
    )
    assert 0.0 <= score <= 1.0


def test_admiralty_label():
    assert admiralty_to_label("B", "2") == "B2"
    assert admiralty_to_label("A", "1") == "A1"
