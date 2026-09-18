# TODO: Validate


import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, delete, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.channel_scope import in_a_user_channel
from app.channels.models import ChannelTitle
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle, UnmatchedTitle
from app.titles.schemas import (
    UnmatchedTitleImport,
    UnmatchedTitleOutput,
    UnmatchedTitleReadOptions,
    UnmatchedTitlesPublic,
)
from app.titles.service.linking import old_link_title_to_tmdb
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import tmdb_title_url
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.manage_plugins import get_plugin_from_url, plugins

_UNMATCHED_COLUMNS: dict[str, Any] = {
    "title_name": Title.name,
    "title_year": Title.year,
    "media_type": Title.media_type,
    "provider_name": UnmatchedTitle.provider_name,
    "plugin_key": UnmatchedTitle.plugin_key,
}


# TODO: Validate
def plugin_key_for_provider(provider_name: str) -> str | None:
    """Return the plugin that carries `provider_name`, if one of them does."""
    for plugin in plugins:
        if plugin.matches_tmdb_provider(provider_name):
            return plugin.plugin_name()
    return None


# TODO: Validate
def _plugin_keys_carrying(session: Session, title: Title) -> set[str]:
    """Return the plugins whose rows already stand for `title`."""
    return set(
        session.exec(
            select(Plugin.key)
            .select_from(TitleTmdbTitle)
            .join(Title, onclause=col(TitleTmdbTitle.title_id) == Title.id)
            .join(Source, onclause=col(Title.source_id) == Source.id)
            .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
            .where(col(TitleTmdbTitle.tmdb_title_id) == title.id),
        ).all(),
    )


# TODO: Validate
def record_unmatched_providers(
    session: Session,
    title: Title,
    provider_names: set[str],
) -> None:
    """Write down every service carrying `title` that nothing here carries.

    Called with the whole of what TMDB says rather than one name at a time, so a
    service that has since dropped the title, or one a plugin has since been
    written for, has its row taken away on the same pass that adds the others.
    """
    carried_by = _plugin_keys_carrying(session, title)
    wanted: dict[str, str | None] = {}
    for provider_name in provider_names:
        plugin_key = plugin_key_for_provider(provider_name)
        if plugin_key is not None and plugin_key in carried_by:
            continue
        wanted[provider_name] = plugin_key

    existing = {
        record.provider_name: record
        for record in session.exec(
            select(UnmatchedTitle).where(col(UnmatchedTitle.title_id) == title.id),
        ).all()
    }
    for provider_name, record in existing.items():
        if provider_name not in wanted:
            session.delete(record)
    for provider_name, plugin_key in wanted.items():
        kept = existing.get(provider_name)
        if kept is None:
            session.add(
                UnmatchedTitle(
                    title_id=title.id,
                    provider_name=provider_name,
                    plugin_key=plugin_key,
                ),
            )
        elif kept.plugin_key != plugin_key:
            kept.plugin_key = plugin_key
            session.add(kept)
    session.flush()


# TODO: Validate
def remove_unmatched_title(
    session: Session,
    title_id: uuid.UUID,
    provider_name: str,
) -> None:
    session.exec(
        delete(UnmatchedTitle).where(
            col(UnmatchedTitle.title_id) == title_id,
            col(UnmatchedTitle.provider_name) == provider_name,
        ),
    )


# TODO: Validate
def remove_plugin_unmatched_titles(
    session: Session,
    title_id: uuid.UUID,
    plugin_key: str,
) -> None:
    session.exec(
        delete(UnmatchedTitle).where(
            col(UnmatchedTitle.title_id) == title_id,
            col(UnmatchedTitle.plugin_key) == plugin_key,
        ),
    )


# TODO: Validate
def _unmatched_base(
    *,
    in_user_channels_only: bool,
    include_ignored: bool,
) -> SelectOfScalar[UnmatchedTitle]:
    return (
        select(UnmatchedTitle)
        .select_from(UnmatchedTitle)
        .join(Title, onclause=col(UnmatchedTitle.title_id) == Title.id)
        .options(selectinload(UnmatchedTitle.title))  # type: ignore[arg-type]
        .where(
            col(Title.deleted_at).is_(None),
            is_not_linked(Title),
            *([] if include_ignored else [col(UnmatchedTitle.ignored_at).is_(None)]),
            *([in_a_user_channel()] if in_user_channels_only else []),
        )
    )


