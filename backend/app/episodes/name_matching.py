# TODO: Validate

import re
from functools import lru_cache

from rapidfuzz import fuzz

from app.episodes import name_forms

_NUMBERED_NAME = r"(?:(?:episode|ep|session|part)\s*\.?\s*#?\s*\d+|#\s*\d+)"
_ONLY_NUMBERED_NAME = re.compile(rf"^\s*{_NUMBERED_NAME}\s*$", re.IGNORECASE)


# TODO: Validate
def _untitled_number(name: str) -> str:
    untitled = re.sub(
        rf"^\s*{_NUMBERED_NAME}\s*[-:.]?\s+",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    return untitled or name


# TODO: Validate
def is_only_numbered_name(name: str) -> bool:
    return _ONLY_NUMBERED_NAME.match(name) is not None


# TODO: Validate
@lru_cache(maxsize=16384)
def plaintext(name: str | None) -> str:
    if not name:
        return ""
    return name_forms.plaintext(_untitled_number(name))


# TODO: Validate
@lru_cache(maxsize=16384)
def loose_plaintext(name: str | None) -> str:
    if not name:
        return ""
    stripped = plaintext(
        re.sub(r"\bthe\b", " ", _untitled_number(name), flags=re.IGNORECASE),
    )
    return stripped.removesuffix("s") or stripped


# TODO: Validate
@lru_cache(maxsize=16384)
def name_parts(name: str | None) -> tuple[str, ...]:
    if not name or not plaintext(name):
        return ()
    parts = [
        part
        for part in re.split(r"[/;]|\s+-\s+", name)
        if plaintext(part) and not is_only_numbered_name(part)
    ]
    if len(parts) < 2:  # noqa: PLR2004
        return (name,)
    return tuple(dict.fromkeys([name, *parts]))


# TODO: Validate
def contains_name(name: str, other_name: str) -> bool:
    if not name or not other_name or len(other_name) >= len(name):
        return False
    return other_name in name


# TODO: Validate
@lru_cache(maxsize=65536)
def similarity(name: str | None, other_name: str | None) -> float:
    stripped = plaintext(name)
    other_stripped = plaintext(other_name)
    if not stripped or not other_stripped:
        return 0.0
    if stripped == other_stripped:
        return 1.0

    ratio = fuzz.ratio(stripped, other_stripped) / 100
    if stripped not in other_stripped and other_stripped not in stripped:
        return ratio

    shorter, longer = sorted((stripped, other_stripped), key=len)
    return max(ratio, len(shorter) / len(longer))
