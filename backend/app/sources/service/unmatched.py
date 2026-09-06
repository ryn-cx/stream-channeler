# TODO: Validate
"""Source service functions."""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, delete, select

from app.schemas import Message
from app.sources.models import UnmatchedSource
from app.sources.schemas import UnmatchedSourceImport, UnmatchedSourceOutput
from app.titles.models import Title
from app.titles.service.canonical import match_title_to_tmdb
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.manage_plugins import get_plugin_for_url


# TODO: Validate
def remove_unmatched_source(
    session: Session,
    title_id: uuid.UUID,
    provider_name: str,
) -> None:
    session.exec(
        delete(UnmatchedSource).where(
            col(UnmatchedSource.title_id) == title_id,
            col(UnmatchedSource.provider_name) == provider_name,
        ),
    )


# TODO: Validate
def remove_plugin_unmatched_sources(
    session: Session,
    title_id: uuid.UUID,
    plugin_key: str,
) -> None:
    result = session.exec(
        delete(UnmatchedSource).where(
            col(UnmatchedSource.title_id) == title_id,
            col(UnmatchedSource.plugin_key) == plugin_key,
        ),
    )
    if result.rowcount:
        session.commit()


# TODO: Validate
def _unmatched_source_output(
    unmatched_source: UnmatchedSource,
) -> UnmatchedSourceOutput:
    return UnmatchedSourceOutput(
        id=unmatched_source.id,
        provider_name=unmatched_source.provider_name,
        plugin_key=unmatched_source.plugin_key,
        created_at=unmatched_source.created_at,
        modified_at=unmatched_source.modified_at,
        title_id=unmatched_source.title_id,
        title_name=unmatched_source.title.name,
    )


# TODO: Validate
def list_unmatched_sources(session: Session) -> list[UnmatchedSourceOutput]:
    statement = (
        select(UnmatchedSource)
        .where(col(UnmatchedSource.ignored_at).is_(None))
        .options(selectinload(UnmatchedSource.title))  # type: ignore[arg-type]
        .order_by(col(UnmatchedSource.created_at).desc())
    )
    return [
        _unmatched_source_output(record) for record in session.exec(statement).all()
    ]


# TODO: Validate
def import_unmatched_source(
    session: Session,
    unmatched_source: UnmatchedSource,
    import_input: UnmatchedSourceImport,
) -> Message:
    url = import_input.url.strip()
    plugin_class = get_plugin_for_url(url)
    if plugin_class is None:
        raise HTTPException(
            status_code=400,
            detail=f"No plugin imports {url}",
        )

    title = session.exec(
        select(Title).where(Title.id == unmatched_source.title_id),
    ).one_or_none()
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")

    plugin_instance = plugin_class(session)
    try:
        results = plugin_instance.import_url(url)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for result in results:
        match_title_to_tmdb(session, result.title, title)

    session.delete(unmatched_source)
    session.commit()
    return Message(message="Unmatched source imported successfully")


# TODO: Validate
def ignore_unmatched_source(
    session: Session,
    unmatched_source: UnmatchedSource,
) -> Message:
    unmatched_source.ignored_at = tz_datetime.now()
    session.add(unmatched_source)
    session.commit()
    return Message(message="Unmatched source ignored")


# TODO: Validate
def delete_unmatched_source(
    session: Session,
    unmatched_source: UnmatchedSource,
) -> Message:
    session.delete(unmatched_source)
    session.commit()
    return Message(message="Unmatched source deleted")
