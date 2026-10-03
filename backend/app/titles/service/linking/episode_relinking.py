# TODO: Validate

from sqlmodel import Session, col, delete, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.service.linking import (
    EpisodeLinker,
    load_title_episodes,
    title_episodes,
)
from app.plugins.identifiers import TMDB_VIDEOS_SOURCE_KEY
from app.seasons.models import Season
from app.titles.models import Title


# TODO: Validate
def _old_relink_episodes(session: Session, tmdb_title: Title) -> None:
    for link in list(tmdb_title.linked_title_links):
        if link.linked_title.source.key != TMDB_VIDEOS_SOURCE_KEY:
            _relink_episode(session, link.linked_title)


# TODO: Validate
def _relink_episode(session: Session, linked_title: Title) -> None:
    loaded_title = load_title_episodes(session, linked_title)
    EpisodeLinker(session, loaded_title).relink_titles()


# TODO: Validate
def _old_unlink_episodes_from_dropped_tmdb_titles(
    session: Session,
    website_title: Title,
) -> None:
    episodes = title_episodes(load_title_episodes(session, website_title))
    if not episodes:
        return

    tmdb_title_ids = {tmdb_title.id for tmdb_title in website_title.tmdb_titles}
    episode_ids = [episode.id for episode in episodes]
    kept_tmdb_episode_ids = (
        select(col(Episode.id))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .where(col(Season.title_id).in_(tmdb_title_ids))
    )
    unlinked_episode_ids = set(
        session.exec(
            select(col(EpisodeTmdbEpisode.episode_id)).where(
                col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
                col(EpisodeTmdbEpisode.tmdb_episode_id).not_in(kept_tmdb_episode_ids),
            ),
        ).all(),
    )
    session.exec(
        delete(EpisodeTmdbEpisode)
        .where(
            col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
            col(EpisodeTmdbEpisode.tmdb_episode_id).not_in(kept_tmdb_episode_ids),
        )
        .execution_options(synchronize_session=False),
    )
    still_linked_episode_ids = set(
        session.exec(
            select(col(EpisodeTmdbEpisode.episode_id)).where(
                col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
            ),
        ).all(),
    )
    for episode in episodes:
        session.expire(episode, ["tmdb_episode_links", "is_linked"])
        if (
            episode.id in unlinked_episode_ids
            and episode.id not in still_linked_episode_ids
            and episode.tmdb_episode_validated_at is not None
        ):
            episode.tmdb_episode_validated_at = None
            session.add(episode)
    session.flush()
