# TODO: Validate
"""Serve a copy of a title as the title itself.

A plugin stores only what its own website reported, so anything that site had no
value for stays unset on the stored record, and what it did report is one
website's account of a thing every other website also has an account of. The
canonical row is the single answer for all of them — TMDB's where TMDB has a
record, and the one copy's own where it does not — so a record is served by
reading the row it points at.

Nothing is written back. A copy follows the canonical row as it is served rather
than being rewritten whenever that row changes.

This is the whole of what `tmdb_fallback.py` did, without the identifier-string
lookup or the special case for media TMDB has never heard of: a YouTube video
reads its canonical row exactly as a linked episode does, and the only thing
still asked about TMDB is whether there is a page on themoviedb.org to link to.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow

# What each level's canonical row answers for. Anything else belongs to the copy
# alone — `url` above all, which says where rather than what.
SHOW_FIELDS = ("name", "description", "image_url")
SEASON_FIELDS = ("name", "image_url")
EPISODE_FIELDS = (
    "name",
    "description",
    "image_url",
    "duration",
    "release_date",
    "air_date",
)

SHOW_ID_FIELD = "canonical_show_id"
SEASON_ID_FIELD = "canonical_season_id"
EPISODE_ID_FIELD = "canonical_episode_id"

TMDB_SEASON_NUMBER_FIELD = "tmdb_season_number"
TMDB_SEASON_NAME_FIELD = "tmdb_season_name"
TMDB_EPISODE_NUMBER_FIELD = "tmdb_episode_number"
TMDB_URL_FIELD = "tmdb_url"
NAME_FIELD = "name"

TMDB_PAGE_URL = "https://www.themoviedb.org"


# TODO: Validate
def _canonical_rows(
    session: Session,
    rows: Sequence[Any],
    id_field: str,
    model: type[CanonicalShow | CanonicalSeason | CanonicalEpisode],
) -> dict[UUID, Any]:
    """Load the canonical row each of `rows` points at, keyed by its id."""
    ids = {
        getattr(row, id_field, None)
        for row in rows
        if getattr(row, id_field, None) is not None
    }
    if not ids:
        return {}
    return {
        record.id: record
        for record in session.exec(select(model).where(col(model.id).in_(ids))).all()
    }


# TODO: Validate
def _fill[RowT](
    session: Session,
    rows: Sequence[RowT],
    id_field: str,
    model: type[CanonicalShow | CanonicalSeason | CanonicalEpisode],
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Fill every unset `fields` value on `rows` from their canonical row.

    `rows` are output schemas rather than stored records, so filling them leaves
    nothing to be written back to the database.
    """
    incomplete = [
        row for row in rows if any(getattr(row, field) is None for field in fields)
    ]
    canonical_rows = _canonical_rows(session, incomplete, id_field, model)
    for row in incomplete:
        canonical = canonical_rows.get(getattr(row, id_field, None))
        if canonical is None:
            continue
        for field in fields:
            if getattr(row, field) is None:
                setattr(row, field, getattr(canonical, field))
    return rows


