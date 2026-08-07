# TODO: Validate
"""Fill what a website leaves out from the TMDB media standing in for it.

A plugin stores only what its own website reports, so anything the site has no
value for stays unset on the stored record. The TMDB plugin imports the same
title as its own media, and every record carries the identifier of the TMDB
record standing in for it, so the gaps are filled from there as the media is
served. Nothing is written back, which is what lets a record follow TMDB without
being rewritten every time TMDB changes.
"""

from collections.abc import Callable, Sequence
from typing import Any

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.media.identifiers import (
    TMDB_IDENTIFIER_PREFIX,
    TMDB_PLUGIN_KEY,
)
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

SHOW_FALLBACK_FIELDS = ("name", "description", "image_url")
SEASON_FALLBACK_FIELDS = ("name", "image_url")
EPISODE_FALLBACK_FIELDS = (
    "name",
    "description",
    "image_url",
    "duration",
    "release_date",
    "air_date",
)

SHOW_IDENTIFIER_FIELD = "show_identifier"
SEASON_IDENTIFIER_FIELD = "season_identifier"
EPISODE_IDENTIFIER_FIELD = "episode_identifier"
TMDB_SEASON_NUMBER_FIELD = "tmdb_season_number"
TMDB_SEASON_NAME_FIELD = "tmdb_season_name"
TMDB_EPISODE_NUMBER_FIELD = "tmdb_episode_number"
TMDB_URL_FIELD = "tmdb_url"
NAME_FIELD = "name"

TMDB_PAGE_URL = "https://www.themoviedb.org"


def _tmdb_shows(identifiers: set[str]) -> SelectOfScalar[Show]:
    return (
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Show.show_identifier).in_(identifiers),
            col(Show.deleted_at).is_(None),
        )
    )


def _tmdb_seasons(identifiers: set[str]) -> SelectOfScalar[Season]:
    return (
        select(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Season.season_identifier).in_(identifiers),
            col(Season.deleted_at).is_(None),
        )
    )


def _tmdb_episodes(identifiers: set[str]) -> SelectOfScalar[Episode]:
    return (
        select(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Episode.episode_identifier).in_(identifiers),
            col(Episode.deleted_at).is_(None),
        )
    )


def _counterparts(
    session: Session,
    rows: Sequence[Any],
    statement: Callable[[set[str]], SelectOfScalar[Any]],
    identifier_field: str,
) -> dict[str, Any]:
    identifiers = _tmdb_identified(rows, identifier_field)
    if not identifiers:
        return {}

    return {
        getattr(record, identifier_field): record
        for record in session.exec(statement(identifiers)).all()
    }


