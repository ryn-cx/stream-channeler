# TODO: Validate
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.playlists.dependencies import OwnedPlaylist, ReadablePlaylist
from app.playlists.models import Playlist, PlaylistEpisode
from app.playlists.schemas import (
    PlaylistCreate,
    PlaylistDetailOutput,
    PlaylistEpisodesOutput,
    PlaylistEpisodeWithExtrasOutput,
    PlaylistOutput,
    PlaylistUpdate,
)
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.watches.models import Watch

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistOutput])
def get_playlists(current_user: CurrentUser) -> list[Playlist]:
    """List all `Playlist`s owned by the current `User`."""
    return current_user.playlists


# FAST003 - Parameter is used by ReadablePlaylist.
@router.get("/{playlist_id}", response_model=PlaylistDetailOutput)  # noqa: FAST003
def get_playlist(playlist: ReadablePlaylist) -> Playlist:
    """Get a `Playlist` with its ordered episode list."""
    return playlist


# FAST003 - Parameter is used by ReadablePlaylist.
@router.get("/{playlist_id}/episodes")  # noqa: FAST003
def get_playlist_episodes(
    session: SessionDep,
    playlist: ReadablePlaylist,
    user: OptionalUser,
) -> PlaylistEpisodesOutput:
    """Read the episodes for a playlist with hydrated season/show/source/plugin data."""
    output = PlaylistEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
    )

    # Look up the most recent watch per episode for the current viewer (if any).
    latest_watches: dict[uuid.UUID, Watch] = {}
    if user and playlist.episodes:
        episode_ids = [entry.episode_id for entry in playlist.episodes]
        watches = session.exec(
            select(Watch)
            .where(Watch.user_id == user.id)
            .where(col(Watch.episode_id).in_(episode_ids))
            .order_by(col(Watch.watch_date).desc()),
        ).all()
        for watch in watches:
            if watch.episode_id not in latest_watches:
                latest_watches[watch.episode_id] = watch

    for entry in playlist.episodes:
        episode = entry.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        extras: dict[str, Any] = {"position": entry.position}
        latest_watch = latest_watches.get(episode.id)
        if latest_watch:
            extras["watch_date"] = latest_watch.watch_date
            extras["verified"] = latest_watch.verified
            extras["episode_watch_id"] = latest_watch.id

        output.episodes.append(
            PlaylistEpisodeWithExtrasOutput(
                **episode.model_dump(),
                **extras,
            ),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    return output


@router.post("", response_model=PlaylistDetailOutput)
def create_playlist(
    session: SessionDep,
    current_user: CurrentUser,
    playlist_in: PlaylistCreate,
) -> Playlist:
    """Create a `Playlist` with all of its episodes in one shot.

    The order of `episode_ids` defines the saved order. After creation the
    episode list cannot be modified — to change it, create a new playlist.
    """
    episode_ids = playlist_in.episode_ids
    if episode_ids:
        existing = set(
            session.exec(
                select(Episode.id).where(col(Episode.id).in_(episode_ids)),
            ).all(),
        )
        missing = [str(eid) for eid in episode_ids if eid not in existing]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown episode ids: {missing}",
            )

    playlist = Playlist(
        name=playlist_in.name,
        visibility=playlist_in.visibility,
        user_id=current_user.id,
    )
    session.add(playlist)
    session.flush()

    for position, episode_id in enumerate(episode_ids):
        session.add(
            PlaylistEpisode(
                playlist_id=playlist.id,
                episode_id=episode_id,
                position=position,
            ),
        )

    session.commit()
    session.refresh(playlist)
    return playlist


# FAST003 - Parameter is used by OwnedPlaylist.
@router.patch("/{playlist_id}", response_model=PlaylistDetailOutput)  # noqa: FAST003
def update_playlist(
    session: SessionDep,
    playlist: OwnedPlaylist,
    playlist_in: PlaylistUpdate,
) -> Playlist:
    """Update a `Playlist`'s metadata and optionally replace its episodes.

    Individual `PlaylistEpisode` rows are never modified in place — when
    `episode_ids` is supplied, every existing entry is deleted and a fresh
    ordered set is inserted in one transaction.
    """
    metadata = playlist_in.model_dump(
        exclude_unset=True,
        exclude={"episode_ids"},
    )
    if metadata:
        playlist.sqlmodel_update(metadata)

    if "episode_ids" in playlist_in.model_fields_set:
        episode_ids = playlist_in.episode_ids or []
        if episode_ids:
            existing = set(
                session.exec(
                    select(Episode.id).where(col(Episode.id).in_(episode_ids)),
                ).all(),
            )
            missing = [str(eid) for eid in episode_ids if eid not in existing]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown episode ids: {missing}",
                )

        for entry in list(playlist.episodes):
            session.delete(entry)
        session.flush()
        for position, episode_id in enumerate(episode_ids):
            session.add(
                PlaylistEpisode(
                    playlist_id=playlist.id,
                    episode_id=episode_id,
                    position=position,
                ),
            )

    session.commit()
    session.refresh(playlist)
    return playlist


# FAST003 - Parameter is used by OwnedPlaylist.
@router.delete("/{playlist_id}")  # noqa: FAST003
def delete_playlist(session: SessionDep, playlist: OwnedPlaylist) -> Message:
    """Delete a `Playlist` owned by the current `User`."""
    session.delete(playlist)
    session.commit()
    return Message(message="Playlist deleted successfully")
