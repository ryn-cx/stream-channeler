# TODO: Validate
"""Give every copy of a title, season and episode the canonical row it is of.

A copy points at the row it is of. Where TMDB has a record, every copy naming
that record points at one shared row, which is what makes two websites' episodes
one episode to watch; where it does not, the copy is only ever itself and gets a
row of its own.

The TMDB plugin's linker is what points a copy at a shared row, and it does so
by the key the id TMDB issued spells out. Everything else falls to
`reconcile_show`, which gives a copy with no row of its own one to stand for it
and keeps it across re-imports.

The metadata on a canonical row is written by the copy entitled to write it: the
TMDB plugin writes the rows TMDB holds directly, and the single copy there is
writes the rest. A website's copy of a title TMDB holds never writes over it.
"""

import uuid
from collections.abc import Collection

from sqlmodel import Session, col, select, update

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_media.keys import (
    is_tmdb_key,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_show_key,
)
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.watches.models import Watch


# TODO: Validate
def canonical_show_by_key(session: Session, key: str) -> CanonicalShow:
    """Return the title `key` names, creating it if nothing claims it yet."""
    existing = session.exec(
        select(CanonicalShow).where(CanonicalShow.key == key),
    ).first()
    if existing:
        return existing
    canonical = CanonicalShow(key=key)
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def canonical_season_by_key(
    session: Session,
    key: str,
    canonical_show_id: uuid.UUID,
) -> CanonicalSeason:
    """Return the season `key` names, creating it if nothing claims it yet."""
    existing = session.exec(
        select(CanonicalSeason).where(
            CanonicalSeason.canonical_show_id == canonical_show_id,
            CanonicalSeason.key == key,
        ),
    ).first()
    if existing:
        return existing
    canonical = CanonicalSeason(key=key, canonical_show_id=canonical_show_id)
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def canonical_episode_by_key(
    session: Session,
    key: str,
    canonical_season_id: uuid.UUID,
) -> CanonicalEpisode:
    """Return the episode `key` names, creating it if nothing claims it yet."""
    existing = session.exec(
        select(CanonicalEpisode).where(
            CanonicalEpisode.canonical_season_id == canonical_season_id,
            CanonicalEpisode.key == key,
        ),
    ).first()
    if existing:
        return existing
    canonical = CanonicalEpisode(key=key, canonical_season_id=canonical_season_id)
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def canonical_show_for(
    session: Session,
    media_type: MediaType,
    tmdb_id: int,
) -> CanonicalShow:
    """Return the title TMDB holds under `tmdb_id`, creating it if needed."""
    return canonical_show_by_key(session, tmdb_show_key(media_type, tmdb_id))


# TODO: Validate
def canonical_season_for(
    session: Session,
    media_type: MediaType,
    tmdb_id: int,
    canonical_show_id: uuid.UUID,
) -> CanonicalSeason:
    """Return the season TMDB holds under `tmdb_id`, creating it if needed."""
    return canonical_season_by_key(
        session,
        tmdb_season_key(media_type, tmdb_id),
        canonical_show_id,
    )


# TODO: Validate
def canonical_episode_for(
    session: Session,
    media_type: MediaType,
    tmdb_id: int,
    canonical_season_id: uuid.UUID,
) -> CanonicalEpisode:
    """Return the episode TMDB holds under `tmdb_id`, creating it if needed."""
    return canonical_episode_by_key(
        session,
        tmdb_episode_key(media_type, tmdb_id),
        canonical_season_id,
    )


# TODO: Validate
def canonical_ids_by_key(
    session: Session,
    keys: Collection[str],
    level: type[Show | Season | Episode],
) -> dict[str, uuid.UUID]:
    """Map each record key in `keys` to the canonical row that record is of.

    For the places still handed a plugin's own keys from outside — a plugin says
    what a URL imported by the keys its records carry — where what has to be
    stored is the row those records are of.
    """
    if not keys:
        return {}
    canonical_column = {
        Show: Show.canonical_show_id,
        Season: Season.canonical_season_id,
        Episode: Episode.canonical_episode_id,
    }[level]
    rows = session.exec(
        select(level.key, canonical_column).where(  # type: ignore[call-overload]
            col(level.key).in_(keys),
            col(canonical_column).is_not(None),
        ),
    ).all()
    return dict(rows)


