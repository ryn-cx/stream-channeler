# TODO: Validate
import uuid

from sqlmodel import Session

from app.watches.models import Watch
from tests.episodes.utils import create_random_episode
from tests.users.utils import create_random_user
from tests.utils.utils import build_random_model


def create_random_watch(
    db: Session,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Watch:
    if user_id is None:
        user_id = create_random_user(db).id
    episode = create_random_episode(db, user_id=user_id)
    watch = build_random_model(Watch, user_id=user_id, episode_id=episode.id, **kwargs)
    db.add(watch)
    # Flush so watch.episode can be accessed.
    db.flush()
    return watch
