"""This file sets up sample counties to use for dev/testing.

The real localizations live in a private repo.

The two counties contained here are:
    Suffix County
    Prefixton

The two are distinguished only by the way they flag individuals in the
narratives -- as you might guess, "Suffix County" uses suffixes like
"Jane Doe (S)" and Prefixton uses prefixes like "(S) Jane Doe".
"""
from collections import defaultdict

from .const import INDICATOR_POS_PREFIX, INDICATOR_POS_SUFFIX
from .locale import Locale

districts = {"Central", "Western", "Southern", "Lake", "Park", "University"}

street_names = [
    "LILAC DR",
    "COWPEN BLVD",
    "GRAND VIEW BLVD",
    "MAIN ST",
    "MAPLE ST",
    "ELM ST",
    "LAKE ST",
    "HILL ST",
    "OCEAN BLVD",
    "BIG FARM RD",
    "A ST",
    "B ST",
    "C ST",
    "D ST",
    "FIRST ST",
    "1ST AVE",
    "2ND AVE",
    "3RD AVE",
    "4TH AVE",
    "5TH AVE",
    "6TH AVE",
    "7TH AVE",
    "8TH AVE",
    "9TH AVE",
    "10TH AVE",
    "11TH AVE",
    "12TH AVE",
    "20TH ST",
    "21ST ST",
    "22ND ST",
    "RESEARCH PARK DR",
    "ELLIS COURT",
]

neighborhoods = {
    "Parkside",
    "Chinatown",
    "Eastlake",
    "Pinnacle Heights",
    "Little Russia",
    "Canal Street",
}

indicators = defaultdict(
    lambda: "Person",
    {
        "V": "Victim",
        "R": "Reporting",
        "RV": "Reporting Victim",
        "S": "Suspect",
        "W": "Witness",
        "B": "Booked",
        "M": "Missing",
    },
)

suffix_county = Locale(
    "Suffix County",
    police_districts=districts,
    street_names=street_names,
    neighborhoods=neighborhoods,
    indicators=indicators,
    indicator_position=INDICATOR_POS_SUFFIX,
    excluded_names=set(),
)

prefixton = Locale(
    "Prefixton",
    police_districts=districts,
    street_names=street_names,
    neighborhoods=neighborhoods,
    indicators=indicators,
    indicator_position=INDICATOR_POS_PREFIX,
    excluded_names=set(),
)
