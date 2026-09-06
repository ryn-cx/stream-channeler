# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

from sqlmodel import Session

from app.episodes.linking import EpisodeLinker
from app.titles.models import Title


# TODO: Validate
def _reread_in_new_order(session: Session, title: Title) -> None:
    """Read `title` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    TMDB(session).update_title(title, force=True)


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
    for season in non_canonical_title.active_children:
        for episode in season.active_children:
            if episode.canonical_episode_validated_at is not None:
                continue
            for episode_link in list(episode.canonical_episode_links):
                session.delete(episode_link)
        session.flush()
        for episode in season.active_children:
            session.expire(episode, ["canonical_episode_links", "is_canonical"])
    EpisodeLinker(session, non_canonical_title).link_title()


# TODO: Validate
def relink_title(session: Session, title: Title) -> Title:
    if title.is_canonical:
        _relink_non_canonical_titles(session, title)
    else:
        _relink_non_canonical_title(session, title)
    session.commit()
    session.refresh(title)
    return title
