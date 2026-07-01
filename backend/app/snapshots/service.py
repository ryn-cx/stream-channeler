# TODO: Validate
import uuid

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.snapshots.models import Snapshot, SnapshotEpisode
from app.snapshots.schemas import SnapshotDetailOutput, SnapshotPublicOutput
from app.users.models import User


def snapshot_output(snapshot: Snapshot, viewer: User | None) -> SnapshotDetailOutput:
    output = SnapshotDetailOutput.model_validate(snapshot)
    if not snapshot.anonymous:
        return output
    if viewer and (viewer.is_superuser or viewer.id == snapshot.user_id):
        return output
    output.user_id = None
    return output


def public_snapshot_output(
    snapshot: Snapshot,
    username: str | None,
) -> SnapshotPublicOutput:
    anonymous = snapshot.anonymous
    return SnapshotPublicOutput(
        id=snapshot.id,
        user_id=None if anonymous else snapshot.user_id,
        name=snapshot.name,
        visibility=snapshot.visibility,
        anonymous=anonymous,
        username=None if anonymous else username,
    )


def set_snapshot_episodes(
    session: Session,
    snapshot: Snapshot,
    episode_ids: list[uuid.UUID],
) -> None:
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

    snapshot.episodes = [
        SnapshotEpisode(episode_id=episode_id, position=position)  # pyright: ignore[reportCallIssue]
        for position, episode_id in enumerate(episode_ids)
    ]
