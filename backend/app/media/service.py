# TODO: Validate
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

if TYPE_CHECKING:
    from app.users.models import User

from app.channels.models import Channel
from app.channels.schemas import ChannelOutput, ChannelPatchInput, ChannelsListOutput
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.models import Message
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput, PluginPatchInput, PluginsListOutput
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.models import Show
from app.shows.schemas import ShowOutput, ShowPatchInput, ShowPostInput, ShowsListOutput
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from app.watches.models import Watch
from app.watches.schemas import WatchPatchInput

type MediaModel = Channel | Episode | Season | Show | Source | Plugin | Watch
type ListOutput = (
    ChannelsListOutput
    | PluginsListOutput
    | SourcesListOutput
    | ShowsListOutput
    | SeasonsListOutput
    | EpisodesListOutput
)
type Output = (
    ChannelOutput
    | PluginOutput
    | SourceOutput
    | ShowOutput
    | SeasonOutput
    | EpisodeOutput
)
type PatchInput = (
    ChannelPatchInput
    | EpisodePatchInput
    | SeasonPatchInput
    | ShowPatchInput
    | SourcePatchInput
    | PluginPatchInput
    | WatchPatchInput
)


def list_children[T: ListOutput](  # noqa: PLR0913
    session: Session,
    model: type[Channel | Plugin | Source | Show | Season | Episode],
    parent_key_field: str,
    parent_id: uuid.UUID,
    output_schema: type[Output],
    list_schema: type[T],
) -> T:
    """Generic list: query children by FK, validate, and return list output."""
    records = session.exec(
        select(model).where(getattr(model, parent_key_field) == parent_id),
    ).all()
    data = [output_schema.model_validate(record) for record in records]
    # Automatic Pydantic casting.
    return list_schema(data=data)  # type: ignore[arg-type]


def get_first_or_error[T: MediaModel](
    session: Session,
    statement: SelectOfScalar[T],
    current_user_id: uuid.UUID,
    name: str,
) -> T:
    """Execute query, returning 403 if not owned or 404 if not found."""
    if result := session.exec(statement).first():
        if result.get_user_id(session) != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access this {name}",
            )
        return result
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{name} not found",
    )


def get_first_readable_or_error[T: MediaModel](
    session: Session,
    statement: SelectOfScalar[T],
    current_user_id: uuid.UUID | None,
    name: str,
) -> T:
    """Execute query, allowing access if public, owned, or superuser."""
    if result := session.exec(statement).first():
        if result.is_public(session):
            return result
        if current_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if result.get_user_id(session) != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access this {name}",
            )
        return result
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{name} not found",
    )


def get_user_resource[T: MediaModel](
    session: Session,
    model: type[T],
    resource_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> T:
    """Look up a resource by ID and verify user ownership."""
    statement = select(model).where(model.id == resource_id)
    return get_first_or_error(session, statement, current_user_id, model.__name__)


def get_readable_resource[T: MediaModel](
    session: Session,
    model: type[T],
    resource_id: uuid.UUID,
    user: User | None,
) -> T:
    """Get a resource by ID if it is public or owned by the current user."""
    statement = select(model).where(model.id == resource_id)
    user_id = user.id if user else None
    return get_first_readable_or_error(session, statement, user_id, model.__name__)


def raise_if_exists(
    existing: MediaModel | None,
) -> None:
    """Raise 409 Conflict if a record already exists."""
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{type(existing).__name__} with this key already exists",
        )


def create_child[T: Source | Show | Season | Episode](
    session: Session,
    model: type[T],
    parent: Plugin | Source | Show | Season,
    body: SourcePostInput | ShowPostInput | SeasonPostInput | EpisodePostInput,
    parent_key: str,
) -> T:
    """Generic create: check for existing, validate, add, commit, and return."""
    # There is no good way to type hint the relationship between the parent and child
    # models.
    raise_if_exists(model.get(session, parent, body.key))  # type: ignore[attr-defined, arg-type]
    child = model.model_validate(body, update={parent_key: parent.id})
    session.add(child)
    session.commit()
    session.refresh(child)
    return child  # type: ignore[return-value]


def _check_duplicate_key(
    session: Session,
    entry: MediaModel,
    body: PatchInput,
) -> None:
    """Raise 409 if updating key would conflict with a sibling record."""
    # Channel and Watch do not have user editable unique keys.
    if isinstance(entry, (Channel, Watch)):
        return
    if isinstance(body, (ChannelPatchInput, WatchPatchInput)):
        return

    # If the key is not changing no checks needs to be done.
    if body.key is None or body.key == entry.key:
        return
    raise_if_exists(entry.get_sibling(session, body.key))


def update_record[T: MediaModel](
    session: Session,
    entry: T,
    body: PatchInput,
) -> T:
    """Generic update: apply patch, commit, refresh, and return."""
    _check_duplicate_key(session, entry, body)
    entry.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(entry)
    return entry


def delete_record(
    session: Session,
    entry: MediaModel,
) -> Message:
    """Generic delete: remove entry, commit, and return a success message."""
    session.delete(entry)
    session.commit()
    return Message(message=f"{type(entry).__name__} deleted successfully")
