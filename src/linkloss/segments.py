"""The four run segments and their boundaries. Single source of truth for window edges.

OPEN QUESTION (see docs/architecture.md): whether `response` starts when the disruption starts or
when it ends decides the H1 window. Edges are therefore stored explicitly per run (from the run's
manifest) rather than derived from a rule here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Segment(str, Enum):
    STEADY = "steady"
    DISRUPTION = "disruption"
    RESPONSE = "response"
    RECOVERY = "recovery"


ORDER: tuple[Segment, ...] = tuple(Segment)


@dataclass(frozen=True)
class SegmentEdges:
    """Five increasing timestamps (seconds, run wall-clock timebase): t0 < t1 < t2 < t3 < t4.

    steady = [t0, t1), disruption = [t1, t2), response = [t2, t3), recovery = [t3, t4].
    """

    t0: float
    t1: float
    t2: float
    t3: float
    t4: float

    def __post_init__(self) -> None:
        e = self.as_tuple()
        if any(b <= a for a, b in zip(e, e[1:])):
            raise ValueError(f"segment edges must be strictly increasing, got {e}")

    def as_tuple(self) -> tuple[float, float, float, float, float]:
        return (self.t0, self.t1, self.t2, self.t3, self.t4)

    def window(self, segment: Segment) -> tuple[float, float]:
        i = ORDER.index(segment)
        e = self.as_tuple()
        return e[i], e[i + 1]

    def segment_of(self, t: float) -> Segment | None:
        e = self.as_tuple()
        if t < e[0] or t > e[-1]:
            return None
        for i, seg in enumerate(ORDER):
            if t < e[i + 1] or (i == len(ORDER) - 1 and t <= e[-1]):
                return seg
        return None
