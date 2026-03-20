"""Dempster-Shafer theory of evidence for intelligence fusion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MassFunction:
    """A basic probability assignment (mass function) over a frame of discernment.

    Each key is a frozenset of hypotheses, and the value is the mass assigned to it.
    The sum of all masses must equal 1.0.
    """

    masses: dict[frozenset[str], float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.masses:
            # Default: complete uncertainty
            self.masses = {frozenset(["TRUE", "FALSE"]): 1.0}

    @property
    def frame(self) -> frozenset[str]:
        """The full frame of discernment (union of all hypotheses)."""
        all_hyps: set[str] = set()
        for key in self.masses:
            all_hyps.update(key)
        return frozenset(all_hyps)


class DempsterShaferEngine:
    """Dempster-Shafer evidence combination engine."""

    @staticmethod
    def combine(m1: MassFunction, m2: MassFunction) -> MassFunction:
        """Combine two mass functions using Dempster's Rule of Combination.

        m12(A) = (1 / (1-K)) * sum(m1(B) * m2(C) for B,C where B ∩ C = A)
        K = sum(m1(B) * m2(C) for B,C where B ∩ C = ∅)
        """
        combined: dict[frozenset[str], float] = {}
        conflict = 0.0

        for b, mb in m1.masses.items():
            for c, mc in m2.masses.items():
                intersection = b & c
                product = mb * mc

                if not intersection:
                    conflict += product
                else:
                    combined[intersection] = combined.get(intersection, 0.0) + product

        if conflict >= 1.0:
            # Total conflict — return maximum uncertainty
            frame = m1.frame | m2.frame
            return MassFunction(masses={frame: 1.0})

        # Normalize by (1 - K)
        normalizer = 1.0 - conflict
        normalized = {
            key: val / normalizer for key, val in combined.items()
        }

        return MassFunction(masses=normalized)

    @staticmethod
    def combine_multiple(mass_functions: list[MassFunction]) -> MassFunction:
        """Iteratively combine multiple mass functions."""
        if not mass_functions:
            return MassFunction()
        if len(mass_functions) == 1:
            return mass_functions[0]

        result = mass_functions[0]
        for mf in mass_functions[1:]:
            result = DempsterShaferEngine.combine(result, mf)

        return result

    @staticmethod
    def belief(mf: MassFunction, hypothesis: frozenset[str]) -> float:
        """Belief (Bel) = sum of masses of all subsets of the hypothesis."""
        bel = 0.0
        for focal, mass in mf.masses.items():
            if focal and focal.issubset(hypothesis):
                bel += mass
        return bel

    @staticmethod
    def plausibility(mf: MassFunction, hypothesis: frozenset[str]) -> float:
        """Plausibility (Pl) = 1 - Bel(complement)."""
        complement = mf.frame - hypothesis
        return 1.0 - DempsterShaferEngine.belief(mf, complement)

    @staticmethod
    def uncertainty(mf: MassFunction, hypothesis: frozenset[str]) -> float:
        """Uncertainty interval = Pl(A) - Bel(A)."""
        return (
            DempsterShaferEngine.plausibility(mf, hypothesis)
            - DempsterShaferEngine.belief(mf, hypothesis)
        )

    @staticmethod
    def evidence_to_mass(
        source_reliability: float,
        supports_hypothesis: bool,
        hypothesis: str = "TRUE",
        anti_hypothesis: str = "FALSE",
    ) -> MassFunction:
        """Convert a single piece of evidence into a mass function.

        Args:
            source_reliability: How reliable the source is (0.0–1.0).
            supports_hypothesis: Whether this evidence supports or refutes the hypothesis.
            hypothesis: The supported hypothesis name.
            anti_hypothesis: The opposing hypothesis name.

        Returns:
            A MassFunction with appropriate masses.
        """
        frame = frozenset([hypothesis, anti_hypothesis])

        if supports_hypothesis:
            return MassFunction(masses={
                frozenset([hypothesis]): source_reliability,
                frame: 1.0 - source_reliability,
            })
        else:
            return MassFunction(masses={
                frozenset([anti_hypothesis]): source_reliability,
                frame: 1.0 - source_reliability,
            })

    @staticmethod
    def conflict_level(m1: MassFunction, m2: MassFunction) -> float:
        """Compute the conflict factor K between two mass functions.

        K > 0.3 suggests significant disagreement between sources.
        """
        conflict = 0.0
        for b, mb in m1.masses.items():
            for c, mc in m2.masses.items():
                if not (b & c):
                    conflict += mb * mc
        return conflict
