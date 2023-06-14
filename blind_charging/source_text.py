"""Text container with utilities for applying redactions."""
import os
import re
from typing import List, Optional, Tuple

import spacy
from spacy.tokens import Doc, Span, Token

from .annotation import Redaction
from .broken_range import BrokenRange
from .thunk import Thunk

# The model can be swapped out at runtime by providing a path to a package.
# NOTE(jnu): lazy-load NLP model so app CLI methods can work regardless of
# environment config.
nlp = Thunk(lambda: spacy.load(os.getenv("BC_NLP_MODEL", "en_core_web_lg")))


# Punctuation tokens that can end sentences.
_TERMINALS = {".", "!", "?", '"'}


class OverlapError(Exception):
    """Error raised when trying to overwrite an existing redaction."""


def _last_non_space(span: Span) -> Optional[Token]:
    """Find the last non-space token in a span.

    :param sent: Input span
    :returns: Non-space token if found, otherwise None
    """
    for t in list(span)[::-1]:
        if t.pos_ != "SPACE":
            return t
    return None


def _capitalize(text: str) -> str:
    """Capitalize some text that might contain non-alphabetic characters.

    E.g., "[placeholder]" -> "[Placeholder]"

    :param text: Text to capitalize
    :returns: Capitalized text
    """
    for i, c in enumerate(text):
        if c.isalpha():
            return text[:i] + c.upper() + text[i + 1 :]
    return text


def _is_sent_start(doc: Doc, index: int) -> bool:
    """Test whether the given index is in the first token in a sentence.

    :param doc: Spacy Doc
    :param start: Index to check
    :returns: True if index is within first word of a sentence
    """
    seen_space = False
    # Limit search space to previous few tokens
    end_ptr = max(0, index - 3)
    while index >= end_ptr:
        char = doc.text[index]
        span = doc.char_span(index, index + 1)
        if span:
            tok = doc[span.start]
            if tok.pos_ == "PUNCT" and char in _TERMINALS:
                # Found punctuation: check if it's the last token in a
                # sentence. If it is, the initial word was the start of its
                # own sentence.
                return _last_non_space(tok.sent) == tok
        if re.match(r"\s", char):
            # Found a space
            seen_space = True
        elif seen_space:
            # Found another word: can't be beginning of the sentence.
            return False
        index -= 1

    # Found the beginning of the string: must be start of sentence.
    return index == 0


def _clamp_to_word_boundary(doc: Doc, index: int, up: bool = True) -> int:
    """Move index to nearest word boundary if it points to a space.

    :param doc: Spacy Document
    :param index: Start index
    :param up: Direction of clamp (default up; pass False to move index down)
    :returns: Clamped index
    """
    delta = 1 if up else -1
    txt = doc.text
    while index > 0 and index < len(txt) - 1 and re.match(r"\s", txt[index]):
        index += delta
    return index


def _get_indefinite_article_for_text(text: str) -> str:
    """Get the indefinite article to use for the given text.

    Uses heuristics based on word-initial orthography. Not completely accurate.

    :param text: Input text
    :returns: "a" or "an"
    """
    needs_epenthesis = False
    for _, c in enumerate(text):
        if c.isalpha():
            # TODO(jnu): the rules are more complicated, but use simple vowel
            # orthography to catch most cases.
            # (Words like "one" fail to follow this rule.)
            needs_epenthesis = c.lower() in {"a", "e", "i", "o", "u"}
            break
        elif c.isdigit():
            # TODO(jnu): Again, not a perfect rule, but good enough to start.
            # Catches things like "An 8-digit number"
            needs_epenthesis = c == "8"
            break
    return "an" if needs_epenthesis else "a"


