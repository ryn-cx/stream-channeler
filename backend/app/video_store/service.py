# TODO: Validate
"""Video store service."""

import uuid
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import Uuid, case, cast
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, distinct, func, or_, select

from app.channels.channel_scope import child_channel_ids, resolve_channel_ids
from app.channels.models import Channel, ChannelTitle
from app.channels.schemas import TitleCardsOutput
from app.channels.service.titles import title_cards_output, titles_by_tmdb_record_id
from app.episodes.models import Episode
from app.images.service import ImageField, image_url
from app.plugins.identifiers import (
    TMDB_PLUGIN_KEY,
    TMDB_VIDEOS_SOURCE_KEY,
    YOUTUBE_PLUGIN_KEY,
)
from app.plugins.models import Plugin
from app.plugins.schemas import PluginSearchResult
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import (
    Title,
    TitleGenre,
    TitleSpokenLanguage,
    TitleTmdbTitle,
    TitleWatchProvider,
)
from app.tmdb_media.filters import is_not_linked
from app.users.models import User
from app.video_store.schemas import (
    VideoStoreFacetsOutput,
    VideoStoreLanguageOutput,
    VideoStoreOptionOutput,
    VideoStoreProviderTitleCardOptions,
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitleCardOptions,
    VideoStoreTitleDetailOutput,
    VideoStoreTitleOutput,
    VideoStoreTitleSourceOutput,
    VideoStoreTitlesOutput,
    VideoStoreTrailerOutput,
    VideoStoreWatchLinkOutput,
    VideoStoreWatchProviderOutput,
)
from app.watch_providers.models import WatchProvider
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import sorted_plugins

STORE_TITLE_PAGE = 200


# TODO: Validate
def _any_id(
    column: ColumnElement[uuid.UUID],
    identifiers: Sequence[uuid.UUID],
) -> ColumnElement[bool]:
    return column == func.any(cast(list(identifiers), ARRAY(Uuid)))


# TODO: Validate
def store_sources(session: Session) -> list[VideoStoreSourceOutput]:
    """Read every `Source` a store can be built from, largest first.

    TMDB is a catalogue rather than somewhere a title can be watched, so its own
    source is never a shelf.
    """
    rows = session.exec(
        select(
            Source.id,
            Source.key,
            Plugin.key,
            Source.favicon_url,
            Source.image_url,
            func.count(col(Title.id)),
        )
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .join(Title, col(Title.source_id) == col(Source.id))
        .where(
            col(Plugin.key).not_in([TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY]),
            col(Plugin.deleted_at).is_(None),
            col(Source.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
        )
        .group_by(
            col(Source.id),
            col(Source.key),
            col(Plugin.key),
            col(Source.favicon_url),
            col(Source.image_url),
        )
        .order_by(func.count(col(Title.id)).desc()),
    ).all()

    return [
        VideoStoreSourceOutput(
            id=source_id,
            key=source_key,
            plugin_name=plugin_key,
            favicon_url=favicon_url,
            image_url=image_url,
            title_count=title_count,
        )
        for source_id, source_key, plugin_key, favicon_url, image_url, title_count in rows
    ]


# TODO: Validate
def _linked_titles(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Title]:
    if not title_ids:
        return {}

    tmdb_title = aliased(Title)
    rows = session.exec(
        select(TitleTmdbTitle.title_id, tmdb_title)
        .join(
            tmdb_title,
            col(tmdb_title.id) == col(TitleTmdbTitle.tmdb_title_id),
        )
        .where(_any_id(col(TitleTmdbTitle.title_id), title_ids)),
    ).all()
    return dict(rows)


# TODO: Validate
def _title_stats(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, tuple[int, int]]:
    if not title_ids:
        return {}

    rows = session.exec(
        select(
            Season.title_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Season)
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            _any_id(col(Season.title_id), title_ids),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.title_id)),
    ).all()
    return {
        title_id: (season_count, episode_count)
        for title_id, season_count, episode_count in rows
    }


