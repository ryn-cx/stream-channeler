# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

from collections.abc import Sequence

from loguru import logger
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, delete, select

from app.episodes.linking import EpisodeLinker
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.episodes.preload import preload_episodes
from app.titles.models import Title


# TODO: Validate
def _reread_in_new_order(session: Session, title: Title) -> None:
    """Read `title` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    logger.info(f"Rereading title in a new order: {title.name or title.key}")
    TMDB(session).update_title(title, force=True)


# TODO: Validate
def _relinkable_episodes(session: Session, title: Title) -> list[Episode]:
    preload_episodes(session, [title])
    return [
        episode
        for season in title.active_children
        for episode in season.active_children
        if episode.canonical_episode_validated_at is None
    ]


# TODO: Validate
def _preload_canonical_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    unread = [
        episode.id
        for episode in episodes
        if "canonical_episode_links" in instance_state(episode).unloaded
    ]
    if not unread:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(unread))
        .options(
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
def _clear_canonical_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    _preload_canonical_episode_links(session, episodes)
    links = [link for episode in episodes for link in episode.canonical_episode_links]
    if not links:
        return

    session.exec(
        delete(EpisodeCanonicalEpisode).where(
            col(EpisodeCanonicalEpisode.episode_id).in_(
                [episode.id for episode in episodes],
            ),
        ),
    )
    for link in links:
        if link in session:
            session.expunge(link)
    for episode in episodes:
        set_committed_value(episode, "canonical_episode_links", [])


# TODO: Validate
def _relink_non_canonical_titles(session: Session, canonical_title: Title) -> None:
    """Match every non-canonical row of `canonical_title` against it again."""
    for link in list(canonical_title.non_canonical_title_links):
        _relink_non_canonical_title(session, link.non_canonical_title)


# TODO: Validate
def _relink_non_canonical_title(
    session: Session,
    non_canonical_title: Title,
) -> None:
    _clear_canonical_episode_links(
        session,
        _relinkable_episodes(session, non_canonical_title),
    )
    linker = EpisodeLinker(session, non_canonical_title)
    with session.no_autoflush:
        linker.link_title()


# TODO: Validate
def relink_title(session: Session, title: Title) -> Title:
    if title.is_canonical:
        _relink_non_canonical_titles(session, title)
    else:
        _relink_non_canonical_title(session, title)
    session.commit()
    session.refresh(title)
    return title
