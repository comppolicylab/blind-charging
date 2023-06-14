import re
import unittest
from typing import Iterable

import blind_charging as bc
import blind_charging.text_processing as tp
from blind_charging.locale import Locale
from blind_charging.officer import OfficerName
from blind_charging.person import PersonName


class TestMask(unittest.TestCase):
    def mask_tester(self, locale, s_test, s_correct, person_types):
        text = tp.preprocess(s_test)

        person_list = tp.get_persons_from_narrative(text, 123, person_types)
        persons = PersonName.dedupe(person_list, Locale.get(locale))
        officers = OfficerName.dedupe(
            tp.get_officers_from_narrative(text), Locale.get(locale)
        )

        bc.set_locale(locale)
        redacted_narrative = bc.redact(text, persons, officers)

        # TODO(jnu): should just assert on raw annotations, not on
        # masking application. Rewrite test cases to do so.
        s = re.sub(r"<([^<]+?)>", "\\1", redacted_narrative)
        self.assertEqual(s, s_correct, "Failed masking!")

    def redactor_tester(
        self,
        locale,
        s_test,
        s_correct,
        person_list: Iterable[dict],
        officer_list: Iterable[str],
        redact_officers_from_text=True,
    ):
        bc.set_locale(locale)
        redacted_narrative = bc.redact(
            s_test, person_list, officer_list, redact_officers_from_text
        )
        s = re.sub(r"<([^<]+?)>", "\\1", redacted_narrative)
        self.assertEqual(s, s_correct, "Failed masking!")

    # ==================== GENERAL TESTS ======================

    def test_basic_mask_prefix(self):
        s_test = (
            "Upon approaching the intersection of 9th Ave. "
            "and Howard St., "
            "I observed Hispanic male later identified as (B1) John Doe who "
            "matched the suspect description"
        )
        s_correct = (
            "Upon approaching the intersection of [street] Ave. "
            "and [street] St., "
            "I observed [race/ethnicity] male later identified as (B1) "
            "who matched the suspect description"
        )
        self.mask_tester("Prefixton", s_test, s_correct, {"B"})

    def test_basic_mask_suffix(self):
        s_test = (
            "Upon approaching the intersection of 9th Ave. "
            "and Howard St., "
            "I observed Hispanic male later identified as John Doe (B1) who "
            "matched the suspect description"
        )
        s_correct = (
            "Upon approaching the intersection of [street] St. "
            "and [street] St., "
            "I observed [race/ethnicity] male later identified as (B1) "
            "who matched the suspect description"
        )
        self.mask_tester("Suffix County", s_test, s_correct, {"B"})

    # ==================== LOCATION TESTS ======================

    def test_street_name_only(self):
        s_test = (
            "This incident happens at 20th/Oak. It's "
            "also observed at the intersection of Ocean and Hill."
        )
        s_correct = (
            "This incident happens at [street]/[street]. It's "
            "also observed at the intersection of [street] and [street]."
        )
        self.mask_tester("Prefixton", s_test, s_correct, {})
        # self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_street_suffix_park(self):
        s_test = "This incident happens at 417 Ocean Park."
        s_correct = "This incident happens at [location] Park."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_multiple_street_suffix(self):
        s_test = "We were at 1771 Research Park Drive."
        s_correct = "We were at [location] Drive."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_street_suffix_court(self):
        # too difficult to resolve.
        # court conflicts with "DMV court", "Zoom court" etc.
        s_test = "This incident happens at Ellis Court."
        s_correct = "This incident happens at [street] Court."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_court_num(self):
        s_test = "I booked this person for 69 PC court #12345"
        s_correct = "I booked this person for 69 PC court #12345"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_intersection_1(self):
        s_test = "BWC and ICC video(s) available"
        s_correct = "BWC and ICC video(s) available"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_intersection_2(self):
        s_test = "PFD and PPD were dispatched"
        s_correct = "PFD and PPD were dispatched"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_intersection_3(self):
        s_test = "walking N/B Lilac Drive."
        s_correct = "walking N/B [street] Drive."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_intersection_1(self):
        s_test = "corner of Lilac Drive and Cowpen Blvd."
        s_correct = "corner of [street] and [street]."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_intersection_2(self):
        s_test = "at First Street and A Street for"
        s_correct = "at [street] and [street] for"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_intersection_3(self):
        # space after "/"
        # issue: not grabbing longest string?
        # - after adding "\b" to intersection regex, only matching "East" rather than "East 8th"
        # Suggestion: add cardinal direction as suffix to street name?
        s_test = "at Big Farm Rd/ East 8th St. enroute"
        s_correct = "at [street]/[street] enroute"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_way_1(self):
        s_test = "WILL BE IN THE WAY"
        s_correct = "WILL BE IN THE WAY"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_way_2(self):
        # failed
        s_test = "driving 30 MPH on the freeway"
        s_correct = "driving 30 MPH on the freeway"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_lane_1(self):
        # failed
        s_test = "he was in the #2 lane of the freeway"
        s_correct = "he was in the #2 lane of the freeway"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_lane_2(self):
        s_test = "he drove into the W/B lane"
        s_correct = "he drove into the W/B lane"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    # ==================== RACE TESTS ======================

    def test_a_an_words1(self):
        s_test = "I observe an African American male."
        s_correct = "I observe a [race/ethnicity] male."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words2(self):
        s_test = "Witness described a white male."
        s_correct = "Witness described a [race/ethnicity] male."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words3(self):
        s_test = "An African American male"
        s_correct = "A [race/ethnicity] male"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words4(self):
        s_test = "An African-American male"
        s_correct = "A [race/ethnicity] male"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words5(self):
        s_test = "A white adult"
        s_correct = "A [race/ethnicity] adult"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words6(self):
        # mask_race or clause
        s_test = "She is potentially african-american or hispanic."
        s_correct = "She is potentially [race/ethnicity]."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words7(self):
        # mask_skin_color or clause
        s_test = "She looked like a black or brown woman."
        s_correct = "She looked like a [race/ethnicity] woman."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words8(self):
        s_test = "She looked like a white or hispanic woman."
        s_correct = "She looked like a [race/ethnicity] woman."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_a_an_words9(self):
        # fails as white is not in RACE_WORDS (mask_race)
        s_test = "She is potentially white or hispanic."
        s_correct = "She is potentially [race/ethnicity]."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_race_abbrev_1(self):
        s_test = "described as a BMA"
        s_correct = "described as a [race/ethnicity] male adult"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_race_abbrev_2(self):
        s_test = "described as a WFJ or HFJ"
        s_correct = "described as a [race/ethnicity] female juvenile or [race/ethnicity] female juvenile"  # noqa: B950
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_race_list_1(self):
        s_test = "Sex: M, Race: Black, Height: 5'11"
        s_correct = "Sex: M, Race: [race/ethnicity], Height: 5'11"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_race_list_2(self):
        # unexpected space between characters
        s_test = "Sex: M, Race:White, Height: 5'11"
        s_correct = "Sex: M, Race: [race/ethnicity], Height: 5'11"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_race_list_3(self):
        s_test = "She described him as being white or Hispanic."
        s_correct = "She described him as being [race/ethnicity] or [race/ethnicity]."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], False)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], False)

    def test_a_an_words_no_overmatch(self):
        # Avoid matching -an at end of previous word
        s_test = "Human African American male"
        s_correct = "Human [race/ethnicity] male"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_neighborhood_false_1(self):
        # failed
        s_test = "We used a Narcotic Identification Kit."
        s_correct = "We used a Narcotic Identification Kit."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Williams, Malik"}],
            [],
            False,
        )
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], False)

    def test_race_eol(self):
        s_test = "The suspect appeared to be Hispanic."
        s_correct = "The suspect appeared to be [race/ethnicity]."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], False)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], False)

    def test_slur_no_space(self):
        s_test = "John said, 'Chink!'"
        s_correct = "John said, '[race/ethnicity]!'"
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], False)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], False)

    # ==================== COUNTRY TESTS ======================
    def test_country_china_short(self):
        s_test = "a passport from China"
        s_correct = "a passport from [country]"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_country_china_long(self):
        s_test = "who was identified with a People's Republic of China passport."
        s_correct = "who was identified with a [country] passport."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_country_false_1(self):
        # failed
        s_test = "We detained Malik Williams."
        s_correct = "We detained (S1)."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Williams, Malik"}],
            [],
            False,
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Williams, Malik"}],
            [],
            False,
        )

    # ==================== OFFICER TESTS ======================

    def test_officer_vs_location(self):
        s_test = "David Smith #1234 booked the person into County Jail #1."
        s_correct = "Officer #1 booked the person into County Jail #1."
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_officer_bad_segmentation(self):
        s_test = "Officer Krupke# 1234 later transported person to station"
        s_correct = "Officer #1 later transported person to station"
        self.mask_tester("Prefixton", s_test, s_correct, {})
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_officer_no_redact(self):
        s_test = "Officer Krupke #1234 later transported person to station"
        s_correct = "Officer Krupke #1234 later transported person to station"
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], False)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], False)

    def test_officer_false_1(self):
        # failed
        s_test = "The California Peace Officer Standards required us to"
        s_correct = "The California Peace Officer Standards required us to"
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], True)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], True)

    def test_officer_false_2(self):
        # failed
        s_test = "EVIDENCE:\nBWC #101\nRECOMMENDATION:"
        s_correct = "EVIDENCE:\nBWC #101\nRECOMMENDATION:"
        self.redactor_tester("Prefixton", s_test, s_correct, [], [], True)
        self.redactor_tester("Suffix County", s_test, s_correct, [], [], True)

    # ==================== PERSON TESTS ======================

    def test_possessive(self):
        s_test = "Someone snatched (R/V1) Jesus' handbag"
        s_correct = "Someone snatched (RV1)'s handbag"
        self.mask_tester("Prefixton", s_test, s_correct, {})

    def test_person_composite_last_name(self):
        s_test = (
            "I encounter (B1) John Jake Doe Smith, "
            "who is later being referrede as John or Doe."
        )
        s_correct = "I encounter (B1), " "who is later being referrede as (B1) or (B1)."
        self.mask_tester("Prefixton", s_test, s_correct, {})

    def test_person_mispelled(self):
        # redacted mispelled name as the same person
        s_test = "I encounter (B1) John Smith. (B1) Johna Smith was out"
        s_correct = "I encounter (B1). (B1) was out"
        self.mask_tester("Prefixton", s_test, s_correct, {"B"})

    def test_person_redact_prefix_1(self):
        # NER test - without indicator
        s_test = "I encounter (B1) John Smith."
        s_correct = "I encounter (B1)."
        self.mask_tester("Prefixton", s_test, s_correct, {})

    def test_person_redact_prefix_2(self):
        # NER test - with indicator
        s_test = "I encounter (B1) John Smith."
        s_correct = "I encounter (B1)."
        self.mask_tester("Prefixton", s_test, s_correct, {"B"})

    def test_person_redact_prefix_3(self):
        # double indicator as using redact_person rather than get_persons
        s_test = "I encounter (B1) John Smith."
        s_correct = "I encounter (B1) (B1)."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "B", "name": "Smith, John"}],
            [],
        )

    def test_person_redact_prefix_flip(self):
        # redact prefix when specified as suffix
        s_test = "I encounter (B1) John Smith."
        s_correct = "I encounter (B1)."
        self.redactor_tester("Suffix County", s_test, s_correct, [], [])

    def test_person_new_indicator_1(self):
        # NER test - with alternative S/ prefix indicator
        s_test = "I encounter S/John Smith."
        s_correct = "I encounter S/(S1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_person_new_indicator_2(self):
        # NER test - with alternative W/ prefix indicator
        s_test = "I encounter W/John Smith."
        s_correct = "I encounter W/(W1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_person_new_indicator_3(self):
        # NER test - with alternative S- prefix indicator
        s_test = "I encounter S-John Smith."
        s_correct = "I encounter S-(S1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_person_redact_prefix_start(self):
        # NER test - with indicator
        # double indicator as using redact_person rather than get_persons
        s_test = "(B1) John Smith went for a walk."
        s_correct = "(B1) went for a walk."
        self.mask_tester("Prefixton", s_test, s_correct, {"B"})

    def test_person_redact_prefix_two_digits(self):
        # NER test - with indicator
        # double indicator as using redact_person rather than get_persons
        s_test = "(B12) John Smith went for a walk."
        s_correct = "(B1) went for a walk."
        self.mask_tester("Prefixton", s_test, s_correct, {"B"})

    def test_person_redact_prefix_forward_slash(self):
        # NER test - with indicator
        # double indicator as using redact_person rather than get_persons
        s_test = "(R/V1) John Smith went for a walk."
        s_correct = "(RV1) went for a walk."
        self.mask_tester("Prefixton", s_test, s_correct, {"R/V"})

    def test_person_redact_prefix_forward_slash_missing(self):
        # NER test - with indicator
        # double indicator as using redact_person rather than get_persons
        s_test = "(RV1) John Smith went for a walk."
        s_correct = "(RV1) went for a walk."
        self.mask_tester("Prefixton", s_test, s_correct, {"R/V"})

    def test_person_redact_prefix_hyphen(self):
        # NER test - with indicator
        # double indicator as using redact_person rather than get_persons
        s_test = "(S-1) John Smith went for a walk."
        s_correct = "(S1) went for a walk."
        self.mask_tester("Prefixton", s_test, s_correct, {"S"})

    def test_person_redact_suffix_1(self):
        # without PersonName, without indicator
        s_test = "I encounter John Smith (B1)."
        s_correct = "I encounter (B1)."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_person_redact_suffix_2(self):
        # without PersonName, with indicator
        s_test = "I encounter John Smith (B1)."
        s_correct = "I encounter (B1)."
        self.mask_tester("Suffix County", s_test, s_correct, {"B"})

    def test_person_redact_suffix_3(self):
        # with PersonName => double indicator?
        # double indicator as using redact_person rather than get_persons
        s_test = "I encounter John Smith (B1)."
        s_correct = "I encounter (B1) (B1)."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "B", "name": "Smith, John"}],
            [],
        )

    def test_person_redact_suffix_flip(self):
        # redact suffix when specified as prefix
        s_test = "I encounter John Smith (B1)."
        s_correct = "I encounter (B1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_person_redact_false_prefix(self):
        # ensure NER doesn't pick up on false indicator (\w\d{2})
        s_test = "He had an outstanding warrant (W10-101)."
        s_correct = "He had an outstanding warrant (W10-101)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_person_reverse_name(self):
        # when true name is "John Smith", but input is "John, Smith"
        s_test = "I encounter (B1) John Smith."
        s_correct = "I encounter (B1)."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "B", "name": "John, Smith"}],
            [],
        )

    def test_person_middle_name(self):
        # when narrative references "Will Smith" when true name is "John Will Smith"
        s_test = "I encounter (B1) Fred Smith."
        s_correct = "I encounter (B1)."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "B", "name": "Smith, John Fred"}],
            [],
        )

    def test_no_indicator_redaction_1(self):
        s_test = "explained that Hoa has been intimidating"
        s_correct = "explained that (S1) has been intimidating"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_indicator_redaction_2(self):
        # NER test - with text prefix indicator
        s_test = "I encountered a man with the name of John Smith."
        s_correct = "I encountered a man with the name of (PERSON_1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_no_indicator_redaction_3(self):
        # NER test - with text prefix indicator
        s_test = "He mentioned his ex-girlfriend, Lindsey Johnson."
        s_correct = "He mentioned his ex-girlfriend, (PERSON_1)."
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_no_indicator_redaction_4(self):
        # NER test - with multiple text prefix indicators
        s_test = "I found a card in the name of Bob Smith and a card in the name of Jamie Jim."
        s_correct = "I found a card in the name of (PERSON_1) and a card in the name of (PERSON_2)."  # noqa: B950
        self.redactor_tester("Prefixton", s_test, s_correct, [], [])

    def test_enumeration_error_1(self):
        # how are enumerations assigned? alphabetically?
        s_test = (
            "Officer Story #227 obtained a statement from the witness, Susan Talesfore (W)."
            "I later contacted the second witness, Taylor Bassell (W)."
        )
        s_correct = (
            "Officer #1 obtained a statement from the witness, (W1) (W)."
            "I later contacted the second witness, (W2) (W)."
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "W", "name": "Talesfore, Susan J"},
                {"indicator": "W", "name": "Bassell, Taylor Marie"},
            ],
            [],
        )

    def test_enumeration_error_2(self):
        # last output: M2, then M1
        s_test = "Angulo was on the phone with her district manager, Aneela Akram."
        s_correct = "(M2) was on the phone with her district manager, (M1)."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "M", "name": "Akram, Aneela"},
                {"indicator": "M", "name": "Angulo, Beatriz Elena"},
            ],
            [],
        )

    def test_enumeration_error_3(self):
        # includes mispelled jenilynn.
        # no indicator so mispelt person not added + matched by levenstein
        # last output: W2 then W1
        s_test = "told two employees: JENILYN NEWTON and PHILIP ESDAILE"
        s_correct = "told two employees: (W2) and (W1)"
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "W", "name": "Esdaile, Philip John"},
                {"indicator": "W", "name": "Newton, Jenilynn Elizabeth"},
            ],
            [],
        )

    def test_enumeration_error_4(self):
        # last output: M2 then M1
        s_test = "Mysko told Zihao what was happening"
        s_correct = "(M2) told (M1) what was happening"
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "M", "name": "Dai, Zihao"},
                {"indicator": "M", "name": "Mysko, Stepan"},
            ],
            [],
        )

    def test_person_ambiguous_last_name_1(self):
        s_test = "Rachel and Thomas Smith were both at the scene."
        s_correct = "(R1) and (W1) were both at the scene."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "R", "name": "Smith, Rachel"},
                {"indicator": "W", "name": "Smith, Thomas"},
            ],
            [],
        )

    def test_person_ambiguous_last_name_2(self):
        # unclear what the right solution is
        s_test = "Rachel and Thomas Smith were both at the scene."
        s_correct = "(R1) and (PERSON_1) were both at the scene."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "R", "name": "Smith, Rachel"}],
            [],
        )

    def test_person_ambiguous_last_name_3(self):
        s_test = "Smith provided the following description."
        s_correct = "(R1 or W1) provided the following description."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "R", "name": "Smith, Rachel"},
                {"indicator": "W", "name": "Smith, Thomas"},
            ],
            [],
        )

    def test_person_ambiguous_first_name(self):
        # test case for fixing ambiguity
        s_test = "Daniel reported the incident promptly."
        s_correct = "(R1 or W1) reported the incident promptly."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "R", "name": "John, Daniel"},
                {"indicator": "W", "name": "Kim, Daniel"},
            ],
            [],
        )

    def test_person_reordered_name(self):
        # test case for unordered name
        s_test = "Smith reported the incident promptly."
        s_correct = "(R1) reported the incident promptly."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "R", "name": "Daniel Smith"}],
            [],
        )

    def test_person_reordered_suffix(self):
        # test case for unordered name
        s_test = "John Doe reported the incident promptly."
        s_correct = "(R1) reported the incident promptly."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "R", "name": "Doe, John Jr."}],
            [],
        )

    def test_invalid_name_1(self):
        # test: City of Suffix filtered as invalid name, not redacted
        s_test = "I work for the City of Suffix."
        s_correct = "I work for the City of Suffix."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "City of Suffix"}],
            [],
        )

    def test_invalid_name_2(self):
        # test: State of California filtered as invalid name, not redacted
        s_test = "I live in California."
        s_correct = "I live in California."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "State Of California"}],
            [],
        )

    def test_invalid_name_3(self):
        # test: NA not enumerated
        s_test = "We saw Wong and Smith at the bus stop."
        s_correct = "We saw Wong and (V1) at the bus stop."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "V", "name": "N/A"},
                {"indicator": "V", "name": "Smith, Adam"},
            ],
            [],
        )

    def test_name_regex(self):
        # test: regex expressions dont match
        s_test = "I saw Adam in the driveway."
        s_correct = "I saw (V1) in the driveway."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Adam [.*] Smith"}],
            [],
        )

    def test_single_name(self):
        s_test = "I went to Walmart at 10:20am."
        s_correct = "I went to (V1) at 10:20am."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Walmart"}],
            [],
        )

    def test_missing_last_name(self):
        s_test = "I went to Walmart at 10:20am."
        s_correct = "I went to (V1) at 10:20am."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": ", Walmart"}],
            [],
        )

    def test_name_unexpected_character_parentheses(self):
        # test: removes parentheses and redacts name
        s_test = "I went to Walmart at 10:20am."
        s_correct = "I went to (V1) at 10:20am."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Walmart (WSAC)"}],
            [],
        )

    def test_name_unexpected_character_space(self):
        # test: all names are stripped
        s_test = "We saw Wu standing outside."
        s_correct = "We saw (V1) standing outside."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Wu , Hong"}],
            [],
        )

    def test_name_abbreviated_middle(self):
        # test: redacts abbreviated names
        s_test = "The caller was Anne G. Smith."
        s_correct = "The caller was (V1)."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Anne G. Smith"}],
            [],
        )

    def test_name_line_break(self):
        s_test = "I saw John\nSmith climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, John"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, John"}],
            [],
        )

    def test_name_unexpected_character_hyphen(self):
        # test: redacts hyphenated names
        s_test = "Garcia-Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_name_unexpected_character_hyphen_overredaction(self):
        s_test = "We bought 3-4 dozen eggs last week."
        s_correct = "We bought 3-4 dozen eggs last week."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Grocery Outlet - WS"}],
            [],
        )

    def test_hyphenated_surname_front(self):
        s_test = "Garcia was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_hyphenated_surname_back(self):
        s_test = "Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_hyphenated_surname_space(self):
        s_test = "Garcia Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_hyphenated_surname_hyphen(self):
        s_test = "Garcia-Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_hyphenated_surname_concatenated(self):
        s_test = "Garciahernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_compound_surname_front(self):
        s_test = "Garcia was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia Hernandez, David"}],
            [],
        )

    def test_compound_surname_back(self):
        s_test = "Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia Hernandez, David"}],
            [],
        )

    def test_compound_surname_space(self):
        s_test = "Garcia Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia Hernandez, David"}],
            [],
        )

    def test_compound_surname_hyphen(self):
        s_test = "Garcia-Hernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia Hernandez, David"}],
            [],
        )

    def test_compound_surname_concatenated(self):
        s_test = "Garciahernandez was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "Garcia-Hernandez, David"}],
            [],
        )

    def test_compound_surname_three_full(self):
        s_test = "de la Cruz was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "de la Cruz, David"}],
            [],
        )

    def test_compound_surname_three_back(self):
        s_test = "Cruz was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "de la Cruz, David"}],
            [],
        )

    def test_compound_surname_three_concatenated(self):
        s_test = "delacruz was at his doorstep."
        s_correct = "(V1) was at his doorstep."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "V", "name": "de la Cruz, David"}],
            [],
        )

    # ==================== FUZZY NAME MATCH TESTS ======================

    def test_name_fuzzy_add(self):
        # added "l"
        s_test = "I saw Zalvala climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Zavala, Jose"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Zavala, Jose"}],
            [],
        )

    def test_name_fuzzy_substitute(self):
        # switched "c" with "t"
        s_test = "I saw Valentia climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Valencia, Mariela"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Valencia, Mariela"}],
            [],
        )

    def test_name_fuzzy_switch(self):
        # switched "ei" with "ie"
        s_test = "I saw Miesler climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Meisler, Fran"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Meisler, Fran"}],
            [],
        )

    def test_name_fuzzy_delete_hyphen(self):
        # deleted "-"
        s_test = "I saw Glennballant climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Glenn-Ballant, Greg"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Glenn-Ballant, Greg"}],
            [],
        )

    def test_name_fuzzy_delete(self):
        # deleted "h"
        s_test = "I saw Smiters climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smithers, Greg"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smithers, Greg"}],
            [],
        )

    def test_name_fuzzy_first_name(self):
        # deleted "i"
        s_test = "I saw Giorgos climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, Giorgios"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, Giorgios"}],
            [],
        )

    def test_name_fuzzy_full_name(self):
        # deleted "i"
        # currently: (S1) (S1)
        # mask_person redacts "Smith", mask_fuzzy_name redacts "Georgios"
        s_test = "I saw Georgios Smith climb over the fence."
        s_correct = "I saw (S1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, Giorgios"}],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [{"indicator": "S", "name": "Smith, Giorgios"}],
            [],
        )

    def test_name_fuzzy_ambiguous_name(self):
        # deleted "i"
        # currently (S1) but should be ambiguous
        s_test = "I saw Valentia climb over the fence."
        s_correct = "I saw (S1 or V1) climb over the fence."
        self.redactor_tester(
            "Prefixton",
            s_test,
            s_correct,
            [
                {"indicator": "S", "name": "Valencia, Henry"},
                {"indicator": "V", "name": "Valencia, Mary"},
            ],
            [],
        )
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {"indicator": "S", "name": "Valencia, Henry"},
                {"indicator": "V", "name": "Valencia, Mary"},
            ],
            [],
        )

    # ==================== NEIGHBORHOOD TESTS ======================

    def test_redact_neighborhood_1(self):
        s_test = "at the motels in Eastlake"
        s_correct = "at the motels in [neighborhood]"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_redact_neighborhood_2(self):
        s_test = "was transported to Parkside Memorial Hospital by Adam"
        # TODO(jnu): we should be redacting even more of the hospital name,
        # since neighborhood is somewhat inferrable based on the destination.
        s_correct = "was transported to [neighborhood] Memorial Hospital by Adam"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_redact_neighborhood_3(self):
        s_test = "advised UC Eastlake Police Department"
        s_correct = "advised [neighborhood] Police Department"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_redact_neighborhood_1(self):
        s_test = "blood test at St. Mary's Hospital"
        s_correct = "blood test St. Mary's Hospital"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_redact_neighborhood_2(self):
        s_test = "was booked at Suffix County Jail"
        s_correct = "was booked at Suffix County Jail"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_no_redact_neighborhood_3(self):
        s_test = "case to Suffix County DA for review"
        s_correct = "case to Suffix County DA for review"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    # ==================== INDICATOR TESTS ======================

    def test_no_indicator(self):
        # test: redaction works without indicator
        s_test = "I saw Alex in the driveway."
        s_correct = "I saw (PERSON_1) in the driveway."
        self.redactor_tester(
            "Suffix County", s_test, s_correct, [{"name": "Chohlas-Wood, Alex"}], []
        )

    def test_custom_label(self):
        # test: custom_label overrides indicator
        s_test = "I saw Alex in the driveway."
        s_correct = "I saw (Artist 42) in the driveway."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {
                    "indicator": "M",
                    "name": "Chohlas-Wood, Alex",
                    "custom_label": "Artist 42",
                }
            ],
            [],
        )

    def test_custom_label_duplicate(self):
        # test: custom_label duplicates allowed
        s_test = "I saw Alex and Keniel in the driveway."
        s_correct = "I saw (Artist 42) and (Artist 42) in the driveway."
        self.redactor_tester(
            "Suffix County",
            s_test,
            s_correct,
            [
                {
                    "indicator": "M",
                    "name": "Chohlas-Wood, Alex",
                    "custom_label": "Artist 42",
                },
                {"indicator": "V", "name": "Yao, Keniel", "custom_label": "Artist 42"},
            ],
            [],
        )

    # ==================== HAIR STYLE TESTS ======================

    def test_hairstyle_sensitive(self):
        # stand-alone sensitive noun
        s_test = "he had an afro"
        s_correct = "he had a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_sensitive_2(self):
        # stand-alone sensitive split nouns
        s_test = "he had dread locks"
        s_correct = "he had [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_adj(self):
        s_test = "he had curly hair"
        s_correct = "he had [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_adj_2(self):
        s_test = "he had a brown crew cut"
        s_correct = "he had a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_spacing(self):
        # previously, would redacted "red" in "colored"
        # added "\b" to _redact_literal_noun_phrase
        s_test = "he had colored dreadlocks"
        s_correct = "he had colored [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_dash(self):
        # fail
        s_test = "he had poofy afro-style hair"
        s_correct = "he had [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_quotes(self):
        # fail
        s_test = "he had a small 'afro' haircut"
        s_correct = "he had a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_adj_sensitive(self):
        s_test = "he had a curly afro"
        s_correct = "he had a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_adj_sensitive_2(self):
        s_test = "he had curly afro hair"
        s_correct = "he had [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_style(self):
        s_test = "he had a dreadlocks hair style"
        s_correct = "he had a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_style_2(self):
        s_test = "with an afro style hair"
        s_correct = "with a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_type(self):
        s_test = "with an afro type hair style"
        s_correct = "with a [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_list_1(self):
        s_test = "Hair: Black"
        s_correct = "Hair: [color]"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_list_2(self):
        s_test = "Hair: Dreadlocks"
        s_correct = "Hair: [hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_alternative_or_1(self):
        s_test = "silver/white short hair"
        s_correct = "[hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_hairstyle_alternative_or_2(self):
        s_test = "light brown/blond curly hair"
        s_correct = "[hairstyle] hair"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_haircolor(self):
        s_test = "She was having a dumb blonde moment."
        s_correct = "She was having a dumb [physical description] moment."
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_haircolor_list(self):
        s_test = "Hair: Blonde"
        s_correct = "Hair: [color]"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    # ==================== PHYSICAL FEATURES TESTS ======================

    def test_eyes_list(self):
        s_test = "Eyes: Brown"
        s_correct = "Eyes: [color]"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_complexion(self):
        s_test = "light complexion"
        s_correct = "[race/ethnicity] complexion"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_complexion_list_1(self):
        s_test = "Complexion: Dark"
        s_correct = "Complexion: [race/ethnicity]"
        self.mask_tester("Suffix County", s_test, s_correct, {})

    def test_complexion_list_2(self):
        s_test = "Complexion: Light or pale"
        s_correct = "Complexion: [race/ethnicity]"
        self.mask_tester("Suffix County", s_test, s_correct, {})
