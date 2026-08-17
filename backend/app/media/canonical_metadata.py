# TODO: Validate
"""Serve a non-canonical row of an episode as the episode itself.

A plugin stores only what its own website reported, so anything that site had no value
for stays unset on the stored record, and what it did report is one website's account of
a thing every other website also has an account of. The canonical row is the single
answer for all of them — TMDB's where TMDB has a record, and the one non-canonical row's
own where it does not — so a record is served by reading the row it points at.

Only episodes are served this way. A listing is linked to however many titles a
website mixed into one page, and no one of them is the title its name and artwork
belong to, so a listing is served as the website stored it.

Nothing is written back. A non-canonical row follows the canonical row as it is served
rather than being rewritten whenever that row changes.

This is the whole of what `tmdb_fallback.py` did, without the identifier-string
lookup or the special case for media TMDB has never heard of: a YouTube video
reads its canonical row exactly as a linked episode does, and the only thing
still asked about TMDB is whether there is a page on themoviedb.org to link to.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.canonical_media.episodes import canonical_episode_link, links_of
from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import SHOW_LEVEL, parse_tmdb_key
from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.models import MediaMixin
from app.seasons.models import Season
from app.shows.models import Show

# The three merged media models, named by the base they share so a level is
# something to pass rather than something to branch on.
type MediaModel = type[MediaMixin[Any, Any]]

# What each level's canonical row answers for. Anything else belongs to the
# non-canonical row alone — `url` above all, which says where rather than what.
#
# There is no such list for a show. A listing is linked to however many titles a
# website mixed into it, so there is no one row to read a listing's name or
# artwork off, and a listing is served as the website stored it.
EPISODE_FIELDS = (
    "name",
    "description",
    "image_url",
    "duration",
    "air_date",
)

EPISODE_ID_FIELD = "canonical_episode_id"

CANONICAL_KEY_FIELD = "canonical_key"

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
    model: MediaModel,
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
        for record in session.exec(
            select(model).where(is_canonical(model), col(model.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def _fill[RowT](
    session: Session,
    rows: Sequence[RowT],
    id_field: str,
    model: MediaModel,
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
        _label(row, canonical)
    return rows


# TODO: Validate
def _prefer[RowT](
    session: Session,
    rows: Sequence[RowT],
    id_field: str,
    model: MediaModel,
    fields: tuple[str, ...],
) -> Sequence[RowT]:
    """Replace every `fields` value on `rows` with their canonical row's.

    What the canonical row holds is what the media is served as, and what the website
    said is kept only where the canonical row has nothing of its own to say. A
    non-canonical row that is not yet of anything is served entirely as it stored
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
        _label(row, canonical)
    return rows


# TODO: Validate
def _label(row: Any, canonical: Any) -> None:  # noqa: ANN401 - Any output row.
    """Hand the row what says what it is, where it has somewhere to put it.

    The identifier rather than the key, since a key is a website's own id and two
    websites can issue the same one. Collapsing on the key alone would take two
    rows that merely read alike for one episode listed twice.
    """
    if hasattr(row, CANONICAL_KEY_FIELD):
        setattr(row, CANONICAL_KEY_FIELD, canonical.watch_identifier)


