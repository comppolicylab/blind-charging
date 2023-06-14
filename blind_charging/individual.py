import abc
from typing import Iterable, List, Optional, Type, TypeVar

from .locale import Locale

T = TypeVar("T", bound="Individual")


# Regular expression patterns that don't have any real meaning in terms of
# name matching.
EMPTY_PATTERNS = {
    r"",
    r"\b-\b",
    r"\b-",
    r"-\b",
    r"-",
    r"\s+",
    r"\s*",
}


class MergeDifferentPersonsError(Exception):
    """Error raised when merge two persons/officers who are different"""


class Individual(abc.ABC):
    @classmethod
    def clean_patterns(cls, patterns: Iterable[str]) -> List[str]:
        """Ensure that patterns are all meaningful for name matching.

        :param patterns: List of patterns to check
        :returns: List with bad patterns filtered out.
        """
        return [p for p in patterns if p not in EMPTY_PATTERNS]

    @abc.abstractmethod
    def merge(self: T, other: T):
        """Merge two individual instances.

        :param other: Other individual to merge into this one
        """

    @abc.abstractmethod
    def to_dict(self: T):
        """Serialize the instance to a dict.

        :returns: kwargs that can be used to instantiate a new instance that is
        equal to the current one.
        """

    @classmethod
    @abc.abstractmethod
    def dedupe(cls: Type[T], individuals: List[T], locale: Locale) -> List[T]:
        """De-duplicate a list of individuals."""
        persons: List[T] = []
        mentions: List[Optional[T]] = list(individuals)
        i = 0
        while i < len(mentions):
            person_a = mentions[i]
            if person_a is not None:
                changed = False
                for j in range(i + 1, len(mentions)):
                    person_b = mentions[j]
                    if person_b is not None:
                        if person_a == person_b:
                            person_a.merge(person_b)
                            mentions[j] = None
                            changed = True
                if not changed:
                    if not person_a:
                        raise ValueError("Trying to add missing person to list")
                    persons.append(person_a)
                    i += 1
            else:
                i += 1
        return persons

    def name_rep(self):
        """Get the individual's name patterns.

        :returns: List of patterns for this individual
        """
        patterns = self._name_rep_impl()
        return self.clean_patterns(patterns)

    @abc.abstractmethod
    def _name_rep_impl(self: T) -> List[str]:
        """Create a list of patterns to match this name.

        :returns: List of patterns for this individual
        """
