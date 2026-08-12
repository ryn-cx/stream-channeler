# TODO: Validate
"""Make sure nothing reaches the database without the media it is a copy of.

There is no free-floating state: a `Show`, `Season` or `Episode` is always a
copy of something, even when that something is only itself. The plugins build
their records and hand them to the session long before `reconcile_show` runs, so
this fills the gap at the last possible moment — the flush — and lets the
pointers be `NOT NULL`.

The row is made under the key the copy's own key spells out, namespaced by the
plugin that issued it, which is the same key `reconcile_show` would later put it
under. So a copy imported again converges on the row it had rather than minting
a nameless one for the discard pass to clean up after.

A row the TMDB linker already pointed somewhere is left exactly as it is. What
this catches is the ordinary case of a website's own record, which is a copy of
nothing but itself and so gets a row of its own.
"""

import uuid

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_media.keys import record_key
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow


# TODO: Validate
def _already_pointed(canonical: object | None, canonical_id: uuid.UUID | None) -> bool:
    """Report whether a copy is already a copy of something.

    The row is read before the id, since a copy the TMDB linker pointed at one
    carries the row itself and does not carry the id until the flush this runs
    ahead of has written it.
    """
    return canonical is not None or canonical_id is not None


# TODO: Validate
def _plugin_key(show: Show) -> str | None:
    """Return the key of the plugin whose copy `show` is."""
    source = show.source
    if source is None:
        return None
    plugin = source.plugin
    return plugin.key if plugin else None


# TODO: Validate
def _pending_show(
    session: SQLAlchemySession,
    key: str,
) -> CanonicalShow | None:
    """Return the title `key` names, from the session or the database."""
    for pending in session.new:
        if isinstance(pending, CanonicalShow) and pending.key == key:
            return pending
    return session.scalars(
        select(CanonicalShow).where(CanonicalShow.key == key),
    ).first()


# TODO: Validate
def _pending_season(
    session: SQLAlchemySession,
    key: str,
    canonical_show: CanonicalShow,
) -> CanonicalSeason | None:
    """Return the season `key` names under `canonical_show`."""
    for pending in session.new:
        if (
            isinstance(pending, CanonicalSeason)
            and pending.key == key
            and pending.canonical_show is canonical_show
        ):
            return pending
    if canonical_show.id is None:
        return None
    return session.scalars(
        select(CanonicalSeason).where(
            CanonicalSeason.canonical_show_id == canonical_show.id,
            CanonicalSeason.key == key,
        ),
    ).first()


# TODO: Validate
def _pending_episode(
    session: SQLAlchemySession,
    key: str,
    canonical_season: CanonicalSeason,
) -> CanonicalEpisode | None:
    """Return the episode `key` names under `canonical_season`."""
    for pending in session.new:
        if (
            isinstance(pending, CanonicalEpisode)
            and pending.key == key
            and pending.canonical_season is canonical_season
        ):
            return pending
    if canonical_season.id is None:
        return None
    return session.scalars(
        select(CanonicalEpisode).where(
            CanonicalEpisode.canonical_season_id == canonical_season.id,
            CanonicalEpisode.key == key,
        ),
    ).first()


# TODO: Validate
def _fill_shows(session: SQLAlchemySession) -> None:
    """Give every new title in the session the canonical row it is a copy of."""
    for show in session.new:
        if not isinstance(show, Show) or _already_pointed(
            show.canonical_show,
            show.canonical_show_id,
        ):
            continue
        plugin_key = _plugin_key(show)
        if plugin_key is None:
            continue
        key = record_key(plugin_key, show.key)
        canonical = _pending_show(session, key)
        if canonical is None:
            canonical = CanonicalShow(
                key=key,
                name=show.name,
                media_type=show.media_type,
                description=show.description,
                image_url=show.image_url,
                icon=show.icon,
            )
            session.add(canonical)
        show.canonical_show = canonical


# TODO: Validate
def _points_somewhere_new(show: Show) -> bool:
    """Report whether the title `show` is chiefly of is one just written on it."""
    state = inspect(show)
    if state.pending or not state.persistent:
        return True
    return any(
        state.attrs[name].history.has_changes()
        for name in ("canonical_show", "canonical_show_id")
    )


