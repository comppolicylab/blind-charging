import unittest

from blind_charging.locale import Locale
from blind_charging.person import PersonName


class TestPersonName(unittest.TestCase):
    def test_dedupe(self):
        persons = [
            PersonName(indicator="V", report_id=123, name="Jane Doe"),
            PersonName(indicator="RV", report_id=123, name="Jane Doe"),
        ]
        deduped = PersonName.dedupe(persons, Locale.get("Sample County"))
        assert len(deduped) == 1
        # NOTE(jnu): order of parts is alphabetic
        assert deduped[0].code_name == "(RV1 / V1)"

    def test_clean_patterns(self):
        p = PersonName(
            indicator="R1",
            report_id=123,
            f_name="SCPD - #622, #178",
            m_name="#1660, #928, #1476",
            l_name="SCPD - #622, #178",
        )
        assert r"\b-\b" not in p.name_rep()
