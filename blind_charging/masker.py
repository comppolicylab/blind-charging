import itertools
import re
from typing import DefaultDict, Dict, Generator, Iterable, List, Set, Union

from .annotation import Redaction
from .locale import Locale
from .locale.const import USPS_STREET_ABBR
from .mask_const import (
    APPEARANCE_LIST,
    COUNTRIES,
    EYE_COLORS,
    EYE_REF,
    GENERAL_COLORS,
    HAIR_ADJS,
    HAIR_COLORS,
    HAIR_REF,
    LANGUAGES,
    NATIONALITIES,
    PERSON_REF,
    RACE_ABBREV,
    RACE_FEATURES,
    RACE_WORDS,
    SENSITIVE_HAIR_REF,
    SKIN_COLORS,
)
from .officer import OfficerName
from .person import PersonName, _name_match
from .re_util import re_literal_group
from .source_text import SourceText
from .text_processing import get_officers_from_narrative, get_persons_from_narrative

AnyPerson = Union[OfficerName, PersonName]


# TODO(jnu): rewrite to generalize common behaviors. Really we only have three
# approaches: using PersonNames, using RegEx, and using NER. Generalize these
# as first-class rules that can be parameterized and applied.


def _re_literal_adj_list(adjectives: Iterable[str]) -> str:
    """
    Create a RegExp pattern for matching a list of adjectives with literals.

    :param adjectives: List of adjective literals
    :returns: RegExp pattern
    """

    adj_group = re_literal_group(adjectives)
    conj_group = re_literal_group(["and", "or"], capture=False)
    conj_sym_group = re_literal_group(["&", "/"], capture=False)
    det_group = re_literal_group(["a", "an", "the", "some", "any"], capture=False)

    return (
        # fmt: off
        r"\b{adj}(?:\s+,?\s*{adj},?)*"
        r"(?:(?:\s+{cnj}\s+|\s*{cnj_sym}\s*)(?:{det}\s+)?{adj}(?:\s+,?\s*{adj},?)*)?\b"
        # fmt: on
    ).format(adj=adj_group, cnj=conj_group, cnj_sym=conj_sym_group, det=det_group)


def _re_literal_noun_phrase(adjectives: Iterable[str], nouns: Iterable[str]) -> str:
    """Create a RegExp pattern for matching a simple noun phrase with literals.

    Example:
        pattern = f(["green", "black"], ["frog", "toad"])

        This pattern would match "green frog" and "black toad" and even
        "green and black toad."

    :param adjectives: List of adjective literals
    :param noun: List of noun literals
    :returns: RegExp pattern
    """
    adj_list = _re_literal_adj_list(adjectives)
    noun_group = re_literal_group(nouns, name="noun")

    return r"{adj}\s+{n}\b".format(adj=adj_list, n=noun_group)


def _redact_entities(
    doc: SourceText, literals: Iterable[str], placeholder: str, info: str = ""
) -> Generator[Redaction, None, None]:
    """Redact NLP entities matching the given list.

    :param doc: Source text
    :param literals: List of literal strings to match
    :param placeholder: String to use in lieu of matched entities
    :param info: Comment to pass to redaction for tracing
    :yields: Redactions
    """
    search_names = re_literal_group(literals, capture=False)
    # matches search names lazily to allow for longest search name match
    search_pattern = r"(.*?\s+)??\b{}\b(\s+.*)?".format(search_names)
    search_re = re.compile(search_pattern, re.IGNORECASE)

    for ent in doc.nlp.ents[::-1]:
        if not doc.can_redact(ent.start_char, ent.end_char):
            continue
        m = search_re.match(ent.text)
        if m:
            start = ent.start_char
            end = ent.end_char
            pfx = m.group(1) or ""
            sfx = m.group(2) or ""
            replacement = "{}[{}]{}".format(pfx, placeholder, sfx)
            yield doc.redact(start, end, replacement, info=info)


def _redact_words(
    doc: SourceText, literals: Iterable[str], placeholder: str, info: str = ""
) -> Generator[Redaction, None, None]:
    """Redact words as tokenized by NLP.

    :param doc: Source text
    :param literals: List of literal strings to match
    :param placeholder: String to use in lieu of matching words
    :param info: Comment to pass to redaction for tracing
    :yields: Redaction
    """
    candidates = set(literals)
    replacement = "[{}]".format(placeholder)

    for word in list(doc.nlp)[::-1]:
        start_char = word.idx
        end_char = start_char + len(word)
        if not doc.can_redact(start_char, end_char):
            continue
        if word.text in candidates:
            yield doc.redact(start_char, end_char, replacement, info=info)


