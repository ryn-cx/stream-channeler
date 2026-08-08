# TODO: Validate
"""Check an identifier a `User` wrote names a TMDB record, and import what it names.

A `User` can point a record at TMDB by hand by writing the TMDB record's own
identifier on it. Nothing about the identifier says whether TMDB has the record
it names, so one with a wrong id would be stored as a link to nothing and fill
nothing in. Both halves of that are settled here: the identifier is checked
against TMDB, and the title it belongs to is imported so there is something for
the link to read.
"""

from fastapi import HTTPException
from sqlmodel import Session

from app.media.identifiers import MediaType, parse_tmdb_identifier
from plugins.TMDB import TMDB


def check_show_identifier(session: Session, show_identifier: str) -> None:
    """Import the TMDB title a `show_identifier` names, refusing one TMDB has not."""
    parsed = parse_tmdb_identifier(show_identifier)
    if parsed is None:
        return

    media_type, tmdb_id = parsed
    _import_title(session, media_type, tmdb_id)


def check_season_identifier(
    session: Session,
    season_identifier: str,
    show_identifier: str,
) -> None:
    """Check a `season_identifier` names a season of the title its `Show` is linked to.

    A season identifier carries the season's own TMDB id, which says nothing
    about which title the season belongs to, so it is looked for among the
    seasons of the title the `Show` names.
    """
    parsed = parse_tmdb_identifier(season_identifier)
    if parsed is None:
        return

    media_type, tmdb_id = _title_of(show_identifier, season_identifier)
    _import_title(session, media_type, tmdb_id)
    if not TMDB(session).has_season_id(media_type, tmdb_id, parsed[1]):
        raise HTTPException(
            status_code=400,
            detail=f"{show_identifier} has no season {season_identifier}",
        )


def check_episode_identifier(
    session: Session,
    episode_identifier: str,
    show_identifier: str,
) -> None:
    """Check an `episode_identifier` names an episode of the title its `Show` names.

    An episode identifier carries the episode's own TMDB id, which says nothing
    about which title or season the episode belongs to, so it is looked for among
    every episode of the title the `Show` names.
    """
    parsed = parse_tmdb_identifier(episode_identifier)
    if parsed is None:
        return

    media_type, tmdb_id = _title_of(show_identifier, episode_identifier)
    _import_title(session, media_type, tmdb_id)
    if not TMDB(session).has_episode_id(media_type, tmdb_id, parsed[1]):
        raise HTTPException(
            status_code=400,
            detail=f"{show_identifier} has no episode {episode_identifier}",
        )


def _title_of(show_identifier: str, identifier: str) -> tuple[MediaType, int]:
    """Return the TMDB title a season or episode identifier is checked against.

    A season and an episode are only ever TMDB's while the title holding them is,
    so a title carrying a website's own identifier has nothing to check against
    and is what has to be pointed at TMDB first.
    """
    parsed = parse_tmdb_identifier(show_identifier)
    if parsed is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{identifier} names a TMDB record, but its show is not linked to"
                f" TMDB ({show_identifier})"
            ),
        )
    return parsed


def _import_title(session: Session, media_type: MediaType, tmdb_id: int) -> None:
    """Import a whole TMDB title, refusing an id TMDB has no title for.

    A title already imported is left as it is, so this costs nothing beyond the
    check when the media a `User` pointed at is already there.
    """
    if TMDB(session).import_title(media_type, tmdb_id) is None:
        raise HTTPException(
            status_code=400,
            detail=f"TMDB has no {media_type} with the id {tmdb_id}",
        )
