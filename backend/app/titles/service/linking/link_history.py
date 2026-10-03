# TODO: Validate

from typing import Any

from sqlalchemy import (
    Integer,
    Select,
    String,
    Uuid,
    cast,
    literal,
    null,
    union_all,
)
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle, UnmatchedTitle
from app.titles.schemas import (
    TitleLinkHistoryOutput,
    TitleLinkHistoryPublic,
)
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import tmdb_title_url

_website_title: Any = aliased(Title)
_website_source: Any = aliased(Source)
_website_plugin: Any = aliased(Plugin)
_tmdb_title: Any = aliased(Title)


# TODO: Validate
def _link_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("link").label("kind"),
            col(TitleTmdbTitle.id).label("entry_id"),
            col(TitleTmdbTitle.title_id).label("title_id"),
            col(TitleTmdbTitle.tmdb_title_id).label("tmdb_title_id"),
            cast(null(), Uuid).label("unmatched_title_id"),
            col(TitleTmdbTitle.note).label("note"),
            col(TitleTmdbTitle.created_at).label("happened_at"),
            _website_title.name.label("title_name"),
            _website_title.year.label("title_year"),
            _website_title.media_type.label("media_type"),
            _website_title.key.label("title_key"),
            _website_title.url.label("title_url"),
            _website_source.key.label("source_key"),
            _website_plugin.key.label("plugin_name"),
            _tmdb_title.name.label("tmdb_title_name"),
            _tmdb_title.year.label("tmdb_title_year"),
            _tmdb_title.key.label("tmdb_title_key"),
        )
        .select_from(TitleTmdbTitle)
        .join(
            _website_title,
            onclause=col(TitleTmdbTitle.title_id) == _website_title.id,
        )
        .join(_website_source, onclause=_website_title.source_id == _website_source.id)
        .join(_website_plugin, onclause=_website_source.plugin_id == _website_plugin.id)
        .join(
            _tmdb_title,
            onclause=col(TitleTmdbTitle.tmdb_title_id) == _tmdb_title.id,
        )
        .where(
            col(TitleTmdbTitle.manual_tmdb_link).is_(True),
            col(_website_title.deleted_at).is_(None),
            col(_tmdb_title.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _absent_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("absent").label("kind"),
            col(Title.id).label("entry_id"),
            col(Title.id).label("title_id"),
            cast(null(), Uuid).label("tmdb_title_id"),
            cast(null(), Uuid).label("unmatched_title_id"),
            cast(null(), String).label("note"),
            col(Title.tmdb_absent_at).label("happened_at"),
            col(Title.name).label("title_name"),
            col(Title.year).label("title_year"),
            col(Title.media_type).label("media_type"),
            col(Title.key).label("title_key"),
            col(Title.url).label("title_url"),
            col(Source.key).label("source_key"),
            col(Plugin.key).label("plugin_name"),
            cast(null(), String).label("tmdb_title_name"),
            cast(null(), Integer).label("tmdb_title_year"),
            cast(null(), String).label("tmdb_title_key"),
        )
        .select_from(Title)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            col(Title.tmdb_absent_at).is_not(None),
            col(Title.tmdb_title_validated_at).is_not(None),
            col(Title.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _ignored_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("ignored").label("kind"),
            col(UnmatchedTitle.id).label("entry_id"),
            col(UnmatchedTitle.title_id).label("title_id"),
            cast(null(), Uuid).label("tmdb_title_id"),
            col(UnmatchedTitle.id).label("unmatched_title_id"),
            cast(null(), String).label("note"),
            col(UnmatchedTitle.ignored_at).label("happened_at"),
            col(Title.name).label("title_name"),
            col(Title.year).label("title_year"),
            col(Title.media_type).label("media_type"),
            col(Title.key).label("title_key"),
            col(Title.url).label("title_url"),
            col(UnmatchedTitle.provider_name).label("source_key"),
            col(UnmatchedTitle.plugin_key).label("plugin_name"),
            cast(null(), String).label("tmdb_title_name"),
            cast(null(), Integer).label("tmdb_title_year"),
            cast(null(), String).label("tmdb_title_key"),
        )
        .select_from(UnmatchedTitle)
        .join(Title, onclause=col(UnmatchedTitle.title_id) == Title.id)
        .where(
            col(UnmatchedTitle.ignored_at).is_not(None),
            col(Title.deleted_at).is_(None),
            is_not_linked(Title),
        )
    )


# TODO: Validate
def list_title_link_history(
    session: Session,
    params: ReadOptions,
) -> TitleLinkHistoryPublic:
    entries = union_all(
        _link_entries(),
        _absent_entries(),
        _ignored_entries(),
    ).subquery()
    columns: dict[str, Any] = {
        "kind": entries.c.kind,
        "created_at": entries.c.happened_at,
        "note": entries.c.note,
        "title_name": entries.c.title_name,
        "title_year": entries.c.title_year,
        "media_type": entries.c.media_type,
        "source_key": entries.c.source_key,
        "plugin_name": entries.c.plugin_name,
        "tmdb_title_name": entries.c.tmdb_title_name,
    }
    base = select(entries)  # type: ignore[call-overload]
    filtered = _apply_filter_options(base, params.filter_options, columns)
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
            columns,
            [entries.c.happened_at],
            entries.c.entry_id,  # type: ignore[arg-type]
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return TitleLinkHistoryPublic(
        data=_history_outputs(list(session.execute(page).all())),
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )


# TODO: Validate
def _history_outputs(entries: list[Any]) -> list[TitleLinkHistoryOutput]:
    return [
        TitleLinkHistoryOutput(
            id=entry.entry_id,
            kind=entry.kind,
            title_id=entry.title_id,
            tmdb_title_id=entry.tmdb_title_id,
            unmatched_title_id=entry.unmatched_title_id,
            note=entry.note,
            created_at=entry.happened_at,
            title_name=entry.title_name,
            title_year=entry.title_year,
            media_type=entry.media_type,
            title_url=entry.title_url or tmdb_title_url(entry.title_key),
            source_key=entry.source_key,
            plugin_name=entry.plugin_name,
            tmdb_title_name=entry.tmdb_title_name,
            tmdb_title_year=entry.tmdb_title_year,
            tmdb_url=tmdb_title_url(entry.tmdb_title_key),
        )
        for entry in entries
    ]
