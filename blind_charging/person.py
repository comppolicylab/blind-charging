import re
from collections import defaultdict
from typing import DefaultDict, List, Set

from similarity.damerau import Damerau
from similarity.jarowinkler import JaroWinkler

from .individual import Individual, MergeDifferentPersonsError
from .locale import Locale
from .mask_const import WEB_COLORS
from .source_text import nlp

# for distance measure to measure name
damerau = Damerau()
jarowinkler = JaroWinkler()


def _name_match(s1: Set[str], s2: Set[str], max_dist: int = 0) -> bool:
    """
    detect if two sets share the same name
    max_dist is the max edit distance
    if max_dist in (0, 1), use normalized edit dist

    param s1: set of names
    param s2: another set of names
    returns: True if s1 and s2 share a common name
    """
    # TODO (acw): Try Jaro-Winkler here instead of levenshtein, which
    # seems too rigid
    if max_dist == 0:
        return bool(s1 & s2)
    else:
        for a in s1:
            for b in s2:
                dist = (
                    damerau.distance(a, b)
                    if max_dist >= 1
                    else jarowinkler.distance(a, b)
                )
                if dist <= max_dist:
                    return True
        return False


def add_compound_name_parts(name_set=Set[str]) -> Set[str]:
    # for each name in set
    # if hyphenated (space), add the following to set
    # - word before hyphen (space)
    # - word after hyphen (space)
    # - words concatenated together without hyphen (space)
    # - words concatenated together with space instead of hyphen (hyphen instead of space)
    hyphen_pattern = re.compile(r"\w+-\w+")
    space_pattern = re.compile(r"\w+\s\w+")
    new_name_set = name_set.copy()
    for name_part in name_set:
        if hyphen_pattern.match(name_part):
            new_name_set.update(name_part.split("-"))
            new_name_set.add(name_part.replace("-", ""))
            new_name_set.add(name_part.replace("-", " "))
        if space_pattern.match(name_part):
            new_name_set.update(name_part.split())
            new_name_set.add(re.sub(r"\s", "", name_part))
            new_name_set.add(re.sub(r"\s", "-", name_part))

    return new_name_set


