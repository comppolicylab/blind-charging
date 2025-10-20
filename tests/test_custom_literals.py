import blind_charging as bc
from blind_charging.annotation import Redaction


def test_custom_literals():
    """Test support for extending redaction with custom literals."""
    bc.set_locale("Suffix County")
    assert bc.annotate(
        "Suspect was last seen at Oracle Arena.",
        [],
        [],
        literals={
            "stadium": [
                "Oracle Park",
                "Oracle Arena",
                "Oakland Coliseum",
                "Chase Center",
            ],
        },
    ) == [Redaction(25, 37, "[stadium]", "stadium")]
