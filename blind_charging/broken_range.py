"""Data type for discontinuous ranges."""
from typing import List, Tuple


def _find_index(R: List[int], value: int, inside: bool = False) -> int:
    """Find the index of the member equal to or greater than the input value.

    :param R: List of range blocks, as [b0_s, b0_e, ... ]
    :param value: Value to search for
    :param inside: Use > instead of >= as comparator
    :returns: The index of the smallest member greater than or equal to the
    input value. The return value will be equal to the length of the list if
    there is no member that's greater or equal to the input.
    """
    if not R:
        return 0

    low = 0
    high = len(R)

    while (high - low) > 1:
        mid = low + ((high - low) >> 1)
        if value < R[mid]:
            high = mid
        else:
            low = mid

    idx = low if value <= R[low] else high

    if idx == len(R):
        return idx

    if inside and R[idx] == value:
        return idx + 1
    return idx


class BrokenRange(object):
    """Representation of a discontinuous range.

    Includes utilities to update range and merge overlaps.
    """

    def __init__(self):
        self._range: List[int] = []

    def addspan(self, start: int, end: int):
        """Incorporate span [start, end) into the range.

        :param start: Index of start
        :param end: Index of end (exclusive)
        :returns: BrokenRange (self)
        """
        if end <= start:
            raise ValueError("Invalid extent: {}".format(end - start))

        R = self._range

        # Find the index in the range of the start of the block where this
        # span should go.
        start_idx = _find_index(R, start)
        if start_idx % 2 == 1:
            start_idx -= 1

        # When the span is higher than any existing block, just append it.
        # This handles the initial condition when no ranges have been added
        # as well.
        if start_idx == len(R):
            self._range += [start, end]
            return self

        # Find the index in the range of the end of the block where this
        # span should go.
        end_idx = _find_index(R, end + 1)
        if end_idx % 2 == 0:
            end_idx -= 1

        # When the span precedes any existing block, prepend it.
        if end_idx < 0:
            self._range = [start, end] + R
            return self

        block_start = min(start, R[start_idx])
        block_end = max(end, R[end_idx])
        self._range = R[:start_idx] + [block_start, block_end] + R[end_idx + 1 :]

        return self

    def contains(self, value: int) -> bool:
        """Test whether a value is contained in the range.

        :param value: Value to test
        :returns: Boolean indicating membership
        """
        idx = _find_index(self._range, value)

        # If the index is out of range, value is not contained
        if idx == len(self._range):
            return False

        # If the index is even, it must be exact match to be contained.
        # If the index is odd, it must *not* be exact match to be contained.
        if idx % 2 == 0:
            return value == self._range[idx]
        else:
            return value != self._range[idx]

    def overlaps(self, start: int, end: int) -> bool:
        """Test whether given span overlaps any part of this range.

        :param start: Start of span
        :param end: End of span
        :returns: Boolean indicating overlap
        """
        if end <= start:
            raise ValueError("Invalid extent: {}".format(end - start))

        start_idx = _find_index(self._range, start, inside=True)
        end_idx = _find_index(self._range, end, inside=False)

        # An odd index implies span starts inside block
        if start_idx % 2 == 1:
            return True

        # Otherwise if the span crosses any range, there must be overlap.
        return start_idx != end_idx

    def __iadd__(self, span: Tuple[int, int]) -> "BrokenRange":
        return self.addspan(span[0], span[1])

    def __repr__(self) -> str:
        R = self._range
        spans = ["[{},{}]".format(R[i], R[i + 1]) for i in range(0, len(R), 2)]
        return "BrokenRange({})".format(",".join(spans))
