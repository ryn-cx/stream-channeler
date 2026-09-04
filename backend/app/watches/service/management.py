# TODO: Validate
import uuid

from sqlmodel import Session, col, func, select

from app.canonical_media.episodes import (
    canonical_id_of,
)
from app.episodes.models import Episode
from app.media.service.deletion import delete_record
from app.schemas import Message
from app.watches.exceptions import WatchAlreadyExistsError
from app.watches.identifiers import (
    watches_of_canonical_ids,
)
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchRelinkResults,
    WatchUpdate,
)


# TODO: Validate
def create_watch(
    session: Session,
    user_id: uuid.UUID,
    episode: Episode,
    watch_input: WatchCreate,
) -> Watch:
    """Create a `Watch`.

    Raises:
        WatchAlreadyExistsError: If the `Episode` already has an unverified watch.

    """
    # A watch is recorded against the link that played it, so it is that link's
    # own identifier that is stored. What it counts for is worked out on the way
    # back out, where the identifier is read to the episode the link is of and
    # every other link to that episode counts too.
    canonical_id = canonical_id_of(episode)

    unverified_watch_query = watches_of_canonical_ids(user_id, [canonical_id]).where(
        col(Watch.verified) == False,  # noqa: E712 - SQLAlchemy syntax
    )
    if session.exec(unverified_watch_query).first():
        message = "Episode already has an unverified watch. Verify or delete it first."
        raise WatchAlreadyExistsError(message)

    watch = Watch.model_validate(
        watch_input,
        update={
            "episode_id": episode.id,
            "watch_identifier": episode.watch_identifier,
            "user_id": user_id,
        },
    )
    session.add(watch)
    session.commit()
    return watch


# TODO: Validate
def update_watch(
    session: Session,
    input_watch: Watch,
    watch_input: WatchUpdate,
) -> Watch:
    """Update a `Watch`."""
    return watch_input.update(session, input_watch)


# TODO: Validate
def delete_watches(session: Session, input_watch: Watch) -> Message:
    """Delete a `Watch`."""
    delete_record(session, input_watch)
    return Message(message="Watch deleted successfully")


# TODO: Validate
def relink_detached_watches(session: Session) -> WatchRelinkResults:
    """Point every watch left without an episode back at one.

    A watch names what it played rather than the row it was recorded against,
    so one whose episode has since been deleted is attached again as soon as
    another link to that episode exists. Where several do, the `User`'s own
    source order picks between them, exactly as playback would.
    """
    # `relink_watches` loads the models as it is imported, so it is imported
    # where it is used rather than alongside the models it maps.
    from app.tools.relink_watches import relink_watches  # noqa: PLC0415

    detached = session.exec(
        select(func.count()).select_from(Watch).where(col(Watch.episode_id).is_(None)),
    ).one()
    return WatchRelinkResults(detached=detached, relinked=relink_watches(session))
