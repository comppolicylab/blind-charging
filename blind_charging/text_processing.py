"""Utilities for understanding the narrative text.

This module does not do masking per se, but the information gleaned through
these utilities can be used to inform masking.
"""
import re
from typing import List, Optional, Set

import unidecode

from .locale.const import INDICATOR_POS_PREFIX, INDICATOR_POS_SUFFIX
from .mask_const import NAME_PHRASES
from .officer import OfficerName
from .person import PersonName
from .re_util import re_literal_group
from .source_text import nlp


def _add_person_mention(
    mentions: List[PersonName],
    indicator: str,
    report_id: int,
    name: Optional[str] = None,
) -> None:

    text_indicator_regex = re_literal_group(NAME_PHRASES, capture=False)
    text_indicator_regex = r"\b" + text_indicator_regex + r"\b,?"
    text_p = re.compile(text_indicator_regex, re.IGNORECASE)

    if not text_p.match(indicator):
        mentions.append(PersonName(indicator, report_id, name))
    elif text_p.match(indicator) and name:
        mentions.append(PersonName("", report_id, name))


def preprocess(narrative: str) -> str:
    """Apply formatting to text to make it easier to mask.

    :param narrative: Raw text of police narrative
    :returns: Cleaner text ready for processing
    """
    if not narrative:
        return ""
    # NOTE(jnu): any alterations made here should be fine to return either as
    # masked or unmasked text. The resulting text should be treated as the
    # "true" narrative that we want to present.
    narrative = unidecode.unidecode(narrative)
    # TODO(jnu): why is this one necessary?
    narrative = narrative.replace("¿", "'")
    return narrative


def get_persons_from_narrative(
    narrative: str,
    report_id: int,
    person_types: Set[str],
) -> List[PersonName]:
    """Infer Persons mentioned in the narrative.

    Only persons flagged with indicators such as R/V are returned.

    :param narrative: Narrative text
    :param report_id: ID of report
    :param person_types: Known person types listed on this report
    :returns: List of PersonNames
    """
    doc = nlp(narrative)

    if "R/V" in person_types or "V" in person_types:
        person_types = person_types.union({"R/V", "V"})
    if "R/W" in person_types or "W" in person_types:
        person_types = person_types.union({"R/W", "W"})
    person_types = {x.replace("/", "/?") for x in person_types}

    indicator_regex = r"(" + r"|".join(person_types) + r")"
    indicator_regex = r"(?:^|(?<=\W))\(" + indicator_regex + r"(-|/)?\d{1,2}\)(?=\W)"

    front_indicator_regex = r"(" + r"|".join(person_types) + r")"
    front_indicator_regex = (
        r"(?<=\b)" + front_indicator_regex + r"\d{0,2}(-|/)(?=[a-zA-Z])"
    )

    text_indicator_regex = re_literal_group(NAME_PHRASES, capture=False)
    text_indicator_regex = r"\b" + text_indicator_regex + r"\b,?"

    # Find involved-person indicator flags
    p = re.compile(indicator_regex)
    indicators = sorted(p.finditer(doc.text), key=lambda x: x.start())

    front_p = re.compile(front_indicator_regex)
    front_indicators = sorted(front_p.finditer(doc.text), key=lambda x: x.start())

    text_p = re.compile(text_indicator_regex, re.IGNORECASE)
    text_indicators = sorted(text_p.finditer(doc.text), key=lambda x: x.start())

    mentions = list[PersonName]()

    for indicator_position in [INDICATOR_POS_PREFIX, INDICATOR_POS_SUFFIX]:
        # Build a map from indicator position to the matched indicator for all
        # the person entities.
        if indicator_position is INDICATOR_POS_PREFIX:
            person_pos = {e.start_char: e for e in doc.ents if e.label_ == "PERSON"}
        elif indicator_position is INDICATOR_POS_SUFFIX:
            person_pos = {e.end_char: e for e in doc.ents if e.label_ == "PERSON"}
        if indicator_position is INDICATOR_POS_PREFIX:
            indicators += front_indicators
            indicators += text_indicators

        for indicator in indicators:
            # NOTE: The end index is exclusive of any part of the indicator. That
            # is, the character at that position is outside the indicator token.
            if indicator_position is INDICATOR_POS_PREFIX:
                end_idx = indicator.end()
            elif indicator_position is INDICATOR_POS_SUFFIX:
                start_idx = indicator.start()

            # Find person references that come after the indicator and compute
            # their distance.
            if indicator_position is INDICATOR_POS_PREFIX:
                diffs = [
                    (pos - end_idx, ent)
                    for pos, ent in person_pos.items()
                    if pos >= end_idx
                ]
            elif indicator_position is INDICATOR_POS_SUFFIX:
                diffs = [
                    (start_idx - pos, ent)
                    for pos, ent in person_pos.items()
                    if pos <= start_idx
                ]

            # If no person comes after this, add just the indicator.
            if not diffs:
                _add_person_mention(mentions, indicator.group(), report_id)
                continue

            # Take the lowest positive position difference
            offset, next_person = sorted(diffs, key=lambda pair: pair[0])[0]
            # Examine the substring between the indicator and the person. Reject
            # this person if it's not clearly associated with the indicator.
            if indicator_position is INDICATOR_POS_PREFIX:
                tween = doc.text[end_idx : end_idx + offset]
            elif indicator_position is INDICATOR_POS_SUFFIX:
                tween = doc.text[start_idx - offset : start_idx]

            # If there's more than just spaces between the tokens, assume the
            # person is not associated with the indicator, and just add the
            # indicator.
            # TODO(jnu): Probably want more sophisticated logic; some punctuation
            # is probably ok.
            if tween.strip():
                _add_person_mention(mentions, indicator.group(), report_id)
                continue

            # Check if the name is informative. If not, just add the indicator.
            name = next_person.text.strip()
            if "UNKNOWN" in name.upper():
                _add_person_mention(mentions, indicator.group(), report_id)
                continue

            # If we get here, conclude that the name pertains to the indicator.
            _add_person_mention(mentions, indicator.group(), report_id, name)

    return mentions


def get_officers_from_narrative(narrative: str) -> List[OfficerName]:
    """Extract officer names from the narrative text.

    :param narrative: Police report text
    :returns: List of officer names
    """
    dgt5_re = OfficerName.dgt5_re
    t_re = OfficerName.t_re
    n_re = OfficerName.n_re
    star_re = OfficerName.star_re
    officer_regexes = [
        #  (1A23B) (Ofc.) John Doe #1234
        r"(" + dgt5_re + ")?(" + t_re + ")?(" + n_re + "){1,2}(" + star_re + ")",
        #  (1A23B) Ofc. John Doe (#1234)
        r"(" + dgt5_re + ")?" + t_re + "(" + n_re + ")+(" + star_re + ")?",
        #  (1A23B) Ofc. (John Doe) #1234
        r"(" + dgt5_re + ")?" + t_re + "((" + n_re + ")+)?(" + star_re + ")",
        # 1A23B
        dgt5_re,
    ]
    p = re.compile("(" + ")|(".join(officer_regexes) + ")")
    mentions = []
    for m in p.finditer(narrative):
        mentions.append(OfficerName(m.group()))

    return mentions