def mask_skin_color(
    doc: SourceText, placeholder: str = "race/ethnicity"
) -> Generator[Redaction, None, None]:
    """Generate redactions for words used to describe skin color.

    E.g., "black person" -> "[race/ethnicity] person"

    NOTE: There may be overlap here with rules that deal with ethnicity
    directly.

    :param doc: Source text
    :param placeholder: String to use in lieu of skin color words.
    :yields: Redactions
    """
    pattern = _re_literal_noun_phrase(SKIN_COLORS | RACE_WORDS, PERSON_REF)
    skin_color_re = re.compile(pattern, re.IGNORECASE)

    for match in skin_color_re.finditer(doc.text):
        start, end = match.span()
        replacement = "[{}] {}".format(placeholder, match.group("noun"))
        yield doc.redact(start, end, replacement, info="skin color")


def mask_hair_color(
    doc: SourceText, placeholder: str = "color"
) -> Generator[Redaction, None, None]:
    """Generate redactions for hair color.

    E.g., "red hair" -> "[color] hair"

    :param doc: Source text
    :param placeholder: String to use in lieu of color word
    :yields: Redactions
    """
    hair_colors = GENERAL_COLORS | HAIR_COLORS
    pattern = _re_literal_noun_phrase(hair_colors, HAIR_REF)
    hair_color_re = re.compile(pattern, re.IGNORECASE)

    for match in hair_color_re.finditer(doc.text):
        start, end = match.span()
        replacement = "[{}] {}".format(placeholder, match.group("noun"))
        yield doc.redact(start, end, replacement, info="hair color")


def mask_hair_style(
    doc: SourceText, placeholder: str = "hairstyle"
) -> Generator[Redaction, None, None]:
    """Generate redactions for hair styles.

    E.g., "black short afro hair" -> "[hairstyle] hair"

    :param doc: Source text
    :param placeholder: String to use in lieu of hair style
    :yields: Redaction
    """
    hairstyle_adjs = SENSITIVE_HAIR_REF | HAIR_ADJS | GENERAL_COLORS | HAIR_COLORS
    hair_nouns = SENSITIVE_HAIR_REF | HAIR_REF
    replacement = "[{}] hair".format(placeholder)

    for pattern in [
        _re_literal_noun_phrase(hairstyle_adjs, hair_nouns),
        re_literal_group(SENSITIVE_HAIR_REF),
    ]:
        hairstyle_re = re.compile(pattern, re.IGNORECASE)
        for match in hairstyle_re.finditer(doc.text):
            start, end = match.span()
            yield doc.redact(start, end, replacement, info="hair style")


def mask_eye_color(
    doc: SourceText, placeholder: str = "color"
) -> Generator[Redaction, None, None]:
    """Generate redactions for eye color.

    E.g., "blue eyes" -> "[color] eyes"

    :param doc: Source text
    :param placeholder: String to use in lieu of color word
    :yields: Redactions
    """
    eye_colors = GENERAL_COLORS | EYE_COLORS
    pattern = _re_literal_noun_phrase(eye_colors, EYE_REF)
    eye_color_re = re.compile(pattern, re.IGNORECASE)

    for match in eye_color_re.finditer(doc.text):
        start, end = match.span()
        replacement = "[{}] {}".format(placeholder, match.group("noun"))
        yield doc.redact(start, end, replacement, info="eye color")


def mask_country(
    doc: SourceText, placeholder: str = "country"
) -> Generator[Redaction, None, None]:
    """Generate redactions for country names.

    E.g., "Burundi" -> "[country]"

    :param doc: Source text
    :param placeholder: String to use in lieu of country name
    :yields: Redactions
    """
    yield from _redact_entities(doc, COUNTRIES, placeholder, info="country")
    yield from _redact_words(doc, COUNTRIES, placeholder, info="country")


def mask_language(
    doc: SourceText, placeholder: str = "language"
) -> Generator[Redaction, None, None]:
    """Generate redactions for nationalities.

    E.g., "Spanish" -> "[language]"

    :param doc: Source text
    :param placeholder: String to use in lieu of language
    :yields: Redactions
    """
    yield from _redact_entities(doc, LANGUAGES, placeholder, info="language")
    yield from _redact_words(doc, LANGUAGES, placeholder, info="language")


