# TODO: Validate
"""What makes the same media on two websites one thing rather than two.

A `Show`, `Season` and `Episode` each carry an identifier, and it is the TMDB
record's whenever the media is linked to TMDB. The id is read back off that
identifier rather than stored beside it, so the two can never disagree about
which TMDB record the media stands for.

Kept clear of the models so they can read their own identifiers without the
import going in a circle.
"""

TMDB_PLUGIN_KEY = "TMDB"
# A record only has a TMDB counterpart while its identifier is one TMDB issued.
TMDB_IDENTIFIER_PREFIX = f"{TMDB_PLUGIN_KEY} "


def tmdb_identifier(media_type: str, tmdb_id: int) -> str:
    """Return the identifier naming a TMDB record.

    TMDB numbers films and series separately, so the media type is part of the
    identifier to keep a film and a series that share a number apart.
    """
    return f"{TMDB_IDENTIFIER_PREFIX}{media_type} {tmdb_id}"


def identifier_tmdb_id(identifier: str | None) -> int | None:
    """Return the TMDB id an identifier names, or `None` when it names none.

    An identifier a website issued itself names no TMDB record and has no id to
    give, and neither does one that is not shaped like `TMDB <media type> <id>`.
    """
    if not identifier or not identifier.startswith(TMDB_IDENTIFIER_PREFIX):
        return None
    _, _, remainder = identifier.partition(" ")
    _, _, raw_id = remainder.partition(" ")
    return int(raw_id) if raw_id.isdigit() else None