# TODO: Validate
def _record_key(plugin_key: str, record: Show | Season | Episode) -> str:
    """Return the key naming what `record` is a copy of.

    A plugin's own key for a record already names the thing itself rather than
    one listing of it — a YouTube episode is keyed by its video id, which is the
    same id wherever that video turns up — so namespacing it by the plugin is
    enough to make two copies of one work agree on a single row.
    """
    return f"{plugin_key} {record.key}"


# TODO: Validate
def _copy_show_metadata(show: Show, canonical: CanonicalShow) -> None:
    canonical.name = show.name
    canonical.url = show.url
    canonical.media_type = show.media_type
    canonical.description = show.description
    canonical.image_url = show.image_url
    canonical.icon = show.icon


# TODO: Validate
def _copy_season_metadata(season: Season, canonical: CanonicalSeason) -> None:
    canonical.name = season.name
    canonical.url = season.url
    canonical.season_number = season.season_number
    canonical.image_url = season.image_url
    canonical.sort_order = season.sort_order


# TODO: Validate
def _copy_episode_metadata(episode: Episode, canonical: CanonicalEpisode) -> None:
    # The copy's `url` is carried over as the episode's own page, which is
    # right while this is the only copy there is. A row TMDB holds keeps
    # themoviedb.org, since the guard above stops a website writing over it.
    canonical.name = episode.name
    canonical.url = episode.url
    canonical.description = episode.description
    canonical.image_url = episode.image_url
    canonical.episode_number = episode.episode_number
    canonical.duration = episode.duration
    canonical.release_date = episode.release_date
    canonical.air_date = episode.air_date
    canonical.sort_order = episode.sort_order


# TODO: Validate
def standalone_show(
    session: Session,
    show: Show,
    key: str | None = None,
) -> CanonicalShow:
    """Return the row the title `show` is a copy of, creating it if needed.

    A row the linker already pointed it at is kept, so what is recorded against
    a title survives it being imported again. Otherwise `key` is what says which
    title this is, and every copy claiming that key converges on one row.
    """
    if show.canonical_show_id:
        kept = session.get(CanonicalShow, show.canonical_show_id)
        # A row somebody has claimed — by key, or by being TMDB's — is the
        # answer. One the flush hook minted to satisfy the pointer has claimed
        # nothing, so it gives way to the key naming what this really is.
        if kept and (kept.key or not key):
            return kept
    if key:
        return canonical_show_by_key(session, key)
    canonical = CanonicalShow()
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def standalone_season(
    session: Session,
    season: Season,
    canonical_show: CanonicalShow,
    key: str | None = None,
) -> CanonicalSeason:
    """Return the row the season `season` is a copy of, creating it if needed."""
    if season.canonical_season_id:
        kept = session.get(CanonicalSeason, season.canonical_season_id)
        if kept and (kept.key or not key):
            if not is_tmdb_key(kept.key):
                kept.canonical_show_id = canonical_show.id
            return kept
    if key:
        return canonical_season_by_key(session, key, canonical_show.id)
    canonical = CanonicalSeason(canonical_show_id=canonical_show.id)
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def standalone_episode(
    session: Session,
    episode: Episode,
    canonical_season: CanonicalSeason,
    key: str | None = None,
) -> CanonicalEpisode:
    """Return the row the episode `episode` is a copy of, creating it if needed.

    This is what draws two copies of one video together: the same key from the
    channel's uploads and from one of its playlists is one episode to watch,
    where before each copy invented a row of its own.
    """
    if episode.canonical_episode_id:
        kept = session.get(CanonicalEpisode, episode.canonical_episode_id)
        if kept and (kept.key or not key):
            if not is_tmdb_key(kept.key):
                kept.canonical_season_id = canonical_season.id
            return kept
    if key:
        return canonical_episode_by_key(session, key, canonical_season.id)
    canonical = CanonicalEpisode(canonical_season_id=canonical_season.id)
    session.add(canonical)
    session.flush()
    return canonical