def mask_nationality(
    doc: SourceText, placeholder: str = "nationality/ethnicity"
) -> Generator[Redaction, None, None]:
    """Generate redactions for nationalities.

    E.g., "Mexican" -> "[nationality/ethnicity]"

    :param doc: Source text
    :param placeholder: String to use in lieu of nationality
    :yields: Redactions
    """
    # NOTE(acw): Tried using spacy's NER classifier alone here, but it would
    # too often classify irrelevant words (e.g., "5/18/2019" or "Silver Honda")
    # as languages or locations.
    yield from _redact_entities(doc, NATIONALITIES, placeholder, info="nationality")
    yield from _redact_words(doc, NATIONALITIES, placeholder, info="nationality")


def mask_race(
    doc: SourceText, placeholder: str = "race/ethnicity"
) -> Generator[Redaction, None, None]:
    """Generate redactions for words that directly indicate race.

    E.g., "African American" -> "[race/ethnicity]"

    :param doc: Source text
    :param placeholder: String to use in lieu of race/ethnicity
    :yields: Redactions
    """
    pattern = _re_literal_adj_list(RACE_WORDS)
    race_re = re.compile(pattern, re.IGNORECASE)
    replacement = "[{}]".format(placeholder)

    for match in race_re.finditer(doc.text):
        start, end = match.span()
        yield doc.redact(start, end, replacement, info="race")


def mask_other_literals(
    doc: SourceText,
    literals: dict[str, list[str]] | None,
) -> Generator[Redaction, None, None]:
    """Generate redactions based on custom lists of literal words.

    Example:
        literals = {
            "district": ["lake district", "park district"],
            }

        "The suspect was last seen the Park District" ->
        "The suspect was last seen in the [district]"

    :param doc: Source text
    :param literals: Dictionary describing literal words to redact. Keys will
        be used to substitute for each of the values in the associated list.
    :yields: Redactions
    """
    if literals is None:
        return

    for literal, values in literals.items():
        pattern = re_literal_group(values)
        literal_re = re.compile(pattern, re.IGNORECASE)
        replacement = "[{}]".format(literal)

        for match in literal_re.finditer(doc.text):
            start, end = match.span()
            yield doc.redact(start, end, replacement, info=literal)


def mask_race_correlated_feature(
    doc: SourceText, placeholder: str = "physical description"
) -> Generator[Redaction, None, None]:
    """Generate redactions for feature that are highly correlated with race
    without context.

    E.g., "We saw a blonde" -> "We saw a [physical description]"

    :param doc: Source text
    :param placeholder: String to use in lieu of race-correlated features
    :yields: Redactions
    """
    feature_group = re_literal_group(RACE_FEATURES)
    pattern = r"\b{}\b".format(feature_group)
    feature_re = re.compile(pattern, re.IGNORECASE)
    replacement = "[{}]".format(placeholder)

    for match in feature_re.finditer(doc.text):
        start, end = match.span()
        yield doc.redact(start, end, replacement, info="race")


def mask_race_abbrev(
    doc: SourceText, placeholder: str = "race/ethnicity"
) -> Generator[Redaction, None, None]:
    """Generate redactions for abbreviated words that directly indicate race.

    E.g., "AMA" -> "[race/ethnicity] male adult"

    :param doc: Source text
    :param placeholder: String to use in lieu of race/ethnicity
    :yields: Redactions
    """
    race_group = RACE_ABBREV
    pattern = r"(?<=\b){}s?(?=\b)".format(race_group)
    race_re = re.compile(pattern)  # dont ignore case

    sex_dict = {"F": "female", "M": "male"}
    age_dict = {"A": "adult", "J": "juvenile"}

    for match in race_re.finditer(doc.text):
        start, end = match.span()
        # insert female/male, adult/juvenile depending on 2nd and 3rd groups
        replacement = "[{}] {} {}".format(
            placeholder, sex_dict.get(match.group(2)), age_dict.get(match.group(3))
        )
        yield doc.redact(start, end, replacement, info="race")