# TODO: Validate
def _channel_counts(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    return dict(
        session.exec(
            select(ChannelTitle.tmdb_title_id, func.count())
            .where(col(ChannelTitle.tmdb_title_id).in_(title_ids))
            .group_by(col(ChannelTitle.tmdb_title_id)),
        ).all(),
    )


# TODO: Validate
def _episode_counts(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    return dict(
        session.exec(
            select(Season.title_id, func.count(col(Episode.id)))
            .join(Episode, onclause=col(Episode.season_id) == Season.id)
            .where(
                col(Season.title_id).in_(title_ids),
                col(Season.deleted_at).is_(None),
                col(Episode.deleted_at).is_(None),
            )
            .group_by(col(Season.title_id)),
        ).all(),
    )


# TODO: Validate
def _unmatched_output(
    record: UnmatchedTitle,
    channel_count: int,
    episode_count: int,
) -> UnmatchedTitleOutput:
    return UnmatchedTitleOutput(
        id=record.id,
        provider_name=record.provider_name,
        plugin_key=record.plugin_key,
        created_at=record.created_at,
        modified_at=record.modified_at,
        title_id=record.title_id,
        title_name=record.title.name,
        title_year=record.title.year,
        media_type=record.title.media_type,
        tmdb_url=tmdb_title_url(record.title.key),
        channel_count=channel_count,
        episode_count=episode_count,
    )


# TODO: Validate
def list_unmatched_titles(
    session: Session,
    params: UnmatchedTitleReadOptions,
) -> UnmatchedTitlesPublic:
    """Sorted, filtered and paged by the database rather than in the browser.

    There is a row for every service carrying every title nothing here carries,
    which is far more than a page of them, so ordering a page would order only
    the rows already fetched.
    """
    base = _unmatched_base(
        in_user_channels_only=params.in_user_channels_only,
        include_ignored=params.include_ignored,
    )
    filtered = _apply_filter_options(base, params.filter_options, _UNMATCHED_COLUMNS)
    total_count = session.exec(
        select(func.count()).select_from(base.subquery()),
    ).one()
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            _UNMATCHED_COLUMNS,
            [Title.name],
            UnmatchedTitle.id,
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    records = list(session.exec(page).all())
    title_ids = [record.title_id for record in records]
    channel_counts = _channel_counts(session, title_ids)
    episode_counts = _episode_counts(session, title_ids)
    return UnmatchedTitlesPublic(
        data=[
            _unmatched_output(
                record,
                channel_counts.get(record.title_id, 0),
                episode_counts.get(record.title_id, 0),
            )
            for record in records
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )


# TODO: Validate
def import_unmatched_title(
    session: Session,
    unmatched_title: UnmatchedTitle,
    import_input: UnmatchedTitleImport,
) -> Message:
    url = import_input.url.strip()
    plugin_class = get_plugin_from_url(url)
    if plugin_class is None:
        raise HTTPException(
            status_code=400,
            detail=f"No plugin imports {url}",
        )

    title = session.exec(
        select(Title).where(Title.id == unmatched_title.title_id),
    ).one_or_none()
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")

    plugin_instance = plugin_class(session)
    try:
        results = plugin_instance.validate_and_import_url(url)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for result in results:
        old_link_title_to_tmdb(session, result.title, title, "Automatic: Import match")

    session.delete(unmatched_title)
    session.commit()
    return Message(message="Unmatched title imported successfully")


# TODO: Validate
def ignore_unmatched_title(
    session: Session,
    unmatched_title: UnmatchedTitle,
) -> Message:
    unmatched_title.ignored_at = tz_datetime.now()
    session.add(unmatched_title)
    session.commit()
    return Message(message="Unmatched title ignored")


# TODO: Validate
def delete_unmatched_title(
    session: Session,
    unmatched_title: UnmatchedTitle,
) -> Message:
    session.delete(unmatched_title)
    session.commit()
    return Message(message="Unmatched title deleted")
