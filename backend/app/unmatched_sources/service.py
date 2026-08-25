# TODO: Validate
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.schemas import Message
from app.shows.models import Show
from app.unmatched_sources.models import UnmatchedSource
from app.unmatched_sources.schemas import (
    UnmatchedSourceImport,
    UnmatchedSourceOutput,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.manage_plugins import plugin_for_url


# TODO: Validate
def _output(unmatched_source: UnmatchedSource) -> UnmatchedSourceOutput:
    return UnmatchedSourceOutput(
        id=unmatched_source.id,
        provider_name=unmatched_source.provider_name,
        plugin_key=unmatched_source.plugin_key,
        created_at=unmatched_source.created_at,
        modified_at=unmatched_source.modified_at,
        show_id=unmatched_source.show_id,
        show_name=unmatched_source.show.name,
    )


# TODO: Validate
def record_unmatched_source(
    session: Session,
    show_id: uuid.UUID,
    provider_name: str,
    plugin_key: str | None,
) -> None:
    statement = select(UnmatchedSource).where(
        UnmatchedSource.show_id == show_id,
        UnmatchedSource.provider_name == provider_name,
    )
    if session.exec(statement).one_or_none() is not None:
        return

    session.add(
        UnmatchedSource(
            show_id=show_id,
            provider_name=provider_name,
            plugin_key=plugin_key,
        ),
    )
    session.commit()


# TODO: Validate
def clear_unmatched_source(
    session: Session,
    show_id: uuid.UUID,
    provider_name: str,
) -> None:
    statement = select(UnmatchedSource).where(
        UnmatchedSource.show_id == show_id,
        UnmatchedSource.provider_name == provider_name,
    )
    unmatched_source = session.exec(statement).one_or_none()
    if unmatched_source is None:
        return

    session.delete(unmatched_source)
    session.commit()


# TODO: Validate
def list_unmatched_sources(session: Session) -> list[UnmatchedSourceOutput]:
    statement = (
        select(UnmatchedSource)
        .options(selectinload(UnmatchedSource.show))  # type: ignore[arg-type]
        .order_by(col(UnmatchedSource.created_at).desc())
    )
    return [_output(record) for record in session.exec(statement).all()]


# TODO: Validate
def import_unmatched_source(
    session: Session,
    unmatched_source: UnmatchedSource,
    import_input: UnmatchedSourceImport,
) -> Message:
    url = import_input.url.strip()
    plugin_class = plugin_for_url(url)
    if plugin_class is None:
        raise HTTPException(
            status_code=400,
            detail=f"No plugin imports {url}",
        )

    show = session.exec(
        select(Show).where(Show.id == unmatched_source.show_id),
    ).one_or_none()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    try:
        plugin_class(session).import_url(url, show)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    session.delete(unmatched_source)
    session.commit()
    return Message(message="Unmatched source imported successfully")