def mask_appearance_list(
    doc: SourceText, placeholder: str = "color"
) -> Generator[Redaction, None, None]:
    """Generate redactions for words in list format that directly indicate race.

    E.g., "Race: Hispanic" -> "Race: [race/ethnicity]"
    E.g., "Hair: Black" -> "Hair: [color]"

    :param doc: Source text
    :param placeholder: String to use in lieu of feature
    :yields: Redactions
    """
    color_group = _re_literal_adj_list(
        SKIN_COLORS | HAIR_COLORS | HAIR_ADJS | EYE_COLORS | GENERAL_COLORS
    )
    appearance_group = re_literal_group(APPEARANCE_LIST, name="noun")
    pattern = r"{}:\s*{}".format(appearance_group, color_group)
    appearance_list_re = re.compile(pattern, re.IGNORECASE)

    for match in appearance_list_re.finditer(doc.text):
        if match.group("noun").lower() in ["race", "complexion"]:
            placeholder = "race/ethnicity"
            info = "race"
        elif match.group("noun") == "eyes":
            info = "eye color"
        elif match.group("noun") == "hair":
            info = "hair color"
        else:
            info = "appearance list"

        start, end = match.span()
        replacement = "{}: [{}]".format(match.group("noun"), placeholder)
        yield doc.redact(start, end, replacement, info=info)


def mask_street_address(
    doc: SourceText, placeholder: str = "location"
) -> Generator[Redaction, None, None]:
    """Generate redactions for street addresses.

    E.g., "123 Maple St." -> "[location] St."

    :param doc: Source text
    :param placeholder: Text to use in lieu of literal street address
    :yields: Redactions
    """
    endings_group = re_literal_group(USPS_STREET_ABBR)
    street_addr_re = re.compile(
        r"(?:\d{1,5} [\w\s]{1,20}) (" + endings_group + r"\.?)\W?(?=\s|$)",
        re.IGNORECASE,
    )

    # Avoid matching false street locations:
    # e.g. 30 mph, #2 lane
    bad_patterns_re = re.compile(
        r"\d{1,3}\s?mph\b|\b#?\d\s?([nesw]/?b\s?)?lane\b",  # speed | lane in road
        re.IGNORECASE,
    )

    for match in street_addr_re.finditer(doc.text):
        matched_text = match.group(0)
        if bad_patterns_re.search(matched_text):
            continue

        start, end = match.span()
        replacement = "[{}] {}".format(placeholder, match.group(1))
        yield doc.redact(start, end, replacement, info="street address")


def mask_district(
    doc: SourceText, locale: Locale, placeholder: str = "district"
) -> Generator[Redaction, None, None]:
    """Generate redactions for police precincts.

    :param doc: Source text
    :param locale: Locale to use for masking
    :param placeholder: Text to use in lieu of literal district name
    :yields: Redactions
    """
    for match in locale.match_district(doc.text):
        start, end = match.span()
        sfx = (match.group(2) or "").lower()
        # Avoid adding suffix if it'd be awkwardly redundant, as in the case
        # of "[district] district"
        sfx = "" if sfx == placeholder else sfx
        replacement = "[{}]".format(placeholder)
        if sfx:
            replacement += " " + sfx
        yield doc.redact(start, end, replacement, info="district name")


def mask_presumed_street_name(
    doc: SourceText, placeholder: str = "street"
) -> Generator[Redaction, None, None]:
    """Generate redactions for entities that look like street names.

    E.g., "Maple St." -> "[street] St."

    :param doc: Source text
    :param placeholder: Text to use in lieu of street name
    :yields: Redactions
    """
    ending_variants = sum(
        [[abbr, abbr.capitalize(), abbr.upper()] for abbr in USPS_STREET_ABBR],
        list[str](),
    )
    street_endings = re_literal_group(ending_variants, capture=False)
    street_name_pattern = (
        r"(?:(?:\d+|[A-Z])[A-Za-z\']*\s+)+"
        + r"(%s\.?)" % street_endings
        + r"(?=[,\/#!$%\^&\*;:{}=\-_`~()\s])"
    )
    # Last pattern matches any `\b` except `\.` (matched in second pattern)
    # This keeps the period (e.g. in "St.") in the placeholder
    # NOTE(jnu): this is not case insensitive; the point is to use the
    # capitalization structure to infer words that might constitute a street
    # name.
    street_name_re = re.compile(street_name_pattern)

    # Avoid matching false street names:
    # e.g. EB lane, E/B lane, #2 lane (on the freeway)
    bad_patterns_re = re.compile(r"\b(#?\d\s)?([nesw]/?b\s?)?lane\b", re.IGNORECASE)

    for match in street_name_re.finditer(doc.text):
        matched_text = match.group(0)
        if bad_patterns_re.search(matched_text):
            continue

        start, end = match.span()
        replacement = "[{}] {}".format(placeholder, match.group(1))
        yield doc.redact(start, end, replacement, info="presumed street name")


