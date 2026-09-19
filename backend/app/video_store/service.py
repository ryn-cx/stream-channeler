# TODO: Validate
"""Video store service."""

import uuid
from collections.abc import Sequence
from typing import Literal

import httpx
from fastapi import HTTPException, Response
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, distinct, func, select

from app.channels.channel_scope import child_channel_ids, resolve_channel_ids
from app.channels.models import Channel, ChannelTitle
from app.channels.service.titles import titles_by_tmdb_record_id
from app.episodes.models import Episode
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import (
    Title,
    TitleGenre,
    TitleSpokenLanguage,
    TitleTmdbTitle,
    TitleWatchProvider,
)
from app.users.models import User
from app.video_store.schemas import (
    VideoStoreLanguageOutput,
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitleDetailOutput,
    VideoStoreTitleOutput,
    VideoStoreTitlesOutput,
    VideoStoreWatchLinkOutput,
    VideoStoreWatchProviderOutput,
)
from app.watch_providers.models import WatchProvider

STORE_TITLE_PAGE = 200


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
            Plugin.key != TMDB_PLUGIN_KEY,
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
        .where(col(TitleTmdbTitle.title_id).in_(title_ids)),
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
            col(Season.title_id).in_(title_ids),
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
        .where(col(TitleGenre.title_id).in_(title_ids))
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
        .where(col(TitleSpokenLanguage.title_id).in_(title_ids))
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
def _sibling_title_ids(
    session: Session,
    tmdb_title_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Group every website's row of a canonical title under that title."""
    if not tmdb_title_ids:
        return {}

    rows = session.exec(
        select(TitleTmdbTitle.tmdb_title_id, TitleTmdbTitle.title_id).where(
            col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
        ),
    ).all()
    siblings: dict[uuid.UUID, list[uuid.UUID]] = {}
    for tmdb_title_id, title_id in rows:
        siblings.setdefault(tmdb_title_id, []).append(title_id)
    return siblings


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

    shelved: list[VideoStoreTitleOutput] = []
    for title in titles:
        linked_title = linked_titles.get(title.id) or title
        primary, secondary = (
            (linked_title, title) if metadata == "tmdb" else (title, linked_title)
        )
        season_count, episode_count = stats.get(title.id, (0, 0))
        poster = primary.poster_thumbnail_url or secondary.poster_thumbnail_url
        shelved.append(
            VideoStoreTitleOutput(
                id=title.id,
                name=primary.name or secondary.name,
                year=primary.year or secondary.year,
                score=primary.score,
                popularity=primary.popularity,
                media_type=primary.media_type or secondary.media_type,
                original_language=(
                    primary.original_language or secondary.original_language
                ),
                languages=(
                    languages.get(primary.id) or languages.get(secondary.id) or []
                ),
                thumbnail_url=(
                    poster or primary.thumbnail_url or secondary.thumbnail_url
                ),
                is_poster=poster is not None,
                genres=genres.get(primary.id, []),
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
        select(Plugin.key, Title.url)
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Title.id).in_(title_ids),
            col(Title.url).is_not(None),
            col(Title.deleted_at).is_(None),
        )
        .order_by(col(Plugin.key)),
    ).all()

    links: list[VideoStoreWatchLinkOutput] = []
    seen: set[str] = set()
    for plugin_key, url in rows:
        if url is None or url in seen:
            continue
        seen.add(url)
        links.append(VideoStoreWatchLinkOutput(plugin_name=plugin_key, url=url))
    return links


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
    spoken = session.exec(
        select(TitleSpokenLanguage.code, TitleSpokenLanguage.name)
        .where(col(TitleSpokenLanguage.title_id).in_([title.id, linked_title.id]))
        .order_by(col(TitleSpokenLanguage.name)),
    ).all()
    names = dict(spoken)
    original_code = primary.original_language or secondary.original_language
    return VideoStoreTitleDetailOutput(
        id=title.id,
        name=primary.name or secondary.name,
        year=primary.year or secondary.year,
        poster_url=(
            primary.poster_url
            or secondary.poster_url
            or primary.image_url
            or secondary.image_url
        ),
        image_url=(
            primary.image_url
            or secondary.image_url
            or primary.thumbnail_url
            or secondary.thumbnail_url
        ),
        description=primary.description or secondary.description,
        original_language=(
            names.get(original_code, original_code) if original_code else None
        ),
        languages=sorted({name for name in names.values() if name}),
        url=title.url,
        links=_watch_links(
            session,
            [
                title.id,
                linked_title.id,
                *_sibling_title_ids(session, [linked_title.id]).get(
                    linked_title.id,
                    [],
                ),
            ],
        ),
    )


# TODO: Validate
async def title_image(session: Session, title: Title, url: str) -> Response:
    linked_title = _linked_titles(session, [title.id]).get(title.id)
    rows = [title] if linked_title is None else [title, linked_title]
    served = {
        image
        for row in rows
        for image in (
            row.image_url,
            row.thumbnail_url,
            row.poster_url,
            row.poster_thumbnail_url,
        )
        if image is not None
    }
    if url not in served:
        raise HTTPException(status_code=404, detail="Title carries no such image")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        upstream = await client.get(url, headers={"referer": url})
    if upstream.status_code != httpx.codes.OK:
        raise HTTPException(status_code=502, detail="Website would not serve the image")

    return Response(
        content=upstream.content,
        media_type=upstream.headers.get("content-type", "image/jpeg"),
        headers={"cache-control": "public, max-age=86400"},
    )


# TODO: Validate
def store_titles(
    session: Session,
    source: Source,
    metadata: Literal["tmdb", "source"] = "tmdb",
) -> VideoStoreTitlesOutput:
    """Read every title a `Source` carries, in shelf order."""
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
                col(Title.id).in_(tmdb_title_ids),
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
    """Read every `WatchProvider` carrying titles in `region`, largest first."""
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