def _fill[RowT](
    session: Session,
    rows: Sequence[RowT],
    statement: Callable[[set[str]], SelectOfScalar[Any]],
    identifier_field: str,
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Fill every unset `fields` value on `rows` from their TMDB counterpart.

    `rows` are output schemas rather than stored records, so filling them leaves
    nothing to be written back to the database.
    """
    incomplete = [
        row for row in rows if any(getattr(row, field) is None for field in fields)
    ]
    counterparts = _counterparts(session, incomplete, statement, identifier_field)
    for row in incomplete:
        counterpart = counterparts.get(getattr(row, identifier_field))
        if counterpart is None:
            continue
        for field in fields:
            if getattr(row, field) is None:
                setattr(row, field, getattr(counterpart, field))
    return rows


def _prefer[RowT](
    session: Session,
    rows: Sequence[RowT],
    statement: Callable[[set[str]], SelectOfScalar[Any]],
    identifier_field: str,
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Replace every `fields` value on `rows` with their TMDB counterpart's.

    What TMDB has is what the media is served as, and what the website said is
    kept only where TMDB has nothing of its own to say. `rows` are output schemas
    rather than stored records, so nothing is written back to the database.
    """
    counterparts = _counterparts(session, rows, statement, identifier_field)
    for row in rows:
        counterpart = counterparts.get(getattr(row, identifier_field))
        if counterpart is None:
            continue
        for field in fields:
            value = getattr(counterpart, field)
            if value is not None:
                setattr(row, field, value)
    return rows


def fill_shows[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Fill what the website left out of each `Show` row from TMDB."""
    return _fill(
        session,
        rows,
        _tmdb_shows,
        SHOW_IDENTIFIER_FIELD,
        SHOW_FALLBACK_FIELDS,
    )


def fill_seasons[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Fill what the website left out of each `Season` row from TMDB."""
    return _fill(
        session,
        rows,
        _tmdb_seasons,
        SEASON_IDENTIFIER_FIELD,
        SEASON_FALLBACK_FIELDS,
    )


def prefer_shows[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each linked `Show` row as TMDB has it, falling back on the site."""
    return _prefer(
        session,
        rows,
        _tmdb_shows,
        SHOW_IDENTIFIER_FIELD,
        SHOW_FALLBACK_FIELDS,
    )


def prefer_seasons[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each linked `Season` row as TMDB has it, falling back on the site."""
    return _prefer(
        session,
        rows,
        _tmdb_seasons,
        SEASON_IDENTIFIER_FIELD,
        SEASON_FALLBACK_FIELDS,
    )


def fill_episodes[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each linked `Episode` row as TMDB has it, falling back on the site."""
    return _prefer(
        session,
        rows,
        _tmdb_episodes,
        EPISODE_IDENTIFIER_FIELD,
        EPISODE_FALLBACK_FIELDS,
    )


def tmdb_episode_counterpart(
    session: Session,
    episode_identifier: str,
) -> tuple[Episode, Season, Show] | None:
    """Return the TMDB episode standing in for `episode_identifier`, and its parents.

    An episode only has a TMDB counterpart while it is linked, so an identifier
    the website issued itself has nothing to return.
    """
    if not episode_identifier.startswith(TMDB_IDENTIFIER_PREFIX):
        return None

    statement = (
        select(Episode, Season, Show)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            Episode.episode_identifier == episode_identifier,
            col(Episode.deleted_at).is_(None),
        )
    )
    return session.exec(statement).first()


def tmdb_season_counterpart(
    session: Session,
    season_identifier: str,
) -> tuple[Season, Show] | None:
    """Return the TMDB season standing in for `season_identifier`, and its show.

    A season only has a TMDB counterpart while it is linked, so an identifier the
    website issued itself has nothing to return.
    """
    if not season_identifier.startswith(TMDB_IDENTIFIER_PREFIX):
        return None

    statement = (
        select(Season, Show)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            Season.season_identifier == season_identifier,
            col(Season.deleted_at).is_(None),
        )
    )
    return session.exec(statement).first()


def tmdb_show_counterpart(session: Session, show_identifier: str) -> Show | None:
    """Return the TMDB title standing in for `show_identifier`.

    A title only has a TMDB counterpart while it is linked, so an identifier the
    website issued itself has nothing to return.
    """
    if not show_identifier.startswith(TMDB_IDENTIFIER_PREFIX):
        return None

    return session.exec(_tmdb_shows({show_identifier})).first()


def _tmdb_identified(rows: Sequence[Any], identifier_field: str) -> set[str]:
    return {
        getattr(row, identifier_field)
        for row in rows
        if str(getattr(row, identifier_field)).startswith(TMDB_IDENTIFIER_PREFIX)
    }


def prefer_tmdb_seasons[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Replace each linked `Season` row's name and number with TMDB's own.

    A website names and numbers its own seasons, which is not how TMDB names and
    numbers the same ones. Where a season is linked, TMDB's is the one to go by,
    and a season with no TMDB counterpart keeps what the website said.
    """
    identifiers = _tmdb_identified(rows, SEASON_IDENTIFIER_FIELD)
    if not identifiers:
        return rows

    counterparts = {
        season.season_identifier: season
        for season in session.exec(_tmdb_seasons(identifiers)).all()
    }
    for row in rows:
        counterpart = counterparts.get(getattr(row, SEASON_IDENTIFIER_FIELD))
        if counterpart is None:
            continue
        setattr(row, TMDB_SEASON_NUMBER_FIELD, counterpart.season_number)
        if counterpart.name:
            setattr(row, NAME_FIELD, counterpart.name)
    return rows


def fill_tmdb_urls[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Set each linked `Episode` row's page on themoviedb.org.

    TMDB has no page for an episode id on its own, so the address is built from
    the title it belongs to and the numbering TMDB gives it, which is not always
    the numbering the website gave its own copy.
    """
    identifiers = _tmdb_identified(rows, EPISODE_IDENTIFIER_FIELD)
    if not identifiers:
        return rows

    statement = (
        select(
            Episode.episode_identifier,
            Episode.episode_number,
            Season.season_number,
            Show.key,
        )  # type: ignore[call-overload]
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Episode.episode_identifier).in_(identifiers),
            col(Episode.deleted_at).is_(None),
        )
    )
    urls = {
        identifier: tmdb_episode_url(show_key, season_number, episode_number)
        for identifier, episode_number, season_number, show_key in session.exec(
            statement,
        ).all()
    }
    for row in rows:
        url = urls.get(getattr(row, EPISODE_IDENTIFIER_FIELD))
        if url:
            setattr(row, TMDB_URL_FIELD, url)
    return rows


def tmdb_episode_url(
    show_key: str,
    season_number: int | None,
    episode_number: int | None,
) -> str | None:
    """Return the page for a TMDB episode, given the show key it belongs to.

    A TMDB show is keyed by the path its own page lives at ("tv/76075"), which
    is what says whether the title is a film or a series. A film is a single
    page with nothing below it, so its one episode is that page.
    """
    media_type, _, tmdb_id = show_key.partition("/")
    if not tmdb_id:
        return None
    if media_type == "movie":
        return f"{TMDB_PAGE_URL}/movie/{tmdb_id}"
    if season_number is None or episode_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return (
        f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
        f"/season/{season_number}/episode/{episode_number}"
    )


def tmdb_season_url(show_key: str, season_number: int | None) -> str | None:
    """Return the page for a TMDB season, given the show key it belongs to.

    A film is a single page with nothing below it, so its one season is that
    page, and so is a series season TMDB has no number for.
    """
    media_type, _, tmdb_id = show_key.partition("/")
    if not tmdb_id:
        return None
    if media_type == "movie" or season_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}/season/{season_number}"


def tmdb_show_url(show_key: str) -> str | None:
    """Return the page for a TMDB title, given its key."""
    media_type, _, tmdb_id = show_key.partition("/")
    if not tmdb_id:
        return None
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"


def prefer_tmdb_episodes[RowT](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Replace each linked `Episode` row's name and season with TMDB's own.

    Which season an episode belongs to, where in it, and what it is called are
    all things two websites disagree about. The season comes off the TMDB episode
    rather than off the row's own season, since the site can file an episode under
    a season TMDB does not, which is what puts a site's finale in TMDB's specials.
    Where an episode is linked, TMDB's answer is the one to go by, and an episode
    with no TMDB counterpart keeps what the website said.
    """
    identifiers = _tmdb_identified(rows, EPISODE_IDENTIFIER_FIELD)
    if not identifiers:
        return rows

    statement = (
        select(Episode, Season.season_number, Season.name)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Episode.episode_identifier).in_(identifiers),
            col(Episode.deleted_at).is_(None),
        )
    )
    counterparts = {
        episode.episode_identifier: (episode, season_number, season_name)
        for episode, season_number, season_name in session.exec(statement).all()
    }
    for row in rows:
        counterpart = counterparts.get(getattr(row, EPISODE_IDENTIFIER_FIELD))
        if counterpart is None:
            continue
        episode, season_number, season_name = counterpart
        setattr(row, TMDB_SEASON_NUMBER_FIELD, season_number)
        setattr(row, TMDB_EPISODE_NUMBER_FIELD, episode.episode_number)
        setattr(row, TMDB_SEASON_NAME_FIELD, season_name)
        if episode.name:
            setattr(row, NAME_FIELD, episode.name)
    return rows
