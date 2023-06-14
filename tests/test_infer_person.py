import unittest
from typing import List, Set

from blind_charging.locale import Locale
from blind_charging.person import PersonName
from blind_charging.text_processing import get_persons_from_narrative, preprocess


def _get_persons(txt: str, person_types: Set[str]) -> List[PersonName]:
    """Convenience wrapper for calling get persons function.

    :param txt: Narrative text to process
    :param person_types: Known person types
    :returns: List of inferred persons
    """
    processed = preprocess(txt)
    raw = get_persons_from_narrative(processed, 123, person_types)
    # XXX: Shouldn't have to dedupe to run these tests :(
    return PersonName.dedupe(raw, Locale.get("Prefixton"))


class TestPersonInference(unittest.TestCase):
    def test_no_person(self):
        assert _get_persons("foo", {}) == []

    def test_rv_person(self):
        p = _get_persons(
            """\
Blah blah blah this narrative references one person (RV1) Jane Smith and nobody else.""",
            {"RV"},
        )
        assert len(p) == 1
        assert p[0]._name == "Jane Smith"
        assert p[0].id_triplet == {(123, "RV", "1")}

    def test_v_to_rv_person(self):
        p = _get_persons(
            """\
Blah blah blah this narrative references one person (RV1) Jane Smith and nobody else.""",
            {"V"},
        )
        assert len(p) == 1
        assert p[0]._name == "Jane Smith"
        assert p[0].id_triplet == {(123, "RV", "1")}

    def test_name_not_adjacent(self):
        p = _get_persons(
            """\
Blah blah this narrative has an indicator (RV1), but Jane Smith is not \
the same since she's not adjacent.""",
            {"RV"},
        )
        assert len(p) == 1
        assert p[0]._name is None
        assert p[0].id_triplet == {(123, "RV", "1")}

    def test_name_punct_sep(self):
        p = _get_persons(
            """\
An indicator is here (RV1). Jane Smith is not that person.""",
            {"RV"},
        )
        assert len(p) == 1
        assert p[0]._name is None
        assert p[0].id_triplet == {(123, "RV", "1")}

    def test_name_multi(self):
        p = _get_persons(
            """\
This narrative references Jane Doe, but she is not the person we should return.

The person (RV2) Janet Howes is the right person. (Also Ben Jackson is wrong.)
""",
            {"RV"},
        )
        assert len(p) == 1
        assert p[0]._name == "Janet Howes"
        assert p[0].id_triplet == {(123, "RV", "2")}

    def test_variant(self):
        p = _get_persons(
            "I located (V1) Brian Wilson standing in front of the bank.", {"V"}
        )
        assert len(p) == 1
        assert p[0]._name == "Brian Wilson"
        assert p[0].id_triplet == {(123, "V", "1")}
