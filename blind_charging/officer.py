import itertools
import re
from collections import defaultdict
from typing import DefaultDict, List, Optional

from .individual import Individual, MergeDifferentPersonsError
from .locale import Locale
from .source_text import nlp


def _get_name_pattern(
    parts: List[Optional[str]], star: Optional[str] = None
) -> Optional[str]:
    """Get a regular expression that joins a set of parts.

    :param parts: Parts to join with space pattern
    :param star: Optional star part to append to the end
    :returns: Regex, or None if there were no parts to join
    """
    non_null = filter(None, parts)
    if not non_null:
        return None
    pfx = r"\s+".join(non_null)
    if star:
        return pfx + star
    return pfx


class OfficerName(Individual):
    # TODO(itsmrlin): double check name regex to prevent catastrophic backtracking
    # TODO(itsmrlin): automate capitalization variation
    # officer title re
    t_re = (
        r"(Sheriff|Insp\.?|Inspector|Officer|Ofc\.?|"
        r"Off\.?|Sergeant|Sgt\.?|Commissioner|Comm\.?|"
        r"commissioner|comm\.?|FTO|PSA)\s+"
    )
    # 5 digit code re
    dgt5_re = r"(\s|^)?\(?[0-9][A-Z][0-9A-Z]{2,3}\)?(\s|\.|$)"
    # name regex
    n_re = r"[A-Z][A-Za-z\-\']*\s*"
    # star regex
    star_re = r"(?:#\s*)([0-9]{3,5})\b"

    def __init__(self, name):
        ofc_str = name
        self._dict = {"ofc_str": ofc_str}
        self.dgt5_code = None
        self.star = None
        self.title = None
        self.name = []
        self.code_name = None
        self.cls = ""
        self.officer_titles = {
            "OFFICER": "Officer",
            "OFC": "Officer",
            "OFF": "Officer",
            "SERGEANT": "Sergeant",
            "SGT": "Sergeant",
            "INSPECTOR": "Inspector",
            "INSP": "Inspector",
            "SHERIFF": "Sheriff",
            "COMMISSIONER": "Commissioner",
            "COMM": "Commissioner",
            "FTO": "FTO",
            "PSA": "PSA",
        }
        # title to abbr.
        self.t2abbr = {}
        for k in self.officer_titles.keys():
            if self.officer_titles[k] not in self.t2abbr:
                self.t2abbr[self.officer_titles[k]] = [k]
            else:
                self.t2abbr[self.officer_titles[k]].append(k)

        if re.search(OfficerName.star_re, ofc_str):
            star_no = re.search(OfficerName.star_re, ofc_str).group(1)
            self.star = str(star_no)

        parts = ofc_str.split()

        for pp in parts:
            p = pp.upper().strip()
            m = re.match(r"\b[A-Za-z\-\']+\b", p)
            is_officer_title = p.strip(".") in self.officer_titles
            if not is_officer_title and m and not nlp.vocab[p].is_stop:
                p_clean = re.sub(r"[^A-Z]+$", "", p)
                self.name.append(p_clean)
            elif is_officer_title:
                self.title = self.officer_titles[p.strip(".")]
            elif re.match(OfficerName.dgt5_re, p) is not None:
                self.dgt5_code = p.strip("(").strip(")")

        if not self.name:
            self.name = set()
        else:
            self.name = set(self.name)

    def __eq__(self, other):
        # dgt5_code is likely a shift number (including 2 officers) and
        # we do not match officer based on that
        # but we DO know if they are different then officers are different
        if self.dgt5_code != other.dgt5_code:
            return False

        if self.star is not None and self.star == other.star:
            return True

        for n1 in self.name:
            for n2 in other.name:
                if n1 == n2:
                    return True

        return False

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return str(
            {
                "code_name": self.code_name,
                "dgt5_code": self.dgt5_code,
                "star": self.star,
                "title": self.title,
                "name": self.name,
            }
        )

    def __repr__(self):
        return self.__str__()

    def get_indicator(self):
        if self.code_name is None:
            return "CODE NAME NOT ASSIGNED!"

        return self.code_name

    def to_dict(self):
        return self._dict.copy()

    def merge(self, other):
        if self != other:
            raise MergeDifferentPersonsError

        if self.dgt5_code is None:
            self.dgt5_code = other.dgt5_code

        if self.star is None:
            self.star = other.star

        if self.title is None:
            self.title = other.title

        self.name = self.name.union(other.name)

    def _name_rep_impl(self):
        reps = set()
        combined_names = [
            r"\s+".join(x)
            for i in range(1, 3)
            for x in itertools.permutations(self.name, i)
        ]

        dgt5_code = None if self.dgt5_code is None else r"\(?%s\)?" % self.dgt5_code
        # 1A23B
        reps.add(dgt5_code)

        if self.star:
            star_no = self.star
            star_regex = r"\s*#\s*" + star_no
            reps.add(star_regex)
        else:
            star_regex = None

        for n in combined_names:
            # John Doe
            reps.add(_get_name_pattern([n]))
            # John Doe #1234
            reps.add(_get_name_pattern([n], star_regex))
            if dgt5_code:
                # 1A23B John Doe #1234
                reps.add(_get_name_pattern([dgt5_code, n], star_regex))

        if self.title is not None:
            for t in self.t2abbr[self.title]:
                if self.star is not None:
                    # Officer #1234
                    reps.add(_get_name_pattern([t + r"\.?"], star_regex))
                    if dgt5_code:
                        # 1A23B Officer #1234
                        reps.add(_get_name_pattern([dgt5_code, t + r"\.?"], star_regex))

            for n in combined_names:

                for t in self.t2abbr[self.title]:
                    # officer john doe
                    reps.add(_get_name_pattern([t + r"\.?", n]))
                    # officer john doe #1234
                    reps.add(_get_name_pattern([t + r"\.?", n], star_regex))
                    if dgt5_code:
                        # 1a23b officer john doe #1234
                        reps.add(
                            _get_name_pattern([dgt5_code, t + r"\.?", n], star_regex)
                        )

        if None in reps:
            reps.remove(None)

        reps = {r"\b%s\b" % x for x in reps}

        # TODO(jnu): the longest pattern is not necessarily going to yield the
        # longest match. It's an ok heuristic for now, but really we should
        # match all the patterns and resolve ovleraps by choosing the longest
        # match.
        reps = sorted(reps, key=lambda x: len(x), reverse=True)
        return reps

    @classmethod
    def dedupe(
        cls, officers: List["OfficerName"], locale: Locale
    ) -> List["OfficerName"]:
        """Merge duplicated officer references.

        :param officers: List of officers
        :param locale: Location information
        :returns: De-duplicated list of officers
        """
        persons = super(OfficerName, cls).dedupe(officers, locale)

        type_counts: DefaultDict[str, int] = defaultdict(int)
        for p in persons:
            if p.star is not None and p.title is None:
                title = "Officer"
            else:
                title = p.title

            if not title:
                # if no title and no star, but has the 5 digit code
                # it's probably a team/partnership
                if p.dgt5_code is not None:
                    p.code_name = "[officer pair]"
                else:
                    p.code_name = "an officer"
            else:
                type_counts[title] += 1
                p.code_name = "%s #%d" % (title, type_counts[title])
            # TODO(jnu): clean up how the class is applied
            p.cls = "masked-officer"

        return persons