class PersonName(Individual):
    def __init__(
        self,
        indicator=None,
        report_id=None,
        name=None,
        f_name=None,
        m_name=None,
        l_name=None,
        alias=None,
        sfno=None,
        court_no=None,
        custom_label=None,
    ):
        # Store input arguments for serialization
        self._dict = {
            "indicator": indicator,
            "report_id": report_id,
            "name": name,
            "f_name": f_name,
            "m_name": m_name,
            "l_name": l_name,
            "alias": alias,
            "sfno": sfno,
            "court_no": court_no,
            "custom_label": custom_label,
        }

        # Parse args
        ptype = None if indicator is None else re.sub("[^A-Z]+", "", indicator)
        if ptype == "":
            ptype = None
        pnum = None if indicator is None else re.sub("[^0-9]+", "", indicator)
        if pnum == "":
            pnum = None
        if ptype and pnum:
            self.indicator = ptype + pnum
        else:
            self.indicator = None
        self.custom_label = custom_label
        self.id_triplet = {(report_id, ptype, pnum)}
        self.sfno = sfno
        self.court_no = court_no
        self.code_name = None  # to be filled later during dedup
        self.cls = ""
        self.color = ""
        # make names sets in case there are multiple versions
        # (e.g., Mike vs. M.)
        self.full_code_name = None  # see above
        self.first = set()
        self.middle = set()
        self.last = set()
        self.alias = set()
        self._name = name
        if alias is not None:
            self.alias.add(alias.upper())
        if name is not None:
            self.parse_name(name)
            self.last = add_compound_name_parts(self.last)
        elif not (f_name is None and m_name is None and l_name is None):
            self.parse_full_name(f_name=f_name, m_name=m_name, l_name=l_name)
        else:
            pass

        # Cache flag indicating if this person is unknown
        self._is_unknown = "UNKNOWN" in {
            str(f_name).upper(),
            str(m_name).upper(),
            str(l_name).upper(),
        }

    def to_dict(self):
        """Return dictionary of input arguments.

        The following is true:
        ```
        pn1 = PersonName(...)
        d = pn.to_dict()
        pn2 == PersonName(**d)
        ```
        """
        return self._dict.copy()

    def __str__(self):
        return str(
            {
                "code_name": self.code_name,
                "id_triplet": self.id_triplet,
                "first": self.first,
                "middle": self.middle,
                "last": self.last,
            }
        )

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(str(self.id_triplet))

    def __eq__(self, other):
        # if we have two non-None equal person number or court number.
        # then it has to be the same person
        if self.court_no is not None and other.court_no is not None:
            if self.court_no == other.court_no:
                return True
            else:
                return False

        if self.sfno is not None and other.sfno is not None:
            if self.sfno == other.sfno:
                return True
            else:
                return False

        # otherwise match names
        if _name_match(self.last, other.last, 1):
            # after they match last name,
            # if they both have same first name, then match
            if len(self.first) > 0 and len(other.first) > 0:
                if _name_match(self.first, other.first, 1):
                    return True
            else:
                # if no first name, last name only match is a match
                return True

        # Match alias
        if self.alias & other.alias:
            return True

        # Match name to alias
        for name in other.last.union(other.first):
            # We do not compare initials
            if len(name.strip(".")) > 1:
                if name in self.alias:
                    return True
        for name in self.last.union(self.first):
            # We do not compare initials
            if len(name.strip(".")) > 1:
                if name in other.alias:
                    return True

        # Match indicators if no names
        if (not self.last and not self.first) or (not other.last and not other.first):
            if self.id_triplet == other.id_triplet:
                return True

        return False

    def is_chargeable(self):
        if self.sfno is not None:
            return True
        for _report_id, ptype, _pnum in self.id_triplet:
            if ptype in {"B", "C", "D", "S"}:
                return True
        return False

    def is_unknown(self) -> bool:
        """Check whether person is unknown."""
        return self._is_unknown

    def get_indicator(self):
        if self.code_name is None:
            raise Exception("Code name not assigned")
        return self.code_name

    def parse_full_name(self, f_name, m_name, l_name):
        f_name = None if not f_name else f_name.strip().strip(".").upper()
        m_name = None if not m_name else m_name.strip().strip(".").upper()
        l_name = None if not l_name else l_name.strip().strip(".").upper()

        if f_name:
            self.first.add(f_name.upper())
            for p in f_name.upper().split():
                self.first.add(p)

        if m_name:
            self.middle.add(m_name.upper())

        if l_name:
            self.last.add(l_name.upper())
            for p in l_name.upper().split():
                self.last.add(p)

    def parse_name(self, name):
        parts = [p.strip().strip(".").upper() for p in name.split()]
        parts = [
            p for p in parts if not nlp.vocab[p].is_stop and not re.match(r"^\W$", p)
        ]
        if len(parts) == 1:
            # Last name
            self.last.add(parts[0])
        elif len(parts) == 2:
            if parts[0][-1] == ",":
                # last, first
                self.last.add(parts[0].strip(","))
                self.first.add(parts[1])
            else:
                # first last or last f
                # assume no first l. scenario
                if (len(parts[1]) == 1) or (len(parts[1]) == 2 and parts[1][1] == "."):
                    # last f. or last f
                    self.last.add(parts[0])
                    self.first.add(parts[1])
                else:
                    # first last
                    self.first.add(parts[0])
                    self.last.add(parts[1])
        elif len(parts) == 3:
            if parts[0][-1] == ",":
                # last, first m(iddle)
                self.last.add(parts[0].strip(","))
                self.first.add(parts[1])
                self.middle.add(parts[2])  # middle
            elif parts[1][-1] == ",":
                # last last, first
                self.last.add(parts[0] + " " + parts[1].strip(","))
                self.first.add(parts[2])
            else:
                # first middle last
                self.first.add(parts[0])
                self.middle.add(parts[1])  # middle
                self.last.add(parts[2])
        else:
            # anything of length 4 or longer is likely an erroneous parse
            # treating it like a last name
            formatter_name = name.strip().strip(".").upper()
            if "," in formatter_name:
                parts = formatter_name.split(",")
                last = parts[0].strip()
                f = parts[1].strip()
            else:
                f = None
                last = formatter_name
            self.last.add(last)
            for part in last.split():
                self.last.add(part)
            if f:
                self.first.add(f)
                for part in f.split():
                    self.first.add(part)

        # remove any names of length 0 from sets
        self.first.discard("")
        self.middle.discard("")
        self.last.discard("")

    def _name_rep_impl(self) -> List[str]:
        reps = set()

        last_literals = [re.escape(last) for last in self.last]
        first_literals = [re.escape(f) for f in self.first]
        middle_literals = [re.escape(m) for m in self.middle]

        for last in last_literals:
            reps.add(last)

        for f in first_literals:
            reps.add(f)

        for last in last_literals:
            for f in first_literals:
                reps.add(f + r"\s+" + last)  # first last
                reps.add(f[0] + r"\s+" + last)  # f. last
                reps.add(f[0] + r"\." + last)  # f.last
                reps.add(f[0] + r"\.\s+" + last)  # f last
                reps.add(last + r"\s*,\s+" + f)  # last, first
                reps.add(last + r"\s+" + f[0])  # last f
                reps.add(last + r"\s+" + f[0] + r"\.")  # last f.
                reps.add(last + r"\s*,\s+" + f[0])  # last, f
                reps.add(last + r"\s*,\s+" + f[0] + r"\.")  # last, f.
                reps.add(
                    last + r"\s+" + f
                )  # last first - for if name input is accidentally reversed

        for f in first_literals:
            for m in middle_literals:
                for last in last_literals:
                    reps.add(f + r"\s+" + m + r"\s+" + last)  # first middle last
                    reps.add(f + r"\s+" + m[0] + r"\s+" + last)  # first m last
                    reps.add(f + r"\s+" + m[0] + r"\.\s+" + last)  # first m. last
                    reps.add(last + r"\s*,\s+" + f + r"\s+" + m)  # last, first middle
                    reps.add(last + r"\s*,\s+" + f + r"\s+" + m[0])  # last, first m
                    reps.add(
                        last + r"\s*,\s+" + f + r"\s+" + m[0] + r"\."
                    )  # last, first m.
                    reps.add(m + r"\s+" + last)  # middle last

        reps = {r"%s\b" % x for x in reps}
        indicators = set[str]()
        indicator_reps = set[str]()
        if self.indicator:
            indicator_esc = re.escape(self.indicator)
            naked_ind = r"\W%s" % indicator_esc  # RW1
            paren_ind = r"\(%s\)" % indicator_esc  # (RW1)
            slash_base = re.sub(r"([A-Z|a-z])", r"\1/", indicator_esc)
            slash_ind = r"\W%s" % slash_base  # R/W/1
            paren_slash_ind = r"\(%s\)" % slash_base  # (R/W/1)
            middle_slash_base = re.sub(
                r"([A-Z|a-z])(?=[A-Z|a-z])", r"\1/", indicator_esc
            )
            middle_slash_ind = r"\W%s" % middle_slash_base  # R/W1
            paren_middle_slash_ind = r"\(%s\)" % middle_slash_base  # (R/W1)
            indicators = indicators.union(
                {
                    naked_ind,
                    paren_ind,
                    slash_ind,
                    paren_slash_ind,
                    middle_slash_ind,
                    paren_middle_slash_ind,
                }
            )

            for indicator in indicators:
                for rep in reps:
                    indicator_reps.add(r"%s\s*%s" % (indicator, rep))
                    indicator_reps.add(r"%s\s*%s" % (rep, indicator))

        reps = {r"\b%s" % x for x in reps}
        reps = reps.union(indicators).union(indicator_reps)

        # the longest representation first for replacement purpose
        return sorted(reps, key=lambda x: len(x), reverse=True)

    def merge(self, other):
        if self != other:
            raise MergeDifferentPersonsError()

        if self.sfno is None:
            self.sfno = other.sfno
        self.id_triplet = self.id_triplet.union(other.id_triplet)
        self.first = self.first.union(other.first)
        self.middle = self.middle.union(other.middle)
        self.last = self.last.union(other.last)
        self.alias = self.alias.union(other.alias)

    @classmethod
    def dedupe(cls, persons: List["PersonName"], locale: Locale) -> List["PersonName"]:
        """De-duplicate PersonName list.

        :param persons: List of persons
        :param locale: Current location information
        :returns: De-duplicated list
        """
        persons = super(PersonName, cls).dedupe(persons, locale)

        REF_NAMES = locale.indicators

        type_counts: DefaultDict[str, int] = defaultdict(int)
        count = 0
        for p in persons:
            # TODO(jnu): derive these values in a cleaner way
            p.cls = "masked-suspect" if p.is_chargeable() else "masked-person"
            p.color = WEB_COLORS[count % len(WEB_COLORS)]
            count += 1

            # redact with custom label if present
            if p.custom_label:
                p.code_name = p.custom_label
                p.full_code_name = p.custom_label
                continue

            code_name_parts = []
            full_name_parts = []
            ptype_set = {ptype for report_id, ptype, pnum in p.id_triplet}
            for ptype in ptype_set:
                if ptype is not None:
                    cname = REF_NAMES[ptype]
                    type_counts[cname] += 1
                    code_name_parts.append(ptype + str(type_counts[cname]))
                    full_name_parts.append(cname + " " + str(type_counts[cname]))
            # if no code name found for current person type, use person
            if not code_name_parts:
                # Use default value from defaultdict,
                # which is supposed to be person
                cname = REF_NAMES[""]
                type_counts[cname] += 1
                code_name_parts.append("PERSON_" + str(type_counts[cname]))
                full_name_parts.append(cname + " " + str(type_counts[cname]))

            # NOTE(jnu): deterministic order for code name
            p.code_name = "(%s)" % " / ".join(sorted(code_name_parts))
            p.full_code_name = " / ".join(sorted(full_name_parts))

        return persons