def _correct_indef_article(doc: Doc, text: str, index: int) -> Tuple[str, int]:
    """Expand redaction to encompass the indefinite article, if necessary.

    E.g., "an African-American male" -> "a [race/ethnicity] male"

    If the preceding word is an indefinite article, we include it in the
    redacted text, replaced with the correct definite article for the
    substituted text. Do this because the epenthetic 'n' of the article could
    give away information about the underlying text, and also to make the
    text read more smoothly.

    :param doc: Spacy Document
    :param text: Text to substitute as redaction
    :param index: Index where text will be inserted
    :returns: Tuple containing correct redaction text and annotation start
    index (which redacts the article as well).
    """
    correct_article = _get_indefinite_article_for_text(text)
    scanned_words: List[str] = []
    word_terminal_index: List[int] = []
    space_str = ""
    scanning_word = False

    ptr = index
    # At max we only need to search 4 tokens previous to this one.
    end_ptr = max(0, ptr - 4)

    while ptr >= end_ptr:
        char = doc.text[ptr]
        # NOTE: Only match simple spaces. Newlines and tabs will probably
        # result in overmatching.
        if char == " ":
            # Break if we found two words. Note the loop will automatically
            # break when we reach the 0 index.
            if len(scanned_words) == 2:
                break
            space_str = char + space_str
            scanning_word = False
        else:
            if not scanning_word:
                scanning_word = True
                scanned_words.append("")
                word_terminal_index.append(ptr + 1)
            scanned_words[-1] = char + scanned_words[-1]
        ptr -= 1

    # If the preceding word was not the indefinite article, return
    if len(scanned_words) < 2 or scanned_words[-1].lower() not in {"a", "an"}:
        return text, index

    # Match case when substituting article
    existing_article = scanned_words[-1]
    if existing_article.isupper():
        correct_article = correct_article.upper()
    elif existing_article[0].isupper():
        correct_article = correct_article.capitalize()

    new_text = correct_article + space_str + text
    new_idx = word_terminal_index[-1] - len(scanned_words[-1])
    return new_text, new_idx


class SourceText(object):
    """A stateful container for text undergoing redaction.

    This container supplies a stateful representation of the text while
    redaction is in progress, so that redactions can be applied in priority
    order without later rules re-matching text that has already been redacted.

    The container also provides NLP entities based on the original source text
    which are always available to rules, regardless of order.
    """

    def __init__(self, text: str):
        self.text = text
        self.nlp = nlp(text)
        self.cleared = BrokenRange()

    def clear_span(self, start: int, end: int, placeholder="*"):
        """Clear a span in the source text while preserving the text length.

        :param start: Start of extent to clear
        :param end: End of extent to clear
        :param placeholder: Placeholder character to use in span
        """
        extent = end - start
        # Generate a new replacement span, but ensure that the length is
        # correct. This deals with the case that the input placeholder was
        # longer than one character.
        new_span = (placeholder * extent)[:extent]
        self.text = self.text[:start] + new_span + self.text[end:]
        # Track the spans that have been redacted
        self.cleared.addspan(start, end)

    def can_redact(self, start: int, end: int) -> bool:
        """Ensure that no part of the given span is already redacted.

        :param start: Start position of the span
        :param end: End position of the span (inclusive)
        :returns: Boolean indicating whether span is eligible for redaction
        """
        return not self.cleared.overlaps(start, end)

    def redact(
        self,
        start: int,
        end: int,
        text: str,
        clamp: bool = True,
        auto_capitalize: bool = True,
        autocorrect_article: bool = True,
        force: bool = False,
        **kwargs: str
    ) -> Redaction:
        """Redact a span of text with the given replacement.

        :param start: Start of span (position of first character in span)
        :param end: End of span (position last character in span)
        :param text: Replacement text
        :param clamp: Ensure the redaction fits neatly at word boundaries
        :param auto_capitalize: Infer and apply capitalization from underlying
        text span.
        :param autocorrect_article: Automatically modify redaction to account
        for any preceding indefinite article (i.e., "a" vs. "an")
        :param force: Don't throw an error if the span overlaps with a span
        that has already been redacted.
        :param **kwargs: Passed to Redaction constructor
        :returns: Redaction
        :raises OverlapError: If the suggested span would overlap with another
        existing redaction.
        """
        if not force and not self.can_redact(start, end):
            raise OverlapError("Invalid span: {} - {}".format(start, end))

        if clamp:
            start = _clamp_to_word_boundary(self.nlp, start, up=True)
            # Correct for off-by-1 errors, since `end` technically points to
            # the character immediately following the redaction.
            end = _clamp_to_word_boundary(self.nlp, end - 1, up=False) + 1

        if autocorrect_article:
            text, start = _correct_indef_article(self.nlp, text, start)

        if auto_capitalize and _is_sent_start(self.nlp, start):
            text = _capitalize(text)

        self.clear_span(start, end)
        return Redaction(start, end, text, **kwargs)
