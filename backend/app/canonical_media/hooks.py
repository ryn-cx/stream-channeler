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
from sqlmodel import col, select

from app.canonical_media.keys import record_key
from app.episodes.models import CanonicalEpisode, Episode
from app.seasons.models import CanonicalSeason, Season
from app.shows.models import CanonicalShow, Show, ShowCanonicalShow


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
def _pending_shows(session: SQLAlchemySession) -> dict[str, CanonicalShow]:
    """Return every title the session is about to write, by its key."""
    return {
        pending.key: pending
        for pending in session.new
        if isinstance(pending, CanonicalShow)
    }


# TODO: Validate
def _pending_seasons(
    session: SQLAlchemySession,
) -> dict[tuple[uuid.UUID, str], CanonicalSeason]:
    """Return every season the session is about to write, by title and key.

    The title is read off the row a pending season was handed rather than its
    id, since the id is only written on it by the flush this runs ahead of.
    """
    pending_seasons: dict[tuple[uuid.UUID, str], CanonicalSeason] = {}
    for pending in session.new:
        if not isinstance(pending, CanonicalSeason):
            continue
        canonical_show = pending.canonical_show
        parent_id = canonical_show.id if canonical_show else pending.canonical_show_id
        if parent_id is not None:
            pending_seasons[(parent_id, pending.key)] = pending
    return pending_seasons


# TODO: Validate
def _pending_episodes(
    session: SQLAlchemySession,
) -> dict[tuple[uuid.UUID, str], CanonicalEpisode]:
    """Return every episode the session is about to write, by season and key."""
    pending_episodes: dict[tuple[uuid.UUID, str], CanonicalEpisode] = {}
    for pending in session.new:
        if not isinstance(pending, CanonicalEpisode):
            continue
        canonical_season = pending.canonical_season
        parent_id = (
            canonical_season.id if canonical_season else pending.canonical_season_id
        )
        if parent_id is not None:
            pending_episodes[(parent_id, pending.key)] = pending
    return pending_episodes


# TODO: Validate
def _fill_shows(session: SQLAlchemySession) -> None:
    """Give every new title in the session the canonical row it is a copy of."""
    wanted: list[tuple[Show, str]] = []
    for show in session.new:
        if not isinstance(show, Show) or _already_pointed(
            show.canonical_show,
            show.canonical_show_id,
        ):
            continue
        plugin_key = _plugin_key(show)
        if plugin_key is None:
            continue
        wanted.append((show, record_key(plugin_key, show.key)))

    if not wanted:
        return

    # Every key is asked for at once. A flush carries a whole import's worth of
    # copies, and a lookup per copy is a query per copy, every flush.
    by_key = _pending_shows(session)
    missing_keys = {key for _show, key in wanted} - set(by_key)
    if missing_keys:
        stored = session.scalars(
            select(CanonicalShow).where(col(CanonicalShow.key).in_(missing_keys)),
        ).all()
        by_key.update({canonical.key: canonical for canonical in stored})

    for show, key in wanted:
        canonical = by_key.get(key)
        if canonical is None:
            canonical = CanonicalShow(
                key=key,
                name=show.name,
                media_type=show.media_type,
                description=show.description,
                image_url=show.image_url,
            )
            session.add(canonical)
            by_key[key] = canonical
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
    wanted: list[tuple[Season, str, CanonicalShow]] = []
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
        wanted.append((season, record_key(plugin_key, season.key), parent))

    if not wanted:
        return

    by_key = _pending_seasons(session)
    missing = [
        (parent.id, key)
        for _season, key, parent in wanted
        if (parent.id, key) not in by_key
    ]
    if missing:
        # Both halves of the key are matched loosely and the pair is picked out
        # of what comes back, so the whole flush costs one query.
        stored = session.scalars(
            select(CanonicalSeason).where(
                col(CanonicalSeason.canonical_show_id).in_(
                    {parent_id for parent_id, _key in missing},
                ),
                col(CanonicalSeason.key).in_({key for _parent_id, key in missing}),
            ),
        ).all()
        for stored_canonical in stored:
            by_key.setdefault(
                (stored_canonical.canonical_show_id, stored_canonical.key),
                stored_canonical,
            )

    for season, key, parent in wanted:
        canonical: CanonicalSeason | None = by_key.get((parent.id, key))
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
            by_key[(parent.id, key)] = canonical
        season.canonical_season = canonical


# TODO: Validate
def _fill_episodes(session: SQLAlchemySession) -> None:
    """Give every new episode in the session the canonical row it is a copy of."""
    wanted: list[tuple[Episode, str, CanonicalSeason]] = []
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
        wanted.append((episode, record_key(plugin_key, episode.key), parent))

    if not wanted:
        return

    by_key = _pending_episodes(session)
    missing = [
        (parent.id, key)
        for _episode, key, parent in wanted
        if (parent.id, key) not in by_key
    ]
    if missing:
        stored = session.scalars(
            select(CanonicalEpisode).where(
                col(CanonicalEpisode.canonical_season_id).in_(
                    {parent_id for parent_id, _key in missing},
                ),
                col(CanonicalEpisode.key).in_({key for _parent_id, key in missing}),
            ),
        ).all()
        for stored_canonical in stored:
            by_key.setdefault(
                (stored_canonical.canonical_season_id, stored_canonical.key),
                stored_canonical,
            )

    for episode, key, parent in wanted:
        canonical: CanonicalEpisode | None = by_key.get((parent.id, key))
        if canonical is None:
            canonical = CanonicalEpisode(
                key=key,
                canonical_season=parent,
                name=episode.name,
                description=episode.description,
                image_url=episode.image_url,
                episode_number=episode.episode_number,
                duration=episode.duration,
                air_date=episode.air_date,
                sort_order=episode.sort_order,
            )
            session.add(canonical)
            by_key[(parent.id, key)] = canonical
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
