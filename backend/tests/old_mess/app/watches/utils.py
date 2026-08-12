# TODO: Validate
import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import CreatedUser, create_random_user
from tests.app.utils.utils import build_random_model


# TODO: Validate
def create_random_watch(
    session: Session,
    parent: Episode
    | Season
    | Show
    | Source
    | Plugin
    | User
    | CreatedUser
    | uuid.UUID
    | None = None,
    *,
    watch_user: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Watch:
    if isinstance(parent, (User, CreatedUser, uuid.UUID)):
        if watch_user is None:
            watch_user = parent
        parent = None
    if isinstance(watch_user, (User, CreatedUser)):
        watch_user = watch_user.id
    if watch_user is None:
        watch_user = create_random_user(session).id
    if not isinstance(parent, Episode):
        parent = create_random_episode(session, parent or watch_user)
    watch = build_random_model(
        Watch,
        user_id=watch_user,
        episode_id=parent.id,
        **kwargs,
    )
    session.add(watch)
    session.flush()  # Allows watch.episode and watch.user to be accessed.
    return watch
