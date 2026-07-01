# TODO: Validate
import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.snapshots.models import Snapshot, SnapshotEpisode
from app.users.models import User
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import CreatedUser, create_random_user
from tests.app.utils.utils import build_random_model


def create_random_snapshot(
    session: Session,
    user: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Snapshot:
    if user is None:
        user = create_random_user(session)
    if isinstance(user, (User, CreatedUser)):
        user = user.id
    snapshot = build_random_model(Snapshot, user_id=user, **kwargs)
    session.add(snapshot)
    session.flush()  # Allows snapshot.episodes to be accessed.
    return snapshot


def create_random_snapshot_episode(
    session: Session,
    snapshot: Snapshot,
    position: int,
    episode: Episode | None = None,
) -> SnapshotEpisode:
    if episode is None:
        episode = create_random_episode(session)
    entry = SnapshotEpisode(
        snapshot_id=snapshot.id,
        episode_id=episode.id,
        position=position,
    )
    session.add(entry)
    session.flush()
    return entry
