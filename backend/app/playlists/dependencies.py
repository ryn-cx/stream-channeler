# TODO: Validate
"""Playlist dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record, readable_record
from app.playlists.models import Playlist

OwnedPlaylist = Annotated[Playlist, Depends(owned_record(Playlist, "playlist_id"))]
ReadablePlaylist = Annotated[
    Playlist,
    Depends(readable_record(Playlist, "playlist_id")),
]
