# TODO: Validate

import re
from functools import cache

_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "i": "1",
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
}

_WRITTEN_PART = re.compile(
    r"\b(?:parts?|pts?)\s*\.?\s*#?\s*(?P<number>\d+|[a-z]+)\b",
    re.IGNORECASE,
)

_BRACKETED_PART = re.compile(
    r"[(\[]\s*(?P<number>\d{1,2}|[ivx]+)\s*[)\]]",
    re.IGNORECASE,
)


# TODO: Validate
def _part_number(found: re.Match[str]) -> str:
    number = found["number"]
    if number.isdigit():
        return f"part {int(number)}"
    written = _NUMBER_WORDS.get(number.casefold())
    if written is None:
        return found[0]
    return f"part {written}"


# TODO: Validate
@cache
def part_numbers(name: str | None) -> str:
    """Return `name` with every way of writing a part number written one way."""
    if not name:
        return ""
    return _BRACKETED_PART.sub(_part_number, _WRITTEN_PART.sub(_part_number, name))


# TODO: Validate
@cache
def plaintext(name: str | None) -> str:
    """Return `name` with its case, punctuation and spacing taken out."""
    if not name:
        return ""
    spelled_out = name.casefold().replace("&", " and ")
    return "".join(character for character in spelled_out if character.isalnum())


# TODO: Validate
def _without_title_prefix(name: str, title_name: str | None) -> str:
    if not title_name:
        return name
    without_prefix = re.sub(
        rf"^{re.escape(title_name)}[\s\-:|,~.#\u2013\u2014]+",
        "",
        name,
        flags=re.IGNORECASE,
    )
    if without_prefix == name:
        return name
    return _tidied(without_prefix)


# TODO: Validate
def _tidied(name: str) -> str:
    collapsed = re.sub(r"\s+", " ", name)
    return re.sub(r"^[\s\-:|]+|[\s\-:|]+$", "", collapsed)


# TODO: Validate
def _without_name(name: str, other: str | None) -> str:
    if not other:
        return name
    return _tidied(re.sub(re.escape(other), " ", name, flags=re.IGNORECASE))


# TODO: Validate
def _without_season_marker(name: str, season_number: int | None) -> str:
    if season_number is None:
        return name
    marker = rf"\b(?:s|seasons?)\s*#?\s*0*{season_number}\b"
    return _tidied(re.sub(marker, " ", name, flags=re.IGNORECASE))


# TODO: Validate
def strip_show_and_season(
    name: str | None,
    title_name: str | None = None,
    season_name: str | None = None,
    season_number: int | None = None,
) -> str:
    without_language = re.sub(
        r"\((?:sub|dub)\)",
        "",
        name or "",
        flags=re.IGNORECASE,
    )
    without_title = _without_name(without_language, title_name)
    without_season = _without_name(without_title, season_name)
    return _without_season_marker(without_season, season_number)


# TODO: Validate
def get_cased_episode_name(
    name: str | None,
    title_name: str | None = None,
    season_name: str | None = None,
    series_name: str | None = None,
) -> str:
    without_language = re.sub(
        r"\((?:sub|dub)\)",
        "",
        name or "",
        flags=re.IGNORECASE,
    ).strip()
    without_title = _without_title_prefix(without_language, title_name)
    without_season = _without_title_prefix(without_title, season_name)
    without_series = _without_title_prefix(without_season, series_name)
    if re.fullmatch(r"Episode \d+", without_series):
        return ""
    return part_numbers(without_series)


# TODO: Validate
def get_normalized_episode_name(
    name: str | None,
    title_name: str | None = None,
    season_name: str | None = None,
    series_name: str | None = None,
) -> str:
    """Return a normalized episode name.

    Changes:
    - Casefold the episode name.
    - Remove language indicators like "(sub)" or "(dub)".
    - Remove the title (movie/show name) from the episode name.
    - Remove generic episode numbering like "Episode X".
    """
    return get_cased_episode_name(
        name,
        title_name,
        season_name,
        series_name,
    ).casefold()