# TODO: Validate
def _title_genres(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    if not title_ids:
        return {}

    rows = session.exec(
        select(TitleGenre.title_id, TitleGenre.name)
        .where(_any_id(col(TitleGenre.title_id), title_ids))
        .order_by(col(TitleGenre.name)),
    ).all()
    genres: dict[uuid.UUID, list[str]] = {}
    for title_id, name in rows:
        genres.setdefault(title_id, []).append(name)
    return genres


# TODO: Validate
def _title_languages(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    if not title_ids:
        return {}

    rows = session.exec(
        select(TitleSpokenLanguage.title_id, TitleSpokenLanguage.code)
        .where(_any_id(col(TitleSpokenLanguage.title_id), title_ids))
        .order_by(col(TitleSpokenLanguage.code)),
    ).all()
    languages: dict[uuid.UUID, list[str]] = {}
    for title_id, code in rows:
        languages.setdefault(title_id, []).append(code)
    return languages


# TODO: Validate
def store_original_languages(session: Session) -> list[VideoStoreLanguageOutput]:
    """Read every original language a title is filed under, largest first."""
    names = dict(
        session.exec(
            select(TitleSpokenLanguage.code, TitleSpokenLanguage.name).distinct(),
        ).all(),
    )
    rows = session.exec(
        select(Title.original_language, func.count(col(Title.id)))
        .where(
            col(Title.original_language).is_not(None),
            col(Title.deleted_at).is_(None),
        )
        .group_by(col(Title.original_language))
        .order_by(func.count(col(Title.id)).desc()),
    ).all()
    return [
        VideoStoreLanguageOutput(
            code=code,
            name=names.get(code),
            title_count=title_count,
        )
        for code, title_count in rows
        if code is not None
    ]


# TODO: Validate
def store_spoken_languages(session: Session) -> list[VideoStoreLanguageOutput]:
    """Read every language a title is spoken in, largest first."""
    rows = session.exec(
        select(
            TitleSpokenLanguage.code,
            func.min(col(TitleSpokenLanguage.name)),
            func.count(distinct(col(TitleSpokenLanguage.title_id))),
        )
        .join(Title, col(Title.id) == col(TitleSpokenLanguage.title_id))
        .where(col(Title.deleted_at).is_(None))
        .group_by(col(TitleSpokenLanguage.code))
        .order_by(func.count(distinct(col(TitleSpokenLanguage.title_id))).desc()),
    ).all()
    return [
        VideoStoreLanguageOutput(code=code, name=name, title_count=title_count)
        for code, name, title_count in rows
    ]


# TODO: Validate
def _store_facets(
    session: Session,
    listed: list[ColumnElement[bool]],
) -> VideoStoreFacetsOutput:
    stored = select(Title.id).where(*listed)

    media_type_rows = session.exec(
        select(Title.media_type, func.count(col(Title.id)))
        .where(*listed, col(Title.media_type).is_not(None))
        .group_by(col(Title.media_type))
        .order_by(func.count(col(Title.id)).desc()),
    ).all()

    original_language_rows = session.exec(
        select(Title.original_language, func.count(col(Title.id)))
        .where(*listed, col(Title.original_language).is_not(None))
        .group_by(col(Title.original_language))
        .order_by(func.count(col(Title.id)).desc()),
    ).all()
    language_names = dict(
        session.exec(
            select(TitleSpokenLanguage.code, TitleSpokenLanguage.name).distinct(),
        ).all(),
    )

    genre_rows = session.exec(
        select(TitleGenre.name, func.count(distinct(col(TitleGenre.title_id))))
        .where(col(TitleGenre.title_id).in_(stored))
        .group_by(col(TitleGenre.name))
        .order_by(func.count(distinct(col(TitleGenre.title_id))).desc()),
    ).all()

    spoken_language_rows = session.exec(
        select(
            TitleSpokenLanguage.code,
            func.min(col(TitleSpokenLanguage.name)),
            func.count(distinct(col(TitleSpokenLanguage.title_id))),
        )
        .where(col(TitleSpokenLanguage.title_id).in_(stored))
        .group_by(col(TitleSpokenLanguage.code))
        .order_by(func.count(distinct(col(TitleSpokenLanguage.title_id))).desc()),
    ).all()

    return VideoStoreFacetsOutput(
        media_types=[
            VideoStoreOptionOutput(name=media_type, title_count=title_count)
            for media_type, title_count in media_type_rows
            if media_type is not None
        ],
        genres=[
            VideoStoreOptionOutput(name=name, title_count=title_count)
            for name, title_count in genre_rows
        ],
        original_languages=[
            VideoStoreLanguageOutput(
                code=code,
                name=language_names.get(code),
                title_count=title_count,
            )
            for code, title_count in original_language_rows
            if code is not None
        ],
        spoken_languages=[
            VideoStoreLanguageOutput(code=code, name=name, title_count=title_count)
            for code, name, title_count in spoken_language_rows
        ],
    )


# TODO: Validate
def _title_card_filters(
    options: VideoStoreTitleCardOptions,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if options.query:
        filters.append(col(Title.name).ilike(f"%{options.query}%"))
    ranges = [
        (col(Title.year), options.year_from, options.year_to),
        (col(Title.tmdb_score), options.tmdb_score_from, options.tmdb_score_to),
        (
            col(Title.tmdb_popularity),
            options.tmdb_popularity_from,
            options.tmdb_popularity_to,
        ),
        (col(Title.imdb_score), options.imdb_score_from, options.imdb_score_to),
        (
            col(Title.imdb_popularity),
            options.imdb_popularity_from,
            options.imdb_popularity_to,
        ),
    ]
    for column, lowest, highest in ranges:
        if lowest is not None:
            filters.append(column >= lowest)
        if highest is not None:
            filters.append(column <= highest)
    if options.media_types:
        filters.append(col(Title.media_type).in_(options.media_types))
    if options.original_languages:
        filters.append(col(Title.original_language).in_(options.original_languages))
    if options.spoken_languages:
        filters.append(
            col(Title.id).in_(
                select(TitleSpokenLanguage.title_id).where(
                    col(TitleSpokenLanguage.code).in_(options.spoken_languages),
                ),
            ),
        )
    if options.genres:
        filters.append(
            col(Title.id).in_(
                select(TitleGenre.title_id).where(
                    col(TitleGenre.name).in_(options.genres),
                ),
            ),
        )
    return filters


# TODO: Validate
def _sibling_title_ids(
    session: Session,
    tmdb_title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Group every website's row of a canonical title under that title."""
    if not tmdb_title_ids:
        return {}

    rows = session.exec(
        select(TitleTmdbTitle.tmdb_title_id, TitleTmdbTitle.title_id).where(
            _any_id(col(TitleTmdbTitle.tmdb_title_id), tmdb_title_ids),
        ),
    ).all()
    siblings: dict[uuid.UUID, list[uuid.UUID]] = {}
    for tmdb_title_id, title_id in rows:
        siblings.setdefault(tmdb_title_id, []).append(title_id)
    return siblings


# TODO: Validate
def _row_plugins(
    session: Session,
    title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, type[AbstractPlugin]]:
    if not title_ids:
        return {}

    classes = {plugin.plugin_name(): plugin for plugin in sorted_plugins()}
    rows = session.exec(
        select(Title.id, Plugin.key)
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(_any_id(col(Title.id), title_ids)),
    ).all()
    return {
        title_id: classes[plugin_key]
        for title_id, plugin_key in rows
        if plugin_key in classes
    }


# TODO: Validate
def _first_artwork(
    rows: Sequence[Title],
    plugins: dict[uuid.UUID, type[AbstractPlugin]],
    field: ImageField,
) -> str | None:
    for row in rows:
        url: str | None = getattr(row, f"{field}_url")
        if url is None:
            continue
        plugin = plugins.get(row.id, AbstractPlugin)
        if not plugin.PROXY_IMAGES:
            return url
        return image_url(row, field, plugin)
    return None


# TODO: Validate
def _shelve_titles(
    session: Session,
    titles: Sequence[Title],
    metadata: Literal["tmdb", "source"] = "tmdb",
) -> list[VideoStoreTitleOutput]:
    title_ids = [title.id for title in titles]
    linked_titles = _linked_titles(session, title_ids)
    stats = _title_stats(session, title_ids)
    tmdb_ids = [linked.id for linked in linked_titles.values()]
    related_ids = [*title_ids, *tmdb_ids]
    genres = _title_genres(session, related_ids)
    languages = _title_languages(session, related_ids)
    plugins = _row_plugins(session, related_ids)

    shelved: list[VideoStoreTitleOutput] = []
    for title in titles:
        linked_title = linked_titles.get(title.id) or title
        primary, secondary = (
            (linked_title, title) if metadata == "tmdb" else (title, linked_title)
        )
        ordered = (primary, secondary)
        source_genres = genres.get(title.id, [])
        tmdb_genres = (
            genres.get(linked_title.id, []) if title.id in linked_titles else []
        )
        chosen_genres, fallback_genres = (
            (tmdb_genres, source_genres)
            if metadata == "tmdb"
            else (source_genres, tmdb_genres)
        )
        shelf_genres = chosen_genres or [f"!{name}" for name in fallback_genres]
        season_count, episode_count = stats.get(title.id, (0, 0))
        poster = _first_artwork(ordered, plugins, "poster_thumbnail")
        thumbnail = _first_artwork(ordered, plugins, "thumbnail")
        shelved.append(
            VideoStoreTitleOutput(
                id=title.id,
                name=primary.name or secondary.name,
                year=primary.year or secondary.year,
                tmdb_score=linked_title.tmdb_score,
                tmdb_popularity=linked_title.tmdb_popularity,
                imdb_score=linked_title.imdb_score,
                imdb_popularity=linked_title.imdb_popularity,
                media_type=primary.media_type or secondary.media_type,
                original_language=(
                    primary.original_language or secondary.original_language
                ),
                languages=(
                    languages.get(primary.id) or languages.get(secondary.id) or []
                ),
                thumbnail_url=poster or thumbnail,
                is_poster=poster is not None,
                genres=shelf_genres,
                season_count=season_count,
                episode_count=episode_count,
            ),
        )
    return shelved


# TODO: Validate
def _watch_links(
    session: Session,
    title_ids: list[uuid.UUID],
) -> list[VideoStoreWatchLinkOutput]:
    """Read every website one title, its canonical row and its siblings sit on."""
    if not title_ids:
        return []

    rows = session.exec(
        select(Source.key, Title.url)
        .select_from(Title)
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            _any_id(col(Title.id), title_ids),
            col(Title.url).is_not(None),
            col(Title.deleted_at).is_(None),
        )
        .order_by(col(Plugin.key), col(Source.key)),
    ).all()

    links: list[VideoStoreWatchLinkOutput] = []
    seen: set[tuple[str, str]] = set()
    for source_key, url in rows:
        if url is None or (source_key, url) in seen:
            continue
        seen.add((source_key, url))
        links.append(VideoStoreWatchLinkOutput(source_name=source_key, url=url))
    return links


# TODO: Validate
def _title_sources(
    session: Session,
    title_ids: list[uuid.UUID],
) -> list[VideoStoreTitleSourceOutput]:
    """Read every website row a title is reported against."""
    if not title_ids:
        return []

    rows = session.exec(
        select(Title.id, Plugin.key, Source.key, Title.name, Title.url)
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            _any_id(col(Title.id), title_ids),
            col(Title.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .order_by(col(Plugin.key), col(Source.key)),
    ).all()
    return [
        VideoStoreTitleSourceOutput(
            title_id=title_id,
            plugin_name=plugin_key,
            source_key=source_key,
            name=name,
            url=url,
        )
        for title_id, plugin_key, source_key, name, url in rows
    ]


# TODO: Validate
def _average_runtime(session: Session, title_id: uuid.UUID) -> int | None:
    runtime = session.exec(
        select(func.avg(col(Episode.duration)))
        .select_from(Season)
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            col(Season.title_id) == title_id,
            col(Episode.deleted_at).is_(None),
            col(Episode.duration).is_not(None),
        ),
    ).one()
    return None if runtime is None else round(runtime)


# TODO: Validate
def _trailers(
    session: Session,
    tmdb_title_id: uuid.UUID,
) -> list[VideoStoreTrailerOutput]:
    rows = session.exec(
        select(Season.key, Episode.name, Episode.url)
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .where(
            col(TitleTmdbTitle.tmdb_title_id) == tmdb_title_id,
            Source.key == TMDB_VIDEOS_SOURCE_KEY,
            col(Title.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            col(Episode.url).is_not(None),
        )
        .order_by(
            case(
                {
                    "Trailer": 0,
                    "Teaser": 1,
                    "Clip": 2,
                    "Behind the Scenes": 3,
                    "Bloopers": 4,
                    "Featurette": 5,
                },
                value=col(Season.key),
                else_=6,
            ),
            col(Season.key),
            col(Episode.sort_order),
        ),
    ).all()
    return [
        VideoStoreTrailerOutput(type=video_type, name=name, url=url)
        for video_type, name, url in rows
        if url is not None
    ]


# TODO: Validate
def title_detail(
    session: Session,
    title: Title,
    metadata: Literal["tmdb", "source"] = "tmdb",
) -> VideoStoreTitleDetailOutput:
    """Read everything the case viewer shows for one shelved title."""
    linked_title = _linked_titles(session, [title.id]).get(title.id) or title
    primary, secondary = (
        (linked_title, title) if metadata == "tmdb" else (title, linked_title)
    )
    plugins = _row_plugins(session, [title.id, linked_title.id])
    ordered = (primary, secondary)
    spoken = session.exec(
        select(TitleSpokenLanguage.code, TitleSpokenLanguage.name)
        .where(col(TitleSpokenLanguage.title_id).in_([title.id, linked_title.id]))
        .order_by(col(TitleSpokenLanguage.name)),
    ).all()
    names = dict(spoken)
    original_code = primary.original_language or secondary.original_language
    related_ids = [
        title.id,
        linked_title.id,
        *_sibling_title_ids(session, [linked_title.id]).get(linked_title.id, []),
    ]
    return VideoStoreTitleDetailOutput(
        id=title.id,
        name=primary.name or secondary.name,
        year=primary.year or secondary.year,
        poster_url=_first_artwork(ordered, plugins, "poster"),
        image_url=(
            _first_artwork(ordered, plugins, "image")
            or _first_artwork(ordered, plugins, "thumbnail")
        ),
        description=primary.description or secondary.description,
        original_language=(
            names.get(original_code, original_code) if original_code else None
        ),
        languages=sorted({name for name in names.values() if name}),
        runtime=_average_runtime(session, linked_title.id),
        imdb_score=linked_title.imdb_score,
        imdb_popularity=linked_title.imdb_popularity,
        url=title.url,
        links=_watch_links(session, related_ids),
        sources=_title_sources(session, related_ids),
        trailers=_trailers(session, linked_title.id),
    )


# TODO: Validate
def title_matches(session: Session, title: Title) -> list[PluginSearchResult]:
    """Search TMDB for what a title's own website says it is.

    The query is the plugin's lookup info rather than anything the caller passes,
    so reading this never puts a visitor's own words in front of TMDB.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    plugin_classes = {plugin.plugin_name(): plugin for plugin in sorted_plugins()}
    plugin_class = plugin_classes[title.source.plugin.key]
    queries = []
    if plugin_class.implements("tmdb_lookup_info"):
        plugin_instance = plugin_class(session, title.source.plugin)
        queries = [lookup.name for lookup in plugin_instance.tmdb_lookup_info(title)]
    if not queries and title.name:
        queries = [title.name]

    tmdb = TMDB(session)
    matches: list[PluginSearchResult] = []
    seen: set[str] = set()
    for query in queries:
        for result in tmdb.in_app_search(query).results:
            key = result.media_identifier or result.url
            if key in seen:
                continue
            seen.add(key)
            matches.append(result)
    return matches


# TODO: Validate
def store_titles(
    session: Session,
    source: Source,
    metadata: Literal["tmdb", "source"] = "tmdb",
) -> VideoStoreTitlesOutput:
    """Read every title a `Source` has, in shelf order."""
    listed = [
        col(Title.source_id) == source.id,
        col(Title.deleted_at).is_(None),
    ]
    titles = session.exec(
        select(Title).where(*listed).order_by(col(Title.name), col(Title.id)),
    ).all()

    return VideoStoreTitlesOutput(
        titles=_shelve_titles(session, titles, metadata),
    )


# TODO: Validate
def channel_titles(
    session: Session,
    channel: Channel,
    user: User | None,
) -> VideoStoreTitlesOutput:
    """Read every title a `Channel` shelves, canonical rows first."""
    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )
    listed = [
        col(ChannelTitle.channel_id).in_(channel_ids),
        col(ChannelTitle.is_blacklist_only).is_(False),
    ]

    tmdb_title_ids = session.exec(
        select(ChannelTitle.tmdb_title_id)
        .join(
            Title,
            col(Title.id) == col(ChannelTitle.tmdb_title_id),
            isouter=True,
        )
        .where(*listed)
        .group_by(col(ChannelTitle.tmdb_title_id), col(Title.name))
        .order_by(col(Title.name), col(ChannelTitle.tmdb_title_id)),
    ).all()

    canonical = {
        title.id: title
        for title in session.exec(
            select(Title).where(
                _any_id(col(Title.id), tmdb_title_ids),
                col(Title.deleted_at).is_(None),
            ),
        ).all()
    }
    unlinked = titles_by_tmdb_record_id(
        session,
        [
            tmdb_title_id
            for tmdb_title_id in tmdb_title_ids
            if tmdb_title_id not in canonical
        ],
    )

    shelved: list[Title] = []
    for tmdb_title_id in tmdb_title_ids:
        title = canonical.get(tmdb_title_id)
        if title is not None:
            shelved.append(title)
            continue
        shelved.extend(unlinked.get(tmdb_title_id, []))

    return VideoStoreTitlesOutput(
        titles=_shelve_titles(session, shelved),
    )


# TODO: Validate
def _source_listing(source: Source) -> list[ColumnElement[bool]]:
    website_title = aliased(Title)
    linked_from_source = (
        select(TitleTmdbTitle.tmdb_title_id)
        .join(website_title, col(website_title.id) == col(TitleTmdbTitle.title_id))
        .where(
            col(website_title.source_id) == source.id,
            col(website_title.deleted_at).is_(None),
        )
    )
    return [
        is_not_linked(Title),
        col(Title.deleted_at).is_(None),
        or_(
            col(Title.source_id) == source.id,
            col(Title.id).in_(linked_from_source),
        ),
    ]


# TODO: Validate
def source_title_cards(
    session: Session,
    source: Source,
    options: VideoStoreTitleCardOptions,
) -> TitleCardsOutput:
    listed = [*_source_listing(source), *_title_card_filters(options)]
    canonical = select(Title.id).where(*listed)
    total = session.exec(select(func.count()).select_from(canonical.subquery())).one()
    tmdb_title_ids = session.exec(
        canonical.order_by(func.lower(col(Title.name)), col(Title.id))
        .offset(options.offset)
        .limit(options.limit),
    ).all()
    return title_cards_output(session, tmdb_title_ids, total)


# TODO: Validate
def source_facets(session: Session, source: Source) -> VideoStoreFacetsOutput:
    return _store_facets(session, _source_listing(source))


# TODO: Validate
def store_regions(session: Session) -> list[VideoStoreRegionOutput]:
    """Read every region a watch provider store can be built for, largest first."""
    rows = session.exec(
        select(
            TitleWatchProvider.region,
            func.count(distinct(col(TitleWatchProvider.title_id))),
        )
        .join(Title, col(Title.id) == col(TitleWatchProvider.title_id))
        .where(col(Title.deleted_at).is_(None))
        .group_by(col(TitleWatchProvider.region))
        .order_by(
            func.count(distinct(col(TitleWatchProvider.title_id))).desc(),
            col(TitleWatchProvider.region),
        ),
    ).all()

    return [
        VideoStoreRegionOutput(region=region, title_count=title_count)
        for region, title_count in rows
    ]


# TODO: Validate
def store_watch_providers(
    session: Session,
    region: str,
) -> list[VideoStoreWatchProviderOutput]:
    """Read every `WatchProvider` with titles in `region`, largest first."""
    rows = session.exec(
        select(
            WatchProvider.id,
            WatchProvider.tmdb_provider_id,
            WatchProvider.name,
            WatchProvider.logo_url,
            func.count(distinct(col(TitleWatchProvider.title_id))),
        )
        .join(
            TitleWatchProvider,
            col(TitleWatchProvider.watch_provider_id) == col(WatchProvider.id),
        )
        .join(Title, col(Title.id) == col(TitleWatchProvider.title_id))
        .where(
            TitleWatchProvider.region == region,
            col(Title.deleted_at).is_(None),
        )
        .group_by(
            col(WatchProvider.id),
            col(WatchProvider.tmdb_provider_id),
            col(WatchProvider.name),
            col(WatchProvider.logo_url),
        )
        .order_by(
            func.count(distinct(col(TitleWatchProvider.title_id))).desc(),
            col(WatchProvider.name),
        ),
    ).all()

    return [
        VideoStoreWatchProviderOutput(
            id=watch_provider_id,
            tmdb_provider_id=tmdb_provider_id,
            name=name,
            logo_url=logo_url,
            title_count=title_count,
        )
        for (
            watch_provider_id,
            tmdb_provider_id,
            name,
            logo_url,
            title_count,
        ) in rows
    ]


# TODO: Validate
def provider_titles(
    session: Session,
    watch_provider_id: uuid.UUID,
    region: str,
) -> VideoStoreTitlesOutput:
    """Read every title a `WatchProvider` offers in `region`."""
    titles = session.exec(
        select(Title)
        .join(TitleWatchProvider, col(TitleWatchProvider.title_id) == col(Title.id))
        .where(
            TitleWatchProvider.watch_provider_id == watch_provider_id,
            TitleWatchProvider.region == region,
            col(Title.deleted_at).is_(None),
        )
        .distinct()
        .order_by(col(Title.name), col(Title.id)),
    ).all()

    return VideoStoreTitlesOutput(
        titles=_shelve_titles(session, titles),
    )


# TODO: Validate
def _provider_listing(
    watch_provider_id: uuid.UUID,
    region: str,
) -> list[ColumnElement[bool]]:
    return [
        col(Title.deleted_at).is_(None),
        col(Title.id).in_(
            select(TitleWatchProvider.title_id).where(
                TitleWatchProvider.watch_provider_id == watch_provider_id,
                TitleWatchProvider.region == region.upper(),
            ),
        ),
    ]


# TODO: Validate
def provider_title_cards(
    session: Session,
    watch_provider_id: uuid.UUID,
    options: VideoStoreProviderTitleCardOptions,
) -> TitleCardsOutput:
    listed = [
        *_provider_listing(watch_provider_id, options.region),
        *_title_card_filters(options),
    ]
    offered = select(Title.id).where(*listed)
    total = session.exec(select(func.count()).select_from(offered.subquery())).one()
    tmdb_title_ids = session.exec(
        offered.order_by(func.lower(col(Title.name)), col(Title.id))
        .offset(options.offset)
        .limit(options.limit),
    ).all()
    return title_cards_output(session, tmdb_title_ids, total)


# TODO: Validate
def provider_facets(
    session: Session,
    watch_provider_id: uuid.UUID,
    region: str,
) -> VideoStoreFacetsOutput:
    return _store_facets(session, _provider_listing(watch_provider_id, region))
