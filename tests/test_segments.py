import pytest

from linkloss.segments import Segment, SegmentEdges

EDGES = SegmentEdges(0.0, 60.0, 90.0, 120.0, 180.0)


def test_windows():
    assert EDGES.window(Segment.STEADY) == (0.0, 60.0)
    assert EDGES.window(Segment.RESPONSE) == (90.0, 120.0)


def test_segment_of_boundaries():
    assert EDGES.segment_of(0.0) is Segment.STEADY
    assert EDGES.segment_of(60.0) is Segment.DISRUPTION
    assert EDGES.segment_of(179.9) is Segment.RECOVERY
    assert EDGES.segment_of(180.0) is Segment.RECOVERY
    assert EDGES.segment_of(-1.0) is None
    assert EDGES.segment_of(181.0) is None


def test_edges_must_increase():
    with pytest.raises(ValueError):
        SegmentEdges(0.0, 60.0, 60.0, 120.0, 180.0)
