"""A collection of useful RegExp helpers"""
import re
from typing import Iterable, Optional


def re_literal_group(
    literals: Iterable[str], capture: bool = True, name: Optional[str] = None
) -> str:
    """Create a RegExp group pattern out of a list of literals.

    Sorts literals longest first in pattern to match in priority order. Values
    are escaped when added to the pattern.

    E.g., ["foo", "bar"] -> r"(foo|bar)"

    :param literals: List of literal values to match
    :param capture: Whether to format as a capturing group
    :param name: Name of capture group (ignored if capture is False)
    :returns: RegExp match group
    """
    capturing = ""
    if not capture:
        capturing = "?:"
    elif name:
        capturing = "?P<{}>".format(name)

    priority = sorted(literals, key=lambda x: len(x), reverse=True)
    pattern = r"|".join([re.escape(s) for s in priority])
    return r"({}{})".format(capturing, pattern)
