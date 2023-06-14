import unittest

from blind_charging.broken_range import BrokenRange


class TestBrokenRange(unittest.TestCase):
    def test_overlaps(self):
        b = BrokenRange()
        b.addspan(5, 8)
        assert b.overlaps(4, 6)
        assert b.overlaps(6, 7)
        assert b.overlaps(7, 8)
        assert b.overlaps(7, 9)
        assert not b.overlaps(1, 2)
        # Exclusive end
        assert not b.overlaps(4, 5)
        assert not b.overlaps(8, 10)

    def test_contains(self):
        b = BrokenRange()
        b.addspan(5, 8)
        assert not b.contains(4)
        assert b.contains(5)
        assert b.contains(6)
        assert b.contains(7)
        # Exclusive end
        assert not b.contains(8)
        assert not b.contains(9)

    def test_range_merging(self):
        b = BrokenRange()
        b.addspan(5, 10)
        assert b._range == [5, 10]
        b.addspan(0, 1)
        assert b._range == [0, 1, 5, 10]
        b.addspan(2, 3)
        assert b._range == [0, 1, 2, 3, 5, 10]
        b.addspan(10, 15)
        assert b._range == [0, 1, 2, 3, 5, 15]
        b.addspan(2, 20)
        assert b._range == [0, 1, 2, 20]
        b.addspan(-1, 100)
        assert b._range == [-1, 100]