def mask_known_street_name(
    doc: SourceText, locale: Locale, placeholder: str = "street"
) -> Generator[Redaction, None, None]:
    """Generate redactions for known streets in the city.

    E.g., "Arguello and Euclid" -> "[street] and [street]"

    :param doc: Source text
    :param locale: Locale to use for masking
    :param placeholder: Text to use in lieu of street name
    :yields: Redactions
    """
    for match in locale.match_street_name(doc.text):
        start, end = match.span()
        replacement = "[{placeholder}]{conj}[{placeholder}]".format(
            placeholder=placeholder, conj=match.group("conj")
        )
        yield doc.redact(start, end, replacement, info="known street name")


def mask_neighborhood(
    doc: SourceText, locale: Locale, placeholder: str = "neighborhood"
) -> Generator[Redaction, None, None]:
    """Generate redactions for neighborhoods in the city.

    E.g., "Parkside" -> "[neighborhood]"

    :param doc: Source text
    :param locale: Locale to use to perform masking
    :param placeholder: Text to use in lieu of neighborhood name
    :yields: Redactions
    """
    # TODO(jnu): improve Locale API for matching these
    yield from _redact_entities(
        doc, locale.neighborhoods, placeholder, info="neighborhood"
    )


def _create_person_name_map(persons: Iterable[AnyPerson]) -> Dict[str, Set[AnyPerson]]:
    """Create a map from surface name representations to persons.

    The map connects the surface representations of a human name (such as
    "John P. Smith") to the PersonName instances that this name could refer to.
    In most cases this should be unique, however there may be ambiguous cases
    such as "J. Smith" that might refer to multiple individuals.

    :param persons: List of person references
    :returns: Map from names to person references
    """
    m = DefaultDict[str, Set[AnyPerson]](set)

    for p in persons:
        for s in p.name_rep():
            m[s].add(p)

    return dict(m)


def mask_person(
    doc: SourceText,
    persons: Iterable[AnyPerson],
    info: str,
) -> Generator[Redaction, None, None]:
    """Generate a list of redactions for the persons given in the input.

    :param doc: Source text
    :param persons: List of person references to redact
    :param annotations: List of existing annotations (passed to avoid adding
    conflicting annotations on a range)
    :yields: Redaction instances
    """
    person_signs = _create_person_name_map(persons)

    # Process surface representations of names in order of longest to shortest.
    # This means the longest names will be replaced first, which should help to
    # avoid ambiguity.
    sorted_signs = sorted(person_signs.items(), key=lambda x: len(x[0]), reverse=True)

    for signifier, signified in sorted_signs:
        # Ambiguous references:
        pattern = re.compile(signifier, re.IGNORECASE)
        ordered_signified = sorted(signified, key=lambda a: a.get_indicator())
        if info == "officer":
            # replacement as "Officer #1 or Officer #2"
            codename = " or ".join([p.get_indicator() for p in ordered_signified])
        elif info == "person":
            # replacement as "(PERSON_1 or PERSON_2)"" rather than "(PERSON_1) or (PERSON_2)""
            codename = "(%s)" % " or ".join(
                [re.sub(r"[\(\)]", "", p.get_indicator()) for p in ordered_signified]
            )

        for match in pattern.finditer(doc.text):
            replacement = codename
            start, end = match.span()
            # Special case: the rare terminal-apostrophe possessive, such as
            # "Moses'" where the correct redaction synthetically adds the 's.
            # TODO(jnu): probably better to handle this where we handle the
            # indefinite article redaction, in SourceText.
            if doc.text[end : end + 2] == "' ":
                replacement = codename + "'s"
                end += 1

            # TODO(jnu): clean up coloring and classing
            ordered_signified[0]
            yield doc.redact(
                start,
                end,
                replacement,
                auto_capitalize=False,
                autocorrect_article=False,
                info=info,
            )


def mask_person_fuzzy(
    doc: SourceText,
    persons: Iterable[PersonName],
    info: str,
) -> Generator[Redaction, None, None]:
    """Generate a list of redactions for the persons given in the input
    by redacting proper nouns in the text which are similar to last names in
    persons.

    :param doc: Source text
    :param persons: List of person references to redact
    :param annotations: List of existing annotations (passed to avoid adding
    conflicting annotations on a range)
    :yields: Redaction instances
    """

    min_character_limit = 5
    propn_tokens = {
        token
        for token in doc.nlp
        if token.pos_ == "PROPN" and len(token) > min_character_limit
    }

    for token in propn_tokens:
        start_char = token.idx
        end_char = start_char + len(token)

        if not doc.can_redact(start_char, end_char):
            continue
        else:
            valid_persons = [
                person
                for person in persons
                if _name_match({f"{person.first} {person.last}"}, {token.text.upper()})
                or _name_match(person.last, {token.text.upper()}, 1)
                or _name_match(person.first, {token.text.upper()}, 1)
            ]

            if valid_persons:
                replacement = "(%s)" % " or ".join(
                    [
                        re.sub(r"[\(\)]", "", person.get_indicator())
                        for person in valid_persons
                    ]
                )
                yield doc.redact(
                    start_char,
                    end_char,
                    replacement,
                    auto_capitalize=False,
                    autocorrect_article=False,
                    info=info,
                )


