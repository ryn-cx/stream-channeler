import uuid
from typing import Any, overload

from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeInput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.models import Message, MetadataMixin
from app.plugins.models import Plugin
from app.plugins.schemas import PluginInput, PluginPatchInput, PluginPostInput
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.models import Show
from app.shows.schemas import ShowInput, ShowPatchInput, ShowPostInput, ShowsListOutput
from app.sources.models import Source
from app.sources.schemas import (
    SourceInput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from app.users.models import User


def get_first_or_error[T: Episode | Season | Show | Source | Plugin](
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


@overload
def create_record(
    session: Session,
    parent: Season,
    post_input: EpisodePostInput,
    input_schema: type[EpisodeInput],
    existing: Episode | None = ...,
) -> Episode: ...


@overload
def create_record(
    session: Session,
    parent: Show,
    post_input: SeasonPostInput,
    input_schema: type[SeasonInput],
    existing: Season | None = ...,
) -> Season: ...


@overload
def create_record(
    session: Session,
    parent: Source,
    post_input: ShowPostInput,
    input_schema: type[ShowInput],
    existing: Show | None = ...,
) -> Show: ...


@overload
def create_record(
    session: Session,
    parent: Plugin,
    post_input: SourcePostInput,
    input_schema: type[SourceInput],
    existing: Source | None = ...,
) -> Source: ...


@overload
def create_record(
    session: Session,
    parent: User,
    post_input: PluginPostInput,
    input_schema: type[PluginInput],
    existing: Plugin | None = ...,
) -> Plugin: ...


def create_record(
    session: Session,
    parent: Season | Show | Source | Plugin | User,
    post_input: (
        EpisodePostInput
        | SeasonPostInput
        | ShowPostInput
        | SourcePostInput
        | PluginPostInput
    ),
    input_schema: type[
        EpisodeInput | SeasonInput | ShowInput | SourceInput | PluginInput
    ],
    existing: Episode | Season | Show | Source | Plugin | None = None,
) -> Episode | Season | Show | Source | Plugin:
    """Generic create for a child entry under a parent."""
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{existing.__class__.__name__} with this key already exists",
        )
    dumped = post_input.model_dump()
    entry = input_schema(**dumped).upsert(parent, None)  # type: ignore[arg-type]
    session.commit()
    return entry


def update_record[T: MetadataMixin](
    session: Session,
    entry: T,
    body: (
        EpisodePatchInput
        | SeasonPatchInput
        | ShowPatchInput
        | SourcePatchInput
        | PluginPatchInput
    ),
) -> T:
    """Generic update: apply patch, commit, refresh, and return."""
    entry.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(entry)
    return entry


@overload
def list_records(
    session: Session,
    parent: Season,
    child_model: type[Episode],
    parent_key: str,
    list_output: type[EpisodesListOutput],
) -> EpisodesListOutput: ...


@overload
def list_records(
    session: Session,
    parent: Show,
    child_model: type[Season],
    parent_key: str,
    list_output: type[SeasonsListOutput],
) -> SeasonsListOutput: ...


@overload
def list_records(
    session: Session,
    parent: Source,
    child_model: type[Show],
    parent_key: str,
    list_output: type[ShowsListOutput],
) -> ShowsListOutput: ...


@overload
def list_records(
    session: Session,
    parent: Plugin,
    child_model: type[Source],
    parent_key: str,
    list_output: type[SourcesListOutput],
) -> SourcesListOutput: ...


def list_records(
    session: Session,
    parent: Season | Show | Source | Plugin,
    child_model: type[Episode | Season | Show | Source],
    parent_key: str,
    list_output: type[
        EpisodesListOutput | SeasonsListOutput | ShowsListOutput | SourcesListOutput
    ],
) -> EpisodesListOutput | SeasonsListOutput | ShowsListOutput | SourcesListOutput:
    """Generic list: query children of a parent and return a list output."""
    column = getattr(child_model, parent_key)
    records: Any = session.exec(select(child_model).where(column == parent.id)).all()
    return list_output(data=list(records), count=len(records))


def delete_record(
    session: Session,
    entry: Episode | Season | Show | Source | Plugin,
    model_name: str,
) -> Message:
    """Generic delete: remove entry, commit, and return a success message."""
    session.delete(entry)
    session.commit()
    return Message(message=f"{model_name} deleted successfully")