# TODO: Validate
def _fill_show_links(session: SQLAlchemySession) -> None:
    """Give every copy in the session a link to the title it is chiefly of.

    The titles a copy stands for are held in one table so that a query asking
    which copies stand for a title has one place to ask, which only works while
    the chief title is in there like any other. `reconcile_show` adds the rest,
    once the seasons have said which further titles the copy turns out to mix.

    A stored copy is only looked at when the title it is chiefly of has just been
    written, since a copy whose title has not moved already has the link and
    reading its links back would cost a query per flush.
    """
    for show in [*session.new, *session.dirty]:
        if not isinstance(show, Show) or not _points_somewhere_new(show):
            continue
        canonical = show.canonical_show
        if canonical is None:
            continue
        if any(
            link.canonical_show is canonical
            or (canonical.id is not None and link.canonical_show_id == canonical.id)
            for link in show.canonical_show_links
        ):
            continue
        session.add(ShowCanonicalShow(show=show, canonical_show=canonical))


# TODO: Validate
def _fill_seasons(session: SQLAlchemySession) -> None:
    """Give every new season in the session the canonical row it is a copy of."""
    for season in session.new:
        if not isinstance(season, Season) or _already_pointed(
            season.canonical_season,
            season.canonical_season_id,
        ):
            continue
        parent = season.show.canonical_show if season.show else None
        plugin_key = _plugin_key(season.show) if season.show else None
        if parent is None or plugin_key is None:
            continue
        key = record_key(plugin_key, season.key)
        canonical = _pending_season(session, key, parent)
        if canonical is None:
            canonical = CanonicalSeason(
                key=key,
                canonical_show=parent,
                name=season.name,
                season_number=season.season_number,
                image_url=season.image_url,
                sort_order=season.sort_order,
            )
            session.add(canonical)
        season.canonical_season = canonical


# TODO: Validate
def _fill_episodes(session: SQLAlchemySession) -> None:
    """Give every new episode in the session the canonical row it is a copy of."""
    for episode in session.new:
        if not isinstance(episode, Episode) or _already_pointed(
            episode.canonical_episode,
            episode.canonical_episode_id,
        ):
            continue
        season = episode.season
        parent = season.canonical_season if season else None
        plugin_key = _plugin_key(season.show) if season and season.show else None
        if parent is None or plugin_key is None:
            continue
        key = record_key(plugin_key, episode.key)
        canonical = _pending_episode(session, key, parent)
        if canonical is None:
            canonical = CanonicalEpisode(
                key=key,
                canonical_season=parent,
                name=episode.name,
                description=episode.description,
                image_url=episode.image_url,
                episode_number=episode.episode_number,
                duration=episode.duration,
                release_date=episode.release_date,
                air_date=episode.air_date,
                sort_order=episode.sort_order,
            )
            session.add(canonical)
        episode.canonical_episode = canonical


# TODO: Validate
def _fill_pending(session: SQLAlchemySession) -> None:
    """Give every new copy in the session the canonical row it is a copy of.

    Walked parent-first so a season can be hung off the title's row and an
    episode off the season's, both of which may themselves have been created
    only moments ago in this same pass. A copy whose plugin cannot be read yet
    is skipped, since there is no key to make the row under; `reconcile_show`
    reaches it once the record is whole.
    """
    _fill_shows(session)
    _fill_show_links(session)
    _fill_seasons(session)
    _fill_episodes(session)


# TODO: Validate
def register_canonical_hooks() -> None:
    """Attach the flush hook to every session.

    Registered once, from `load_models`, so a session made anywhere gets it
    without having to know about it.
    """
    if event.contains(SQLAlchemySession, "before_flush", _before_flush):
        return
    event.listen(SQLAlchemySession, "before_flush", _before_flush)


# TODO: Validate
def _before_flush(session: SQLAlchemySession, _context, _instances) -> None:  # noqa: ANN001 - Signature fixed by SQLAlchemy.
    """Fill in the missing canonical rows, then let the flush proceed."""
    _fill_pending(session)
