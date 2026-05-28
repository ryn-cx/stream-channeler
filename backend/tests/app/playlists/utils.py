# TODO: Validate
import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.playlists.models import Playlist, PlaylistEpisode
from app.users.models import User
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import CreatedUser, create_random_user
from tests.app.utils.utils import build_random_model


def create_random_playlist(
    session: Session,
    user: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Playlist:
    if user is None:
        user = create_random_user(session)
    if isinstance(user, (User, CreatedUser)):
        user = user.id
    playlist = build_random_model(Playlist, user_id=user, **kwargs)
    session.add(playlist)
    session.flush()  # Allows playlist.episodes to be accessed.
    return playlist


def create_random_playlist_episode(
    session: Session,
    playlist: Playlist,
    position: int,
    episode: Episode | None = None,
) -> PlaylistEpisode:
    if episode is None:
        episode = create_random_episode(session)
    entry = PlaylistEpisode(
        playlist_id=playlist.id,
        episode_id=episode.id,
        position=position,
    )
    session.add(entry)
    session.flush()
    return entry
