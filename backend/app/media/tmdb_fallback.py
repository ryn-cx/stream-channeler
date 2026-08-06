# TODO: Validate
"""Fill what a website leaves out from the TMDB media standing in for it.

A plugin stores only what its own website reports, so anything the site has no
value for stays unset on the stored record. The TMDB plugin imports the same
title as its own media, and every record links to it by `tmdb_id`, so the gaps
are filled from there as the media is served. Nothing is written back, which is
what lets a record follow TMDB without being rewritten every time TMDB changes.
"""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

TMDB_PLUGIN_KEY = "TMDB"


class _TMDBLinked(Protocol):
    """A row carrying the TMDB id of the media standing in for it."""

    tmdb_id: int | None


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


def _tmdb_shows(tmdb_ids: set[int]) -> SelectOfScalar[Show]:
    return (
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Show.tmdb_id).in_(tmdb_ids),
            col(Show.deleted_at).is_(None),
        )
    )


def _tmdb_seasons(tmdb_ids: set[int]) -> SelectOfScalar[Season]:
    return (
        select(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Season.tmdb_id).in_(tmdb_ids),
            col(Season.deleted_at).is_(None),
        )
    )


def _tmdb_episodes(tmdb_ids: set[int]) -> SelectOfScalar[Episode]:
    return (
        select(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Episode.tmdb_id).in_(tmdb_ids),
            col(Episode.deleted_at).is_(None),
        )
    )


def _fill[RowT: _TMDBLinked](
    session: Session,
    rows: Sequence[RowT],
    statement: Callable[[set[int]], SelectOfScalar[Any]],
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Fill every unset `fields` value on `rows` from their TMDB counterpart.

    `rows` are output schemas rather than stored records, so filling them leaves
    nothing to be written back to the database.
    """
    incomplete = [
        row
        for row in rows
        if row.tmdb_id is not None
        and any(getattr(row, field) is None for field in fields)
    ]
    if not incomplete:
        return rows

    tmdb_ids = {row.tmdb_id for row in incomplete if row.tmdb_id is not None}
    counterparts = {
        record.tmdb_id: record for record in session.exec(statement(tmdb_ids)).all()
    }
    for row in incomplete:
        counterpart = counterparts.get(row.tmdb_id)
        if counterpart is None:
            continue
        for field in fields:
            if getattr(row, field) is None:
                setattr(row, field, getattr(counterpart, field))
    return rows


def fill_shows[RowT: _TMDBLinked](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Fill what the website left out of each `Show` row from TMDB."""
    return _fill(session, rows, _tmdb_shows, SHOW_FALLBACK_FIELDS)


def fill_seasons[RowT: _TMDBLinked](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Fill what the website left out of each `Season` row from TMDB."""
    return _fill(session, rows, _tmdb_seasons, SEASON_FALLBACK_FIELDS)


def fill_episodes[RowT: _TMDBLinked](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Fill what the website left out of each `Episode` row from TMDB."""
    return _fill(session, rows, _tmdb_episodes, EPISODE_FALLBACK_FIELDS)
