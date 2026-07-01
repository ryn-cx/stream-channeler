# TODO: Validate
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import col, func, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.service import delete_record
from app.models import Visibility
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.snapshots import service
from app.snapshots.dependencies import (
    EditableSnapshot,
    ExistingSnapshot,
    ReadableSnapshot,
)
from app.snapshots.models import Snapshot
from app.snapshots.schemas import (
    SnapshotAdminOutput,
    SnapshotAdminUpdate,
    SnapshotCreate,
    SnapshotDetailOutput,
    SnapshotEpisodesOutput,
    SnapshotEpisodeWithExtrasOutput,
    SnapshotPublicListOutput,
    SnapshotUpdate,
)
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.watches.models import Watch

snapshots_router = APIRouter(prefix="/snapshots", tags=["snapshots"])
admin_router = APIRouter(
    prefix="/admin/snapshots",
    tags=["snapshots"],
    dependencies=[Depends(get_current_active_superuser)],
)


@snapshots_router.post("", response_model=SnapshotDetailOutput)
def create_snapshot(
    session: SessionDep,
    current_user: CurrentUser,
    snapshot_input: SnapshotCreate,
) -> Snapshot:
    """Create a `Snapshot` with all of its episodes in one shot."""
    snapshot = Snapshot(
        name=snapshot_input.name,
        visibility=snapshot_input.visibility,
        anonymous=snapshot_input.anonymous,
        user_id=current_user.id,
    )
    service.set_snapshot_episodes(session, snapshot, snapshot_input.episode_ids)
    session.add(snapshot)
    session.commit()
    return snapshot


@snapshots_router.get("")
def get_snapshots(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[SnapshotAdminOutput]:
    """Get all of the `Snapshot`s editable by the `User`."""
    rows = session.exec(
        select(Snapshot, User.username)
        .join(User, col(User.id) == Snapshot.user_id)
        .where(Snapshot.user_id == current_user.id),
    ).all()
    return [
        SnapshotAdminOutput.model_validate(snapshot, update={"username": username})
        for snapshot, username in rows
    ]


@snapshots_router.get("/public")
def get_public_snapshots(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SnapshotPublicListOutput:
    """List public `Snapshot`s with a positive admin score, highest score first.

    Snapshots with a `score` of `0` are hidden. Results are ordered by `score`
    descending, then by `id` ascending, and returned a page at a time.
    """
    public_and_scored = (
        Snapshot.visibility == Visibility.public,
        Snapshot.score >= 1,
    )
    count = session.exec(
        select(func.count()).select_from(Snapshot).where(*public_and_scored),
    ).one()
    rows = session.exec(
        select(Snapshot, User.username)
        .join(User, col(User.id) == Snapshot.user_id)
        .where(*public_and_scored)
        .order_by(col(Snapshot.score).desc(), col(Snapshot.id))
        .offset(offset)
        .limit(limit),
    ).all()
    data = [
        service.public_snapshot_output(snapshot, username)
        for snapshot, username in rows
    ]
    return SnapshotPublicListOutput(data=data, count=count)


@snapshots_router.get("/{snapshot_id}", response_model=SnapshotDetailOutput)  # noqa: FAST003 - Used by ReadableSnapshot
def get_snapshot(
    snapshot: ReadableSnapshot,
    user: OptionalUser,
) -> SnapshotDetailOutput:
    """Get a `Snapshot` if it's readable by the `User`."""
    return service.snapshot_output(snapshot, user)


@snapshots_router.patch("/{snapshot_id}", response_model=SnapshotDetailOutput)  # noqa: FAST003 - Used by EditableSnapshot
def update_snapshot(
    session: SessionDep,
    snapshot: EditableSnapshot,
    snapshot_input: SnapshotUpdate,
) -> Snapshot:
    """Update and return a `Snapshot` if it's editable by the `User`."""
    metadata = snapshot_input.model_dump(
        exclude_unset=True,
        exclude={"episode_ids"},
    )
    if metadata:
        snapshot.sqlmodel_update(metadata)

    if "episode_ids" in snapshot_input.model_fields_set:
        episode_ids = snapshot_input.episode_ids or []
        service.set_snapshot_episodes(session, snapshot, episode_ids)

    session.commit()
    session.refresh(snapshot)
    return snapshot


@snapshots_router.delete("/{snapshot_id}")  # noqa: FAST003 - Used by EditableSnapshot
def delete_snapshot(session: SessionDep, snapshot: EditableSnapshot) -> Message:
    """Delete a `Snapshot` if it's editable by the `User`."""
    return delete_record(session, snapshot)


@admin_router.patch("/{snapshot_id}")  # noqa: FAST003 - Used by ExistingSnapshot.
def admin_update_snapshot(
    session: SessionDep,
    snapshot: ExistingSnapshot,
    snapshot_input: SnapshotAdminUpdate,
) -> SnapshotAdminOutput:
    """Update any field on any `Snapshot` as an admin, including `score`."""
    snapshot.sqlmodel_update(snapshot_input.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(snapshot)
    username = session.get_one(User, snapshot.user_id).username
    return SnapshotAdminOutput.model_validate(snapshot, update={"username": username})


@snapshots_router.get("/{snapshot_id}/media")  # noqa: FAST003 - Used by ReadableSnapshot
def get_snapshot_episodes(
    session: SessionDep,
    snapshot: ReadableSnapshot,
    user: OptionalUser,
) -> SnapshotEpisodesOutput:
    """Read the episodes for a snapshot with hydrated season/show/source/plugin data."""
    output = SnapshotEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
    )

    # Look up the most recent watch per episode for the current viewer (if any).
    latest_watches: dict[uuid.UUID, Watch] = {}
    if user and snapshot.episodes:
        episode_ids = [entry.episode_id for entry in snapshot.episodes]
        watches = session.exec(
            select(Watch)
            .where(Watch.user_id == user.id)
            .where(col(Watch.episode_id).in_(episode_ids))
            .order_by(col(Watch.watch_date).desc()),
        ).all()
        for watch in watches:
            if watch.episode_id not in latest_watches:
                latest_watches[watch.episode_id] = watch

    for entry in snapshot.episodes:
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
            SnapshotEpisodeWithExtrasOutput(
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


router = APIRouter()
router.include_router(snapshots_router)
router.include_router(admin_router)