# TODO: Validate
def _prefer[RowT](
    session: Session,
    rows: Sequence[RowT],
    id_field: str,
    model: type[CanonicalShow | CanonicalSeason | CanonicalEpisode],
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Replace every `fields` value on `rows` with their canonical row's.

    What the canonical row holds is what the media is served as, and what the
    website said is kept only where the canonical row has nothing of its own to
    say. A copy that is not yet of anything is served entirely as it stored
    itself.
    """
    canonical_rows = _canonical_rows(session, rows, id_field, model)
    for row in rows:
        canonical = canonical_rows.get(getattr(row, id_field, None))
        if canonical is None:
            continue
        for field in fields:
            value = getattr(canonical, field)
            if value is not None:
                setattr(row, field, value)
    return rows


# TODO: Validate
def fill_shows[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Fill what the website left out of each `Show` row from the title itself."""
    return _fill(session, rows, SHOW_ID_FIELD, CanonicalShow, SHOW_FIELDS)


# TODO: Validate
def fill_seasons[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Fill what the website left out of each `Season` row from the season itself."""
    return _fill(session, rows, SEASON_ID_FIELD, CanonicalSeason, SEASON_FIELDS)


# TODO: Validate
def prefer_shows[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each `Show` row as the title is, falling back on the site."""
    return _prefer(session, rows, SHOW_ID_FIELD, CanonicalShow, SHOW_FIELDS)


# TODO: Validate
def prefer_seasons[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each `Season` row as the season is, falling back on the site."""
    return _prefer(session, rows, SEASON_ID_FIELD, CanonicalSeason, SEASON_FIELDS)


# TODO: Validate
def fill_episodes[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each `Episode` row as the episode is, falling back on the site."""
    return _prefer(session, rows, EPISODE_ID_FIELD, CanonicalEpisode, EPISODE_FIELDS)


# TODO: Validate
def prefer_canonical_seasons[RowT](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Replace each `Season` row's name and number with the season's own.

    A website names and numbers its own seasons, which is not how the season is
    named and numbered as a season. A row whose copy is not yet of anything keeps
    what the website said.
    """
    canonical_rows = _canonical_rows(session, rows, SEASON_ID_FIELD, CanonicalSeason)
    for row in rows:
        canonical = canonical_rows.get(getattr(row, SEASON_ID_FIELD, None))
        if canonical is None:
            continue
        setattr(row, TMDB_SEASON_NUMBER_FIELD, canonical.season_number)
        if canonical.name:
            setattr(row, NAME_FIELD, canonical.name)
    return rows


# TODO: Validate
def prefer_canonical_episodes[RowT](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    """Replace each `Episode` row's name and season with the episode's own.

    Which season an episode belongs to, where in it, and what it is called are
    all things two websites disagree about. The season comes off the canonical
    episode rather than off the row's own season, since a site can file an
    episode under a season the canonical hierarchy does not, which is what puts
    one site's finale in another's specials.
    """
    canonical_rows = _canonical_rows(session, rows, EPISODE_ID_FIELD, CanonicalEpisode)
    seasons = _seasons_of(session, canonical_rows.values())
    for row in rows:
        canonical = canonical_rows.get(getattr(row, EPISODE_ID_FIELD, None))
        if canonical is None:
            continue
        season = seasons.get(canonical.canonical_season_id)
        setattr(row, TMDB_EPISODE_NUMBER_FIELD, canonical.episode_number)
        if season is not None:
            setattr(row, TMDB_SEASON_NUMBER_FIELD, season.season_number)
            setattr(row, TMDB_SEASON_NAME_FIELD, season.name)
        if canonical.name:
            setattr(row, NAME_FIELD, canonical.name)
    return rows


# TODO: Validate
def _seasons_of(
    session: Session,
    canonical_episodes: Any,  # noqa: ANN401 - Any iterable of `CanonicalEpisode`.
) -> dict[UUID, CanonicalSeason]:
    """Load the canonical season holding each of `canonical_episodes`."""
    ids = {episode.canonical_season_id for episode in canonical_episodes}
    if not ids:
        return {}
    return {
        season.id: season
        for season in session.exec(
            select(CanonicalSeason).where(col(CanonicalSeason.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def fill_tmdb_urls[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Set each `Episode` row's page on themoviedb.org, where it has one.

    TMDB has no page for an episode id on its own, so the address is built from
    the title it belongs to and the numbering the episode itself carries, which
    is not always the numbering the website gave its own copy. Media TMDB has no
    record of has no page, and is left with none rather than a broken one.
    """
    canonical_rows = _canonical_rows(session, rows, EPISODE_ID_FIELD, CanonicalEpisode)
    seasons = _seasons_of(session, canonical_rows.values())
    shows = _shows_of(session, seasons.values())
    for row in rows:
        canonical = canonical_rows.get(getattr(row, EPISODE_ID_FIELD, None))
        if canonical is None:
            continue
        season = seasons.get(canonical.canonical_season_id)
        show = shows.get(season.canonical_show_id) if season else None
        if show is None:
            continue
        url = tmdb_episode_url(
            show.tmdb_media_type,
            show.tmdb_id,
            season.season_number if season else None,
            canonical.episode_number,
        )
        if url:
            setattr(row, TMDB_URL_FIELD, url)
    return rows


# TODO: Validate
def _shows_of(
    session: Session,
    canonical_seasons: Any,  # noqa: ANN401 - Any iterable of `CanonicalSeason`.
) -> dict[UUID, CanonicalShow]:
    """Load the canonical title holding each of `canonical_seasons`."""
    ids = {season.canonical_show_id for season in canonical_seasons}
    if not ids:
        return {}
    return {
        show.id: show
        for show in session.exec(
            select(CanonicalShow).where(col(CanonicalShow.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def tmdb_episode_url(
    media_type: str | None,
    tmdb_id: int | None,
    season_number: int | None,
    episode_number: int | None,
) -> str | None:
    """Return the page for an episode on themoviedb.org, if TMDB has one.

    A film is a single page with nothing below it, so its one episode is that
    page. Media TMDB has no record of has no page at all.
    """
    if not media_type or tmdb_id is None:
        return None
    if media_type == "movie":
        return f"{TMDB_PAGE_URL}/movie/{tmdb_id}"
    if season_number is None or episode_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return (
        f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
        f"/season/{season_number}/episode/{episode_number}"
    )


# TODO: Validate
def tmdb_season_url(
    media_type: str | None,
    tmdb_id: int | None,
    season_number: int | None,
) -> str | None:
    """Return the page for a season on themoviedb.org, if TMDB has one.

    A film is a single page with nothing below it, so its one season is that
    page, and so is a series season TMDB has no number for.
    """
    if not media_type or tmdb_id is None:
        return None
    if media_type == "movie" or season_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}/season/{season_number}"


# TODO: Validate
def tmdb_show_url(media_type: str | None, tmdb_id: int | None) -> str | None:
    """Return the page for a title on themoviedb.org, if TMDB has one."""
    if not media_type or tmdb_id is None:
        return None
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"


# TODO: Validate
def canonical_episode_of(
    session: Session,
    canonical_episode_id: UUID | None,
) -> tuple[CanonicalEpisode, CanonicalSeason, CanonicalShow] | None:
    """Return the episode a copy is of, with the season and title above it.

    A copy that is not of anything yet has nothing to return, which is the one
    case a caller has to handle; media TMDB has never heard of has a canonical
    row like any other.
    """
    if canonical_episode_id is None:
        return None
    return session.exec(
        select(CanonicalEpisode, CanonicalSeason, CanonicalShow)
        .join(
            CanonicalSeason,
            onclause=col(CanonicalEpisode.canonical_season_id) == CanonicalSeason.id,
        )
        .join(
            CanonicalShow,
            onclause=col(CanonicalSeason.canonical_show_id) == CanonicalShow.id,
        )
        .where(CanonicalEpisode.id == canonical_episode_id),
    ).first()


# TODO: Validate
def canonical_season_of(
    session: Session,
    canonical_season_id: UUID | None,
) -> tuple[CanonicalSeason, CanonicalShow] | None:
    """Return the season a copy is of, with the title above it."""
    if canonical_season_id is None:
        return None
    return session.exec(
        select(CanonicalSeason, CanonicalShow)
        .join(
            CanonicalShow,
            onclause=col(CanonicalSeason.canonical_show_id) == CanonicalShow.id,
        )
        .where(CanonicalSeason.id == canonical_season_id),
    ).first()


# TODO: Validate
def canonical_show_of(
    session: Session,
    canonical_show_id: UUID | None,
) -> CanonicalShow | None:
    """Return the title a copy is of."""
    if canonical_show_id is None:
        return None
    return session.get(CanonicalShow, canonical_show_id)


# TODO: Validate
def canonical_numberings(
    canonical_show: CanonicalShow,
) -> list[tuple[UUID, int | None, int | None]]:
    """Return how a title numbers each of its episodes, for counting them through.

    The canonical mirror of `_numberings` in the base plugin: canonical rows are
    never soft-deleted, so every season and episode under the title counts.
    """
    return [
        (episode.id, season.season_number, episode.episode_number)
        for season in canonical_show.canonical_seasons
        for episode in season.canonical_episodes
    ]
