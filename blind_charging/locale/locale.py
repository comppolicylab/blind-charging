"""Localization utilities for redaction."""
import re
from typing import Dict, Iterable, List

from ..re_util import re_literal_group
from .const import USPS_STREET_ABBR

# Track all instances to provide a lookup API
_REGISTRY: Dict[str, "Locale"] = {}


class Locale:
    """A collection of information specific to a city or region.

    Provides match helpers to facilitate location-aware redaction.
    """

    def __new__(cls, *args, **kwargs) -> "Locale":
        inst = super().__new__(cls)
        _REGISTRY[args[0].lower()] = inst
        return inst

    @staticmethod
    def get(name: str) -> "Locale":
        """Fetch a locale by name.

        :param name: Name of locale
        :returns: Locale instance
        :raises ValueError: If locale doesn't exist
        """
        locale = _REGISTRY.get(name.lower(), None)
        if not locale:
            raise ValueError("Locale {} not found".format(name))
        return locale

    @classmethod
    def _compile_district_re(cls, districts: Iterable[str]) -> re.Pattern:
        district_names_pattern = re_literal_group(districts)
        suffixes_pattern = re_literal_group(
            [
                r"police station",
                r"station",
                r"district",
                r"unit",
            ]
        )
        full_pattern = r"{}\s+{}".format(district_names_pattern, suffixes_pattern)
        return re.compile(full_pattern, re.IGNORECASE)

    @classmethod
    def _compile_street_name_re(cls, street_names: Iterable[str]) -> re.Pattern:
        # Mask known street names that appear but might not have street indicators.
        # Only in strict situations (where we see "Streetname & Streetname" or
        # "Streetname and Streetname")
        street_variants = sum(
            [[name, name.capitalize(), name.upper()] for name in street_names],
            list[str](),
        )
        street_group = re_literal_group(street_variants)
        ending_variants: List[str] = sum(
            [[abbr, abbr.capitalize(), abbr.upper()] for abbr in USPS_STREET_ABBR],
            list[str](),
        )
        endings = re_literal_group(ending_variants)
        optional_endings = r"(?:\s+{})?".format(endings)
        single_street = r"{}{}".format(street_group, optional_endings)
        # Matches street names (g) separated by some "and" or "/"
        # Requires word boundaries before and after match (avoids matching "PD & FD")
        # <conj> used in `mask_known_street_name`
        # NOTE(jnu): search is case sensitive to avoid overmatching, such as "apple and cherry."
        intersection = (
            r"(?<=\b){g}(?P<conj>(?:\s+(?:and|And|AND|\&)\s+)|\s*/\s*){g}(?=\b)".format(
                g=single_street
            )
        )
        return re.compile(intersection)

    @classmethod
    def _compile_excluded_name_re(cls, excluded_names: Iterable[str]) -> re.Pattern:
        # Don't re.escape() names - assume important regex features are included
        pattern = r"|".join(excluded_names)
        return re.compile(pattern, re.IGNORECASE)

    def __init__(
        self,
        name: str,
        police_districts: Iterable[str],
        street_names: Iterable[str],
        excluded_names: Iterable[str],
        neighborhoods: Iterable[str],
        indicators: Dict,
        indicator_position: str,
    ):
        self.name = name
        self._district_re = self._compile_district_re(police_districts)
        self._street_name_re = self._compile_street_name_re(street_names)
        self._excluded_name_re = self._compile_excluded_name_re(excluded_names)
        self.neighborhoods = neighborhoods
        self.indicators = indicators
        self.indicator_position = indicator_position

    def match_district(self, text: str) -> Iterable[re.Match]:
        """Find police district names within the text."""
        return self._district_re.finditer(text)

    def match_street_name(self, text: str) -> Iterable[re.Match]:
        """Find known street names within the text."""
        return self._street_name_re.finditer(text)

    def filter_names(self, persons: Iterable[dict]) -> Iterable[dict]:
        """Trim and remove ineligible names from inputted persons list."""

        filtered_persons = []
        for person in persons:
            # remove person if name literal is missing
            if not person["name"]:
                continue

            person["name"] = person["name"].strip().lower()

            if person["name"] in ["", "n/a", "na", "none", "missing"]:
                continue

            # remove person if name is excluded
            if self._excluded_name_re.match(person["name"]):
                continue

            filtered_persons.append(person)

        return filtered_persons
