# TODO: Validate
"""Video store service."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, distinct, func, select

from app.episodes.models import Episode
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import (
    Title,
    TitleGenre,
    TitleTmdbTitle,
    TitleWatchProvider,
)
from app.video_store.schemas import (
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitleOutput,
    VideoStoreTitlesOutput,
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
def _shelve_titles(
    session: Session,
    titles: Sequence[Title],
) -> list[VideoStoreTitleOutput]:
    title_ids = [title.id for title in titles]
    linked_titles = _linked_titles(session, title_ids)
    stats = _title_stats(session, title_ids)
    genres = _title_genres(
        session,
        title_ids + [linked.id for linked in linked_titles.values()],
    )

    shelved: list[VideoStoreTitleOutput] = []
    for title in titles:
        linked_title = linked_titles.get(title.id) or title
        season_count, episode_count = stats.get(title.id, (0, 0))
        shelved.append(
            VideoStoreTitleOutput(
                id=title.id,
                name=linked_title.name or title.name,
                year=linked_title.year or title.year,
                poster_url=(
                    linked_title.poster_url
                    or title.poster_url
                    or linked_title.image_url
                    or title.image_url
                ),
                poster_thumbnail_url=(
                    linked_title.poster_thumbnail_url or title.poster_thumbnail_url
                ),
                thumbnail_url=(
                    linked_title.poster_thumbnail_url
                    or linked_title.thumbnail_url
                    or title.poster_thumbnail_url
                    or title.thumbnail_url
                ),
                image_url=(
                    linked_title.image_url
                    or title.image_url
                    or linked_title.thumbnail_url
                    or title.thumbnail_url
                ),
                description=linked_title.description or title.description,
                genres=genres.get(linked_title.id) or genres.get(title.id) or [],
                url=title.url,
                season_count=season_count,
                episode_count=episode_count,
            ),
        )
    return shelved


# TODO: Validate
def store_titles(
    session: Session,
    source: Source,
    offset: int,
    limit: int,
) -> VideoStoreTitlesOutput:
    """Read a page of the titles a `Source` carries, in shelf order."""
    total = session.exec(
        select(func.count(col(Title.id))).where(
            col(Title.source_id) == source.id,
            col(Title.deleted_at).is_(None),
        ),
    ).one()

    titles = session.exec(
        select(Title)
        .where(
            col(Title.source_id) == source.id,
            col(Title.deleted_at).is_(None),
        )
        .order_by(col(Title.name), col(Title.id))
        .offset(offset)
        .limit(limit),
    ).all()

    return VideoStoreTitlesOutput(
        titles=_shelve_titles(session, titles),
        total=total,
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
    offset: int,
    limit: int,
) -> VideoStoreTitlesOutput:
    """Read a page of the titles a `WatchProvider` offers in `region`."""
    total = session.exec(
        select(func.count(distinct(col(Title.id))))
        .select_from(Title)
        .join(TitleWatchProvider, col(TitleWatchProvider.title_id) == col(Title.id))
        .where(
            TitleWatchProvider.watch_provider_id == watch_provider_id,
            TitleWatchProvider.region == region,
            col(Title.deleted_at).is_(None),
        ),
    ).one()

    titles = session.exec(
        select(Title)
        .join(TitleWatchProvider, col(TitleWatchProvider.title_id) == col(Title.id))
        .where(
            TitleWatchProvider.watch_provider_id == watch_provider_id,
            TitleWatchProvider.region == region,
            col(Title.deleted_at).is_(None),
        )
        .distinct()
        .order_by(col(Title.name), col(Title.id))
        .offset(offset)
        .limit(limit),
    ).all()

    return VideoStoreTitlesOutput(
        titles=_shelve_titles(session, titles),
        total=total,
    )
