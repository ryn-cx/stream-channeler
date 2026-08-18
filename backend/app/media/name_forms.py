# TODO: Validate
"""The spellings one name can be written in, so two of them can be compared.

A name is written differently on every website that carries it: the case and the
punctuation go their own way, and a title from Japan is written in kana on one
site, in kanji on the next and romanised on a third. None of those are a
different name, so a name is reduced to the set of spellings it could be written
in and two names are the same where any spelling is shared.

The romanisation is a reading rather than a fact. A kanji has more than one and
nothing in a title says which was meant, so every reading the dictionary gives is
kept and the name matches under any of them.
"""

import re
import unicodedata
from functools import cache
from itertools import product
from math import prod

from pykakasi import kakasi
from pykakasi.kanji import Kanwa

# A name whose kanji each have several readings runs to more spellings than are
# worth holding, so past this many only the one reading kakasi settled on is
# kept.
_MAX_READING_COMBINATIONS = 32

_JAPANESE = re.compile(
    "[×々-〆぀-ヿㇰ-ㇿ㐀-䶿"
    "一-鿿豈-﫿！-ﾟ𠀀-𮯯]",
)


# TODO: Validate
@cache
def _converter() -> kakasi:
    return kakasi()


# TODO: Validate
@cache
def _kanwa() -> Kanwa:
    return Kanwa()


# TODO: Validate
def plaintext(name: str | None) -> str:
    """Return `name` with its case, punctuation and spacing taken out."""
    if not name:
        return ""
    return "".join(character for character in name.casefold() if character.isalnum())


# TODO: Validate
def _hepburn(text: str) -> str:
    return "".join(part["hepburn"] for part in _converter().convert(text))


# TODO: Validate
def _readings(segment: str) -> frozenset[str]:
    if not segment:
        return frozenset()
    table = _kanwa().load(segment[0]) or {}
    return frozenset(reading for reading, _context in table.get(segment, []))


# TODO: Validate
@cache
def _romanizations(name: str) -> frozenset[str]:
    if not _JAPANESE.search(name):
        return frozenset()

    readings_per_segment = [
        frozenset({part["hira"], *_readings(part["orig"])})
        for part in _converter().convert(name)
    ]
    if prod(len(readings) for readings in readings_per_segment) > (
        _MAX_READING_COMBINATIONS
    ):
        return frozenset({_hepburn(name)})

    return frozenset(
        _hepburn("".join(combination)) for combination in product(*readings_per_segment)
    )


# TODO: Validate
def _unmarked(plaintext_name: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", plaintext_name)
        if not unicodedata.combining(character)
    )


# TODO: Validate
def _folded(plaintext_name: str) -> str:
    """Return a romanisation with the choices romanisers disagree on taken out.

    A long vowel is written "ou", "oo", "ō" or "o" depending on who romanised it,
    and an "n" before a "b", "m" or "p" is written either way, so all of them are
    written the one way here rather than read as different names.
    """
    without_long_vowels = re.sub(
        r"([aeiou])\1+",
        r"\1",
        _unmarked(plaintext_name).replace("ou", "o"),
    )
    return re.sub(r"m(?=[bmp])", "n", without_long_vowels)


# TODO: Validate
@cache
def plaintext_forms(name: str | None) -> frozenset[str]:
    """Return every spelling `name` could be written in, reduced to plaintext.

    The name itself is always one of them, so a name with nothing to romanise is
    no worse off for being asked.
    """
    if not name:
        return frozenset()

    plaintext_name = plaintext(name)
    forms = {plaintext_name, _folded(plaintext_name)}

    for romanization in _romanizations(name):
        romanized = plaintext(romanization)
        if romanized != plaintext_name:
            forms |= {romanized, _folded(romanized)}

    return frozenset(form for form in forms if form)
