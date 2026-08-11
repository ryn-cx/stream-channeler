# TODO: Validate
"""Make sure nothing reaches the database without the media it is a copy of.

There is no free-floating state: a `Show`, `Season` or `Episode` is always a
copy of something, even when that something is only itself. The plugins build
their records and hand them to the session long before `reconcile_show` runs, so
this fills the gap at the last possible moment — the flush — and lets the
pointers be `NOT NULL`.

A row the TMDB linker already pointed somewhere is left exactly as it is. What
this catches is the ordinary case of a website's own record, which is a copy of
nothing but itself and so gets a row of its own.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session as SQLAlchemySession

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show


# TODO: Validate
def _fill_pending(session: SQLAlchemySession) -> None:
    """Give every new copy in the session the canonical row it is a copy of.

    Walked parent-first so a season can be hung off the title's row and an
    episode off the season's, both of which may themselves have been created
    only moments ago in this same pass.
    """
    for show in session.new:
        if isinstance(show, Show) and show.canonical_show_id is None:
            canonical = CanonicalShow(
                name=show.name,
                media_type=show.media_type,
                description=show.description,
                image_url=show.image_url,
                icon=show.icon,
            )
            session.add(canonical)
            show.canonical_show = canonical

    for season in session.new:
        if isinstance(season, Season) and season.canonical_season_id is None:
            parent = season.show.canonical_show if season.show else None
            if parent is None:
                continue
            canonical = CanonicalSeason(
                canonical_show=parent,
                name=season.name,
                season_number=season.season_number,
                image_url=season.image_url,
                sort_order=season.sort_order,
            )
            session.add(canonical)
            season.canonical_season = canonical

    for episode in session.new:
        if isinstance(episode, Episode) and episode.canonical_episode_id is None:
            parent = episode.season.canonical_season if episode.season else None
            if parent is None:
                continue
            canonical = CanonicalEpisode(
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
