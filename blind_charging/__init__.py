"""This file defines the public blind_charging interface."""
from typing import Iterable, List, Union

from .annotation import Redaction
from .config import get_locale, set_locale
from .individual import Individual
from .masker import annotate as _annotate
from .source_text import nlp

__all__ = [
    "preload",
    "set_locale",
    "get_locale",
    "annotate",
    "apply_annotations",
    "redact",
]


def preload():
    """Load language model into memory.

    This is useful for long-running services to load the NLP model during the
    start-up process. Otherwise the model (which can be quite large and take
    some time to load into memory) will be loaded lazily during the first
    request, which will cause that request to hang and possibly time out.
    """
    object.__getattribute__(nlp, "_factory")()


AnyKindOfIndividual = Union[str, dict, Individual]
"""Any type that might describe an `Individual`."""


def _norm_individual(x: AnyKindOfIndividual) -> dict:
    """Normalize an `Individual` to a dict."""
    if isinstance(x, str):
        return {"name": x}
    elif isinstance(x, Individual):
        return x.to_dict()
    elif isinstance(x, dict):
        return x
    else:
        raise TypeError(f"unexpected type {type(x)}")


def annotate(
    narrative: str,
    persons: Iterable[AnyKindOfIndividual],
    officers: Iterable[AnyKindOfIndividual],
    redact_officers_from_text: bool = True,
    literals: dict[str, list[str]] | None = None,
) -> List[Redaction]:
    """Generate redaction annotations for the input narrative.

    :param narrative: Incident report text
    :param persons: List of people appearing in the text
    :param officers: List of officers appearing in the text
    :param redact_officers_from_text: Whether to mask officer names (default is `True`)
    :param literals: Custom literals to use for redaction (default is `None`)
    :returns: list of annotations
    """
    # Normalize persons lists.
    # The list can either be a list of strings (the name of the person), or it
    # can be an enriched dictionary with more information. See `person.py` for
    # more information about what that dict can look like. Accept that someone
    # might want to pass `Individual` instances directly, though this is not
    # the norm.
    norm_persons = [_norm_individual(p) for p in persons]
    norm_officers = [_norm_individual(o) for o in officers]

    return _annotate(
        get_locale(),
        narrative,
        norm_persons,
        norm_officers,
        redact_officers_from_text=redact_officers_from_text,
        literals=literals,
    )


def apply_annotations(
    narrative: str,
    annotations: Iterable[Redaction],
) -> str:
    """Apply annotations to a narrative.

    :param narrative: Incident report text
    :param annotations: List of annotations
    :returns: redacted narrative
    """
    # Replace the original text with redaction
    redacted = narrative
    for r in sorted(annotations, key=lambda x: x.start, reverse=True):
        redacted = redacted[: r.start] + "<" + r.text + ">" + redacted[r.end :]

    return redacted


def redact(
    narrative: str,
    persons: Iterable[AnyKindOfIndividual],
    officers: Iterable[AnyKindOfIndividual],
    redact_officers_from_text: bool = True,
    literals: dict[str, list[str]] | None = None,
) -> str:
    """Run redaction algorithm.

    :param narrative: Incident report text
    :param persons: List of people appearing in the text
    :param officers: List of officers appearing in the text
    :param redact_officers_from_text: Whether to mask officer names (default is True)
    :param literals: Custom literals to use for redaction
    :returns: redacted narrative
    """
    annotations = annotate(
        narrative,
        persons,
        officers,
        redact_officers_from_text=redact_officers_from_text,
        literals=literals,
    )

    return apply_annotations(narrative, annotations)
