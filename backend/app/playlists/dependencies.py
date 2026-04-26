# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_owned_record, get_readable_record
from app.playlists.models import Playlist
from app.users.dependencies import OptionalUser


def require_owned_playlist(
    session: SessionDep,
    current_user: CurrentUser,
    playlist_id: Annotated[uuid.UUID, Path()],
) -> Playlist:
    """Return a playlist if it exists and belongs to the current user."""
    return get_owned_record(session, Playlist, playlist_id, current_user.id)


def require_readable_playlist(
    session: SessionDep,
    optional_user: OptionalUser,
    playlist_id: uuid.UUID,
) -> Playlist:
    """Return a playlist if it exists and is readable by the current user."""
    return get_readable_record(session, Playlist, playlist_id, optional_user)


OwnedPlaylist = Annotated[Playlist, Depends(require_owned_playlist)]
ReadablePlaylist = Annotated[Playlist, Depends(require_readable_playlist)]
