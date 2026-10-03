# TODO: Validate

from typing import Any

from sqlalchemy import Select, String, and_, asc, cast, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select

from app.channels.channel_scope import _user_channel_titles
from app.plugins.models import Plugin
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.titles.schemas import (
    MismatchedTitleOutput,
    MismatchedTitleReadOptions,
    MismatchedTitlesPublic,
)
from app.tmdb_media.tmdb import tmdb_title_url

_tmdb_title: Any = aliased(Title)


# TODO: Validate
def _comparable_name(name: Any) -> ColumnElement[str]:  # noqa: ANN401
    return func.lower(func.regexp_replace(name, "[^[:alnum:]]+", "", "g"))


# TODO: Validate
def _mismatched_links(*, in_user_channels_only: bool) -> Select[Any]:
    name_mismatched = _comparable_name(col(Title.name)).is_distinct_from(
        _comparable_name(_tmdb_title.name),
    )
    year_mismatched = and_(
        col(Title.year).is_not(None),
        _tmdb_title.year.is_not(None),
        col(Title.year) != _tmdb_title.year,
    )
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            col(TitleTmdbTitle.id).label("link_id"),
            col(TitleTmdbTitle.title_id).label("title_id"),
            col(TitleTmdbTitle.tmdb_title_id).label("tmdb_title_id"),
            col(TitleTmdbTitle.note).label("note"),
            col(TitleTmdbTitle.created_at).label("linked_at"),
            col(Title.name).label("title_name"),
            col(Title.year).label("title_year"),
            col(Title.media_type).label("media_type"),
            col(Title.key).label("title_key"),
            col(Title.url).label("title_url"),
            col(Source.key).label("source_key"),
            col(Plugin.key).label("plugin_name"),
            _tmdb_title.name.label("tmdb_title_name"),
            _tmdb_title.year.label("tmdb_title_year"),
            _tmdb_title.key.label("tmdb_title_key"),
            name_mismatched.label("name_mismatched"),
            year_mismatched.label("year_mismatched"),
        )
        .select_from(TitleTmdbTitle)
        .join(Title, onclause=col(TitleTmdbTitle.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .join(
            _tmdb_title,
            onclause=col(TitleTmdbTitle.tmdb_title_id) == _tmdb_title.id,
        )
        .where(
            col(Title.deleted_at).is_(None),
            col(_tmdb_title.deleted_at).is_(None),
            col(Title.tmdb_title_validated_at).is_(None),
            col(TitleTmdbTitle.manual_tmdb_link).is_(False),
            or_(name_mismatched, year_mismatched),
            *(
                [col(TitleTmdbTitle.tmdb_title_id).in_(_user_channel_titles())]
                if in_user_channels_only
                else []
            ),
        )
    )


# TODO: Validate
def list_mismatched_titles(
    session: Session,
    params: MismatchedTitleReadOptions,
) -> MismatchedTitlesPublic:
    links = _mismatched_links(
        in_user_channels_only=params.in_user_channels_only,
    ).subquery()
    columns: dict[str, Any] = {
        "linked_at": links.c.linked_at,
        "note": links.c.note,
        "title_name": links.c.title_name,
        "title_year": cast(links.c.title_year, String),
        "media_type": links.c.media_type,
        "source_key": func.concat(links.c.source_key, " · ", links.c.plugin_name),
        "plugin_name": links.c.plugin_name,
        "tmdb_title_name": links.c.tmdb_title_name,
        "tmdb_title_year": cast(links.c.tmdb_title_year, String),
    }
    base = select(links)  # type: ignore[call-overload]
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
            [asc(links.c.title_name)],
            links.c.link_id,  # type: ignore[arg-type]
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return MismatchedTitlesPublic(
        data=[
            MismatchedTitleOutput(
                id=link.link_id,
                title_id=link.title_id,
                tmdb_title_id=link.tmdb_title_id,
                note=link.note,
                linked_at=link.linked_at,
                title_name=link.title_name,
                title_year=link.title_year,
                media_type=link.media_type,
                title_url=link.title_url or tmdb_title_url(link.title_key),
                source_key=link.source_key,
                plugin_name=link.plugin_name,
                tmdb_title_name=link.tmdb_title_name,
                tmdb_title_year=link.tmdb_title_year,
                tmdb_url=tmdb_title_url(link.tmdb_title_key),
                name_mismatched=link.name_mismatched,
                year_mismatched=link.year_mismatched,
            )
            for link in session.execute(page).all()
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )
