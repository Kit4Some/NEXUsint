"""Data fusion engine — Dempster-Shafer, cross-INT correlation, evidence combination."""

from nexus.fusion.dempster_shafer import DempsterShaferEngine, MassFunction
from nexus.fusion.cross_int_correlator import (
    CrossIntCorrelator,
    CorrelationResult,
    Chain,
)
from nexus.fusion.evidence_combiner import (
    EvidenceCombiner,
    CombinedEvidence,
    ConflictReport,
)

__all__ = [
    "DempsterShaferEngine",
    "MassFunction",
    "CrossIntCorrelator",
    "CorrelationResult",
    "Chain",
    "EvidenceCombiner",
    "CombinedEvidence",
    "ConflictReport",
]
