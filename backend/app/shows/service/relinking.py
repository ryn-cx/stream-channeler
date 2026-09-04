# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

from sqlmodel import Session

from app.episodes.linking import EpisodeLinker
from app.shows.models import Show


# TODO: Validate
def _reread_in_new_order(session: Session, show: Show) -> None:
    """Read `show` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    TMDB(session).update_show(show, force=True)


# TODO: Validate
def _relink_non_canonical_shows(session: Session, canonical_show: Show) -> None:
    """Match every non-canonical row of `canonical_show` against it again."""
    for link in list(canonical_show.non_canonical_shows):
        _relink_non_canonical_show(session, link.show)


# TODO: Validate
def _relink_non_canonical_show(
    session: Session,
    non_canonical_show: Show,
) -> None:
    for season in non_canonical_show.active_children:
        for episode in season.active_children:
            if episode.canonical_episode_validated_at is not None:
                continue
            for episode_link in list(episode.canonical_episode_links):
                session.delete(episode_link)
            episode.canonical_episode_note = None
        session.flush()
        for episode in season.active_children:
            session.expire(episode, ["canonical_episode_links", "is_canonical"])
    EpisodeLinker(session, non_canonical_show).link_show()


# TODO: Validate
def relink_show(session: Session, show: Show) -> Show:
    if show.is_canonical:
        _relink_non_canonical_shows(session, show)
    else:
        _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show