# TODO: Validate
def fill_episodes[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Serve each `Episode` row as the episode is, falling back on the site."""
    return _prefer(session, rows, EPISODE_ID_FIELD, Episode, EPISODE_FIELDS)


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
    canonical_rows = _canonical_rows(session, rows, EPISODE_ID_FIELD, Episode)
    seasons = _seasons_of(session, canonical_rows.values())
    for row in rows:
        canonical = canonical_rows.get(getattr(row, EPISODE_ID_FIELD, None))
        if canonical is None:
            continue
        season = seasons.get(canonical.season_id)
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
    canonical_episodes: Any,  # noqa: ANN401 - Any iterable of `Episode`.
) -> dict[UUID, Season]:
    """Load the canonical season holding each of `canonical_episodes`."""
    ids = {episode.season_id for episode in canonical_episodes}
    if not ids:
        return {}
    return {
        season.id: season
        for season in session.exec(
            select(Season).where(col(Season.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def fill_tmdb_urls[RowT](session: Session, rows: Sequence[RowT]) -> Sequence[RowT]:
    """Set each `Episode` row's page on themoviedb.org, where it has one.

    TMDB has no page for an episode id on its own, so the address is built from the
    title it belongs to and the numbering the episode itself carries, which is not
    always the numbering the website gave its own non-canonical row. Media TMDB has no
    record of has no page, and is left with none rather than a broken one.
    """
    canonical_rows = _canonical_rows(session, rows, EPISODE_ID_FIELD, Episode)
    seasons = _seasons_of(session, canonical_rows.values())
    shows = _shows_of(session, seasons.values())
    for row in rows:
        canonical = canonical_rows.get(getattr(row, EPISODE_ID_FIELD, None))
        if canonical is None:
            continue
        season = seasons.get(canonical.season_id)
        show = shows.get(season.show_id) if season else None
        if show is None:
            continue
        url = tmdb_episode_url(
            show.key,
            season.season_number if season else None,
            canonical.episode_number,
        )
        if url:
            setattr(row, TMDB_URL_FIELD, url)
    return rows


# TODO: Validate
def _shows_of(
    session: Session,
    canonical_seasons: Any,  # noqa: ANN401 - Any iterable of `Season`.
) -> dict[UUID, Show]:
    """Load the canonical title holding each of `canonical_seasons`."""
    ids = {season.show_id for season in canonical_seasons}
    if not ids:
        return {}
    return {
        show.id: show
        for show in session.exec(
            select(Show).where(is_canonical(Show), col(Show.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def tmdb_episode_url(
    show_key: str | None,
    season_number: int | None,
    episode_number: int | None,
) -> str | None:
    """Return the page for an episode on themoviedb.org, if TMDB has one.

    Built from the key of the title the episode is under, which is where the
    half of the catalogue and the id both come from. A film is a single page
    with nothing below it, so its one episode is that page. Media TMDB has no
    record of has no page at all.
    """
    parsed = parse_tmdb_key(show_key, SHOW_LEVEL)
    if parsed is None:
        return None
    media_type, tmdb_id = parsed
    if media_type is MediaType.movie:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    if season_number is None or episode_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return (
        f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
        f"/season/{season_number}/episode/{episode_number}"
    )


# TODO: Validate
def tmdb_season_url(show_key: str | None, season_number: int | None) -> str | None:
    """Return the page for a season on themoviedb.org, if TMDB has one.

    A film is a single page with nothing below it, so its one season is that
    page, and so is a series season TMDB has no number for.
    """
    parsed = parse_tmdb_key(show_key, SHOW_LEVEL)
    if parsed is None:
        return None
    media_type, tmdb_id = parsed
    if media_type is MediaType.movie or season_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}/season/{season_number}"


# TODO: Validate
def tmdb_show_url(show_key: str | None) -> str | None:
    """Return the page for a title on themoviedb.org, if TMDB has one."""
    parsed = parse_tmdb_key(show_key, SHOW_LEVEL)
    if parsed is None:
        return None
    media_type, tmdb_id = parsed
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"


# TODO: Validate
def canonical_episode_of(
    session: Session,
    canonical_episode_id: UUID | None,
) -> tuple[Episode, Season, Show] | None:
    """Return the episode a non-canonical row is of, with the season and title above it.

    A non-canonical row that is not of anything yet has nothing to return, which is the
    one case a caller has to handle; media TMDB has never heard of has a canonical row
    like any other.
    """
    if canonical_episode_id is None:
        return None
    return session.exec(
        select(Episode, Season, Show)
        .join(
            Season,
            onclause=col(Episode.season_id) == Season.id,
        )
        .join(
            Show,
            onclause=col(Season.show_id) == Show.id,
        )
        .where(
            is_canonical(Episode),
            is_canonical(Show),
            Episode.id == canonical_episode_id,
        ),
    ).first()


# TODO: Validate
def canonical_season_of(
    session: Session,
    season_id: UUID,
) -> tuple[Season, Show] | None:
    """Return the season a non-canonical row's episodes are of, with the title above it.

    A season is not a non-canonical row of anything itself, so the answer is the season
    its episodes' canonical episodes are under, which is nothing when none of them is
    linked to anything.
    """
    copy_episode = aliased(Episode)
    canonical_episode = aliased(Episode)
    copy_link = canonical_episode_link()
    return session.exec(
        select(Season, Show)
        .select_from(copy_episode)
        .join(copy_link, links_of(copy_episode, copy_link))
        .join(
            canonical_episode,
            onclause=col(copy_link.canonical_episode_id) == canonical_episode.id,
        )
        .join(Season, onclause=col(canonical_episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            is_canonical(Show),
            col(copy_episode.season_id) == season_id,
            col(copy_episode.deleted_at).is_(None),
        ),
    ).first()


# TODO: Validate
def canonical_show_of(session: Session, show: Show) -> Show | None:
    """Return the one title `show` is linked to, where it is linked to one.

    A listing that mixes titles is as much linked to each of them as of any
    other, so there is no one title to set beside it and it is answered for with
    none.
    """
    canonical_show_id = show.sole_canonical_show_id
    if canonical_show_id is None:
        return None
    return session.exec(
        select(Show).where(is_canonical(Show), Show.id == canonical_show_id),
    ).first()


# TODO: Validate
def canonical_numberings(
    canonical_show: Show,
) -> list[tuple[UUID, int | None, int | None]]:
    """Return how a title numbers each of its episodes, for counting them through.

    The canonical mirror of `_numberings` in the base plugin: canonical rows are
    never soft-deleted, so every season and episode under the title counts.
    """
    return [
        (episode.id, season.season_number, episode.episode_number)
        for season in canonical_show.seasons
        for episode in season.episodes
    ]
