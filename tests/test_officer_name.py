import unittest

from blind_charging.officer import OfficerName


class TestOfficerName(unittest.TestCase):
    def test_segmentation(self):
        o = OfficerName("Officer Krupke# 1234")
        assert o.name == {"KRUPKE"}
        assert o.star == "1234"