# TODO: Validate
def _repoint_watches(
    session: Session,
    episode: Episode,
    canonical: CanonicalEpisode,
) -> None:
    """Move the watches of `episode` onto the canonical episode it is now of.

    A watch is of whatever the copy it was recorded against turns out to be of,
    so settling a match by hand carries the watch history over with it rather
    than leaving it against the row the copy has moved off.
    """
    if canonical.key is None:
        return
    session.execute(
        update(Watch)
        .where(
            col(Watch.episode_id) == episode.id,
            col(Watch.canonical_episode_key).is_distinct_from(canonical.key),
        )
        .values(canonical_episode_key=canonical.key),
    )


# TODO: Validate
def _is_watched(session: Session, canonical_episode_keys: Collection[str]) -> bool:
    """Whether any watch is recorded against one of these keys."""
    if not canonical_episode_keys:
        return False
    return (
        session.exec(
            select(Watch.id).where(
                col(Watch.canonical_episode_key).in_(canonical_episode_keys),
            ),
        ).first()
        is not None
    )


# TODO: Validate
def _episode_keys_under_season(
    session: Session,
    canonical_season_id: uuid.UUID,
) -> list[str]:
    return list(
        session.exec(
            select(CanonicalEpisode.key).where(  # type: ignore[arg-type]
                CanonicalEpisode.canonical_season_id == canonical_season_id,
                col(CanonicalEpisode.key).is_not(None),
            ),
        ).all(),
    )


# TODO: Validate
def _episode_keys_under_show(
    session: Session,
    canonical_show_id: uuid.UUID,
) -> list[str]:
    return list(
        session.exec(
            select(CanonicalEpisode.key)  # type: ignore[arg-type]
            .join(
                CanonicalSeason,
                col(CanonicalSeason.id) == col(CanonicalEpisode.canonical_season_id),
            )
            .where(
                CanonicalSeason.canonical_show_id == canonical_show_id,
                col(CanonicalEpisode.key).is_not(None),
            ),
        ).all(),
    )


# TODO: Validate
def discard_if_unused(session: Session, canonical_id: uuid.UUID) -> None:
    """Delete a canonical episode nothing is of any more.

    A row left behind by a copy moving to another is one nothing can reach, and
    it is dropped rather than kept as media that exists nowhere. A row that
    still has a copy pointing at it, or a watch recorded against it, is left
    alone - watch history is the reason a canonical row outlives its copies.
    """
    still_used = session.exec(
        select(Episode.id).where(Episode.canonical_episode_id == canonical_id),
    ).first()
    if still_used:
        return
    abandoned = session.get(CanonicalEpisode, canonical_id)
    if abandoned is None or is_tmdb_key(abandoned.key):
        return
    if abandoned.key and _is_watched(session, [abandoned.key]):
        return
    session.delete(abandoned)


# TODO: Validate
def _discard_show_if_unused(session: Session, canonical_id: uuid.UUID) -> None:
    """Delete a canonical title no copy is of any more, and its seasons with it.

    Only ever an unclaimed row: one the flush hook minted to satisfy a pointer
    and that the key then moved the copy off. A title anybody claimed is left
    alone, and so is one whose cascade would take an episode somebody watched.
    """
    abandoned = session.get(CanonicalShow, canonical_id)
    if abandoned is None or abandoned.key:
        return
    still_used = session.exec(
        select(Show.id).where(Show.canonical_show_id == canonical_id),
    ).first()
    if still_used is not None:
        return
    if _is_watched(session, _episode_keys_under_show(session, canonical_id)):
        return
    session.delete(abandoned)


# TODO: Validate
def _discard_season_if_unused(session: Session, canonical_id: uuid.UUID) -> None:
    """Delete a canonical season no copy is of any more, if nobody claimed it."""
    abandoned = session.get(CanonicalSeason, canonical_id)
    if abandoned is None or abandoned.key:
        return
    still_used = session.exec(
        select(Season.id).where(Season.canonical_season_id == canonical_id),
    ).first()
    if still_used is not None:
        return
    if _is_watched(session, _episode_keys_under_season(session, canonical_id)):
        return
    session.delete(abandoned)


