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
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

TMDB_PLUGIN_KEY = "TMDB"
# A record only has a TMDB counterpart while its identifier is one TMDB issued.
TMDB_IDENTIFIER_PREFIX = f"{TMDB_PLUGIN_KEY} "

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
TMDB_EPISODE_NUMBER_FIELD = "tmdb_episode_number"
NAME_FIELD = "name"


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
        row
        for row in rows
        if str(getattr(row, identifier_field)).startswith(TMDB_IDENTIFIER_PREFIX)
        and any(getattr(row, field) is None for field in fields)
    ]
    if not incomplete:
        return rows

    identifiers = {getattr(row, identifier_field) for row in incomplete}
    counterparts = {
        getattr(record, identifier_field): record
        for record in session.exec(statement(identifiers)).all()
    }
    for row in incomplete:
        counterpart = counterparts.get(getattr(row, identifier_field))
        if counterpart is None:
            continue
        for field in fields:
            if getattr(row, field) is None:
                setattr(row, field, getattr(counterpart, field))
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


def fill_episodes[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Fill what the website left out of each `Episode` row from TMDB."""
    return _fill(
        session,
        rows,
        _tmdb_episodes,
        EPISODE_IDENTIFIER_FIELD,
        EPISODE_FALLBACK_FIELDS,
    )


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


def prefer_tmdb_episodes[RowT](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Replace each linked `Episode` row's name and numbers with TMDB's own.

    Which season an episode belongs to, where in it, and what it is called are
    all things two websites disagree about. Where an episode is linked, TMDB's
    answer is the one to go by, and an episode with no TMDB counterpart keeps
    what the website said.
    """
    identifiers = _tmdb_identified(rows, EPISODE_IDENTIFIER_FIELD)
    if not identifiers:
        return rows

    statement = (
        select(Episode, Season.season_number)
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
        episode.episode_identifier: (episode, season_number)
        for episode, season_number in session.exec(statement).all()
    }
    for row in rows:
        counterpart = counterparts.get(getattr(row, EPISODE_IDENTIFIER_FIELD))
        if counterpart is None:
            continue
        episode, season_number = counterpart
        setattr(row, TMDB_SEASON_NUMBER_FIELD, season_number)
        setattr(row, TMDB_EPISODE_NUMBER_FIELD, episode.episode_number)
        if episode.name:
            setattr(row, NAME_FIELD, episode.name)
    return rows
