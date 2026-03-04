import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.watches.models import Watch
from app.watches.schemas import WatchInput
from tests.episodes.utils import create_random_episode
from tests.utils.utils import build_random_model


def create_random_watch(
    db: Session,
    user_id: uuid.UUID,
    episode: Episode | None = None,
) -> Watch:
    if episode is None:
        episode = create_random_episode(db)

    watch_input = build_random_model(WatchInput, user_id=user_id)
    watch = watch_input.upsert(episode, None)
    db.commit()
    return watch