# TODO: Validate
def point_episode_at(
    session: Session,
    episode: Episode,
    canonical: CanonicalEpisode,
) -> None:
    """Point `episode` at `canonical`, carrying its watches and metadata over.

    Used where a link changes outside an import, which is to say where a `User`
    settles a match by hand. The row the episode was of is discarded when moving
    off it leaves nothing pointing at it.
    """
    previous_id = episode.canonical_episode_id
    if canonical.id == previous_id:
        return

    episode.canonical_episode = canonical
    if not is_tmdb_key(canonical.key):
        _copy_episode_metadata(episode, canonical)
    session.add(episode)
    session.flush()

    _repoint_watches(session, episode, canonical)
    if previous_id:
        discard_if_unused(session, previous_id)


# TODO: Validate
def _discard_abandoned(
    session: Session,
    *,
    kept_show_id: uuid.UUID,
    shows: set[uuid.UUID],
    seasons: set[uuid.UUID],
    episodes: set[uuid.UUID],
) -> None:
    """Drop the rows the keys moved every copy off, deepest level first.

    Only ever rows nobody claimed: ones the flush hook minted to satisfy a
    pointer before `reconcile_show` worked out what the record really is of.
    """
    session.flush()
    for canonical_id in episodes:
        discard_if_unused(session, canonical_id)
    session.flush()

    # Titles first, so a season the cascade takes is already gone by the time
    # its own turn comes; a title a watch holds is not, and its seasons are then
    # weighed one at a time like any other.
    for canonical_id in shows:
        if canonical_id != kept_show_id:
            _discard_show_if_unused(session, canonical_id)
    session.flush()

    for canonical_id in seasons:
        if session.get(CanonicalSeason, canonical_id) is not None:
            _discard_season_if_unused(session, canonical_id)
    session.flush()


# TODO: Validate
def reconcile_show(session: Session, show: Show, plugin_key: str) -> None:
    """Give `show` and everything under it the canonical rows they are of.

    A copy the TMDB linker pointed at a shared row keeps it; anything else is
    only ever itself and is given a row of its own. `plugin_key` says whose copy
    this is, which is what decides whether it may write the metadata: a row TMDB
    holds is described by TMDB itself, and every other copy of it only points at
    the row.
    """
    from app.media.identifiers import (
        TMDB_PLUGIN_KEY,
    )

    previous_show_id = show.canonical_show_id
    canonical_show = standalone_show(session, show, _record_key(plugin_key, show))
    show.canonical_show = canonical_show
    if not is_tmdb_key(canonical_show.key) or plugin_key == TMDB_PLUGIN_KEY:
        _copy_show_metadata(show, canonical_show)

    # Gathered rather than dropped as they are found: a row is only spare once
    # every copy has moved, and a later season or episode may still be pointing
    # at one an earlier move left looking unused.
    abandoned_shows = {previous_show_id} if previous_show_id else set()
    abandoned_seasons: set[uuid.UUID] = set()
    abandoned_episodes: set[uuid.UUID] = set()

    for season in show.seasons:
        previous_season_id = season.canonical_season_id
        canonical_season = standalone_season(
            session,
            season,
            canonical_show,
            _record_key(plugin_key, season),
        )
        season.canonical_season = canonical_season
        if not is_tmdb_key(canonical_season.key) or plugin_key == TMDB_PLUGIN_KEY:
            _copy_season_metadata(season, canonical_season)
        if previous_season_id and previous_season_id != canonical_season.id:
            abandoned_seasons.add(previous_season_id)

        for episode in season.episodes:
            previous_id = episode.canonical_episode_id
            canonical_episode = standalone_episode(
                session,
                episode,
                canonical_season,
                _record_key(plugin_key, episode),
            )
            episode.canonical_episode = canonical_episode
            if not is_tmdb_key(canonical_episode.key) or plugin_key == TMDB_PLUGIN_KEY:
                _copy_episode_metadata(episode, canonical_episode)
            if previous_id != canonical_episode.id:
                session.flush()
                _repoint_watches(session, episode, canonical_episode)
                if previous_id:
                    abandoned_episodes.add(previous_id)

    _discard_abandoned(
        session,
        kept_show_id=canonical_show.id,
        shows=abandoned_shows,
        seasons=abandoned_seasons,
        episodes=abandoned_episodes,
    )
