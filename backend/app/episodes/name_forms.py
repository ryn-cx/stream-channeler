# TODO: Validate

from functools import cache


# TODO: Validate
@cache
def plaintext(name: str | None) -> str:
    """Return `name` with its case, punctuation and spacing taken out."""
    if not name:
        return ""
    spelled_out = name.casefold().replace("&", " and ")
    return "".join(character for character in spelled_out if character.isalnum())
