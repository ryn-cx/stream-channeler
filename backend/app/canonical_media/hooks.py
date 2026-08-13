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

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import record_key
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow, index_show


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
def _is_title(show: Show) -> bool:
    """Report whether `show` is a title rather than a website's listing of one.

    Told by the source rather than by the copy pointer, which is the thing this
    module is here to fill in: until it has run, a listing points at nothing
    just as a title does. A title is on no website, and that is true of it from
    the moment it is built.
    """
    return show.source is None and show.source_id is None


# TODO: Validate
def _is_canonical_season(season: Season) -> bool:
    """Report whether `season` is a season rather than a copy of one."""
    return season.show is not None and _is_title(season.show)


# TODO: Validate
def _is_canonical_episode(episode: Episode) -> bool:
    """Report whether `episode` is an episode rather than a copy of one."""
    return episode.season is not None and _is_canonical_season(episode.season)


# TODO: Validate
def _pending_shows(session: SQLAlchemySession) -> dict[str, Show]:
    """Return every title the session is about to write, by its key."""
    return {
        pending.key: pending
        for pending in session.new
        if isinstance(pending, Show) and _is_title(pending)
    }


# TODO: Validate
def _pending_seasons(
    session: SQLAlchemySession,
) -> dict[tuple[uuid.UUID, str], Season]:
    """Return every season the session is about to write, by title and key.

    The title is read off the row a pending season was handed rather than its
    id, since the id is only written on it by the flush this runs ahead of.
    """
    pending_seasons: dict[tuple[uuid.UUID, str], Season] = {}
    for pending in session.new:
        if not isinstance(pending, Season) or not _is_canonical_season(pending):
            continue
        show = pending.show
        parent_id = show.id if show else pending.show_id
        if parent_id is not None:
            pending_seasons[(parent_id, pending.key)] = pending
    return pending_seasons


# TODO: Validate
def _pending_episodes(
    session: SQLAlchemySession,
) -> dict[tuple[uuid.UUID, str], Episode]:
    """Return every episode the session is about to write, by season and key."""
    pending_episodes: dict[tuple[uuid.UUID, str], Episode] = {}
    for pending in session.new:
        if not isinstance(pending, Episode) or not _is_canonical_episode(pending):
            continue
        season = pending.season
        parent_id = season.id if season else pending.season_id
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
            select(Show).where(is_canonical(Show), col(Show.key).in_(missing_keys)),
        ).all()
        by_key.update({canonical.key: canonical for canonical in stored})

    for show, key in wanted:
        canonical = by_key.get(key)
        if canonical is None:
            canonical = Show(
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
    wanted: list[tuple[Season, str, Show]] = []
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
            select(Season).where(
                is_canonical(Season),
                col(Season.show_id).in_(
                    {parent_id for parent_id, _key in missing},
                ),
                col(Season.key).in_({key for _parent_id, key in missing}),
            ),
        ).all()
        for stored_canonical in stored:
            by_key.setdefault(
                (stored_canonical.show_id, stored_canonical.key),
                stored_canonical,
            )

    for season, key, parent in wanted:
        canonical: Season | None = by_key.get((parent.id, key))
        if canonical is None:
            canonical = Season(
                key=key,
                show=parent,
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
    wanted: list[tuple[Episode, str, Season]] = []
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
            select(Episode).where(
                is_canonical(Episode),
                col(Episode.season_id).in_(
                    {parent_id for parent_id, _key in missing},
                ),
                col(Episode.key).in_({key for _parent_id, key in missing}),
            ),
        ).all()
        for stored_canonical in stored:
            by_key.setdefault(
                (stored_canonical.season_id, stored_canonical.key),
                stored_canonical,
            )

    for episode, key, parent in wanted:
        canonical: Episode | None = by_key.get((parent.id, key))
        if canonical is None:
            canonical = Episode(
                key=key,
                season=parent,
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
    """Attach the flush hook and the listing index to every session.

    Registered once, from `load_models`, so a session made anywhere gets them
    without having to know about them.
    """
    if event.contains(SQLAlchemySession, "before_flush", _before_flush):
        return
    event.listen(SQLAlchemySession, "before_flush", _before_flush)
    # Both ends of how a session comes to hold a listing: one it was handed and
    # one it read in. A listing is looked up by its source and key on the import
    # hot path, and that pair stopped naming a row in the identity map when a
    # title and a listing became one table.
    event.listen(SQLAlchemySession, "after_attach", _index_attached)
    event.listen(SQLAlchemySession, "loaded_as_persistent", _index_attached)


# TODO: Validate
def _index_attached(session: SQLAlchemySession, instance: object) -> None:
    """Put a listing the session has taken hold of into its index."""
    if isinstance(instance, Show):
        index_show(session, instance)


# TODO: Validate
def _before_flush(session: SQLAlchemySession, _context, _instances) -> None:  # noqa: ANN001 - Signature fixed by SQLAlchemy.
    """Fill in the missing canonical rows, then let the flush proceed."""
    _fill_pending(session)