def mask(
    locale: Locale,
    narrative: str,
    persons: Iterable[PersonName],
    officers: Iterable[OfficerName],
    literals: dict[str, list[str]] | None = None,
) -> List[Redaction]:
    """Apply masking and formatting to narrative text.

    :param narrative: Incident report text
    :param persons: List of names of people appearing in text
    :param OfficerName: List of names of officers appearing in text
    :param literals: Optional dictionary of custom lists to extend redaction
    :returns: List of redactions
    """
    doc = SourceText(narrative)

    return list(
        itertools.chain(
            mask_person(doc, officers, "officer"),
            mask_person(doc, persons, "person"),
            mask_street_address(doc),
            mask_district(doc, locale),
            mask_known_street_name(doc, locale),
            mask_presumed_street_name(doc),
            mask_neighborhood(doc, locale),
            mask_skin_color(doc),
            mask_hair_style(doc),
            mask_hair_color(doc),
            mask_eye_color(doc),
            mask_appearance_list(doc),
            mask_race_abbrev(doc),
            mask_race(doc),
            mask_race_correlated_feature(doc),
            mask_country(doc),
            mask_language(doc),
            mask_nationality(doc),
            mask_person_fuzzy(doc, persons, "person"),
            mask_other_literals(doc, literals),
        )
    )


def merge_annotations(annotations, narrative: str) -> List[Redaction]:
    """Merge 'person' annotations that contain the same text and info
    if they are only separated by a single white space

    e.g. "(S1) (S1)" -> "(S1)"
    :param annotations: unsorted list of annotations
    :param narrative: Incident report text
    :returns: reverse sorted list of merged annotations
    """
    if not annotations or len(annotations) <= 1:
        return annotations

    # order redactions by character number, last to first
    annotations.sort(key=lambda x: x.start, reverse=True)

    final_annotations = list[Redaction]()
    end_annotation = annotations[0]

    for annotation in annotations[1:]:
        if (
            end_annotation.start - annotation.end <= 1
            and end_annotation.text == annotation.text
            and end_annotation.info == annotation.info
            and end_annotation.info == "person"
            and re.match(r"\s", narrative[annotation.end : end_annotation.start])
        ):
            end_annotation.start = annotation.start
        else:
            final_annotations.append(end_annotation)
            end_annotation = annotation
    final_annotations.append(end_annotation)

    return final_annotations


def annotate(
    locale: Locale,
    narrative: str,
    persons: Iterable[dict],
    officers: Iterable[dict],
    redact_officers_from_text: bool = True,
    literals: dict[str, list[str]] | None = None,
) -> List[Redaction]:
    """Apply redaction tool and formatting to narrative text.

    :param locale: location of narrative
    :param narrative: Incident report text
    :param persons: List of people appearing in text
    :param officers: List of officers appearing in text
    :param redact_officers_from_text: Whether to redact officers from text
    :param literals: Optional dictionary of custom lists to extend redaction
    :returns: redaction annotations
    """
    person_types = set(locale.indicators.keys())

    persons = locale.filter_names(persons)
    formatted_persons = [PersonName(**person) for person in persons]
    formatted_officers = [OfficerName(**officer) for officer in officers]

    # get_persons_from_narrative only applicable to sf right now, will refactor later
    formatted_persons += get_persons_from_narrative(narrative, 0, person_types)
    if redact_officers_from_text:
        formatted_officers += get_officers_from_narrative(narrative)

    formatted_persons = PersonName.dedupe(formatted_persons, locale)
    formatted_officers = OfficerName.dedupe(formatted_officers, locale)

    # create redactions
    annotations = mask(
        locale,
        narrative,
        persons=formatted_persons,
        officers=formatted_officers,
        literals=literals,
    )
    return merge_annotations(annotations, narrative)
