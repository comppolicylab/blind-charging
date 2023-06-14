from typing import Optional, Union

from .locale import Locale

_locale: Optional[Locale] = None
"""Configured locale."""


def set_locale(locale: Union[Locale, str]):
    """Set the default locale to use for masking.

    :param locale: Name of the location
    """
    global _locale
    if isinstance(locale, str):
        _locale = Locale.get(locale)
    elif isinstance(locale, Locale):
        _locale = locale
    else:
        raise TypeError(f"Unexpected locale of type {type(locale)}")


def get_locale() -> Locale:
    """Get the currently configured locale.

    :returns Locale:
    """
    if not _locale:
        raise RuntimeError("Locale is not configured yet")
    return _locale
