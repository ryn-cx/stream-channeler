"""Snapshot dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, existing_record, readable_record
from app.snapshots.models import Snapshot

EditableSnapshot = Annotated[
    Snapshot,
    Depends(editable_record(Snapshot, "snapshot_id")),
]
ReadableSnapshot = Annotated[
    Snapshot,
    Depends(readable_record(Snapshot, "snapshot_id")),
]
ExistingSnapshot = Annotated[
    Snapshot,
    Depends(existing_record(Snapshot, "snapshot_id")),
]
