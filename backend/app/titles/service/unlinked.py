# TODO: Validate

from typing import Any

from sqlalchemy import Select, String, asc, cast
from sqlmodel import Session, col, func, select

from app.channels.channel_scope import _user_channel_titles
from app.plugins.models import Plugin
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title
from app.titles.schemas import (
    UnlinkedTitleOutput,
    UnlinkedTitleReadOptions,
    UnlinkedTitlesPublic,
)
from app.tmdb_media.filters import is_not_linked


# TODO: Validate
def _unlinked_titles(*, in_user_channels_only: bool) -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            col(Title.id).label("title_id"),
            col(Title.name).label("title_name"),
            col(Title.year).label("title_year"),
            col(Title.media_type).label("media_type"),
            col(Title.url).label("title_url"),
            col(Title.link_status).label("link_status"),
            col(Title.created_at).label("created_at"),
            col(Source.key).label("source_key"),
            col(Plugin.key).label("plugin_name"),
        )
        .select_from(Title)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            col(Title.deleted_at).is_(None),
            col(Title.tmdb_absent_at).is_(None),
            is_not_linked(Title),
            col(Source.link_to_tmdb).is_(True),
            *(
                [col(Title.id).in_(_user_channel_titles())]
                if in_user_channels_only
                else []
            ),
        )
    )


# TODO: Validate
def list_unlinked_titles(
    session: Session,
    params: UnlinkedTitleReadOptions,
) -> UnlinkedTitlesPublic:
    titles = _unlinked_titles(
        in_user_channels_only=params.in_user_channels_only,
    ).subquery()
    columns: dict[str, Any] = {
        "created_at": titles.c.created_at,
        "title_name": titles.c.title_name,
        "title_year": cast(titles.c.title_year, String),
        "media_type": titles.c.media_type,
        "link_status": titles.c.link_status,
        "source_key": func.concat(titles.c.source_key, " · ", titles.c.plugin_name),
        "plugin_name": titles.c.plugin_name,
    }
    base = select(titles)  # type: ignore[call-overload]
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
            [asc(titles.c.title_name)],
            titles.c.title_id,  # type: ignore[arg-type]
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return UnlinkedTitlesPublic(
        data=[
            UnlinkedTitleOutput(
                id=title.title_id,
                title_name=title.title_name,
                title_year=title.title_year,
                media_type=title.media_type,
                title_url=title.title_url,
                link_status=title.link_status,
                created_at=title.created_at,
                source_key=title.source_key,
                plugin_name=title.plugin_name,
            )
            for title in session.execute(page).all()
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )
