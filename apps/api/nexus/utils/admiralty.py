"""Admiralty grading system for intelligence reliability assessment."""


def compute_reliability_grade(source_type: str, historical_accuracy: float) -> str:
    """Compute Admiralty source reliability grade (A-F).

    A = Completely reliable (>0.95)
    B = Usually reliable (>0.80)
    C = Fairly reliable (>0.60)
    D = Not usually reliable (>0.40)
    E = Unreliable (>0.20)
    F = Reliability cannot be judged
    """
    if historical_accuracy > 0.95:
        return "A"
    elif historical_accuracy > 0.80:
        return "B"
    elif historical_accuracy > 0.60:
        return "C"
    elif historical_accuracy > 0.40:
        return "D"
    elif historical_accuracy > 0.20:
        return "E"
    else:
        return "F"


def compute_credibility_grade(
    cross_source_count: int,
    consistency: float,
    recency_hours: float,
) -> str:
    """Compute Admiralty information credibility grade (1-6).

    1 = Confirmed by other sources
    2 = Probably true
    3 = Possibly true
    4 = Doubtful
    5 = Improbable
    6 = Truth cannot be judged
    """
    if cross_source_count >= 3 and consistency > 0.9:
        return "1"
    elif cross_source_count >= 2 and consistency > 0.7:
        return "2"
    elif cross_source_count >= 1 and consistency > 0.5:
        return "3"
    elif consistency > 0.3:
        return "4"
    elif consistency > 0.1:
        return "5"
    else:
        return "6"


def compute_confidence_score(
    source_reliability: float,
    cross_corroboration: float,
    recency_factor: float,
    consistency: float,
    weights: tuple[float, float, float, float] = (0.3, 0.3, 0.2, 0.2),
) -> float:
    """Compute a practical confidence score from multiple factors.

    S = w1*SourceReliability + w2*CrossCorroboration + w3*Recency + w4*Consistency
    Returns a value between 0.0 and 1.0.
    """
    w1, w2, w3, w4 = weights
    score = (
        w1 * source_reliability
        + w2 * cross_corroboration
        + w3 * recency_factor
        + w4 * consistency
    )
    return max(0.0, min(1.0, score))


def admiralty_to_label(reliability: str, credibility: str) -> str:
    """Convert Admiralty grades to a human-readable label like 'B2'."""
    return f"{reliability}{credibility}"
