# TODO: Validate


import time
import uuid
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from typing import Any, NamedTuple
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.episode_selector import (
    EpisodeQueryBuilder,
    apply_user_episode_urls,
)
from app.channels.models import (
    Channel,
    ChannelEpisodeSourceFilter,
    ChannelTitle,
)
from app.channels.schemas import (
    ChannelEpisodePlugin,
    ChannelEpisodeSeason,
    ChannelEpisodeSource,
    ChannelEpisodesOutput,
    ChannelEpisodeTitle,
    ChannelOptions,
    EpisodeWithDetails,
    WhitelistEpisodeLinkOutput,
)
from app.channels.service.titles import (
    titles_from_channel_title,
    tmdb_titles_from_channel_title,
)
from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.episodes import (
    links_of,
    links_to,
    tmdb_episode_id_column,
    tmdb_episode_link,
    tmdb_record_id_of,
)
from app.tmdb_media.filters import (
    is_not_linked,
)
from app.tmdb_media.keys import same_issuer_clause
from app.tmdb_media.metadata import serve_as_tmdb_episodes
from app.users.models import User


# TODO: Validate
def _tmdb_episode_id(session: Session, episode_id: UUID) -> UUID | None:
    tmdb_link = tmdb_episode_link()
    named = session.exec(
        select(tmdb_episode_id_column(Episode, tmdb_link))  # type: ignore[call-overload]
        .select_from(Episode)
        .outerjoin(tmdb_link, links_of(Episode, tmdb_link))
        .where(Episode.id == episode_id),
    ).all()
    if len(named) != 1:
        return None
    return named[0]


# TODO: Validate
def _tmdb_title_ids_of_episode(
    session: Session,
    tmdb_episode_id: UUID | None,
) -> set[UUID]:
    """Return the canonical titles `tmdb_episode_id` belongs to.

    An episode of a canonical title belongs to that title alone. An episode that
    stands for nothing hangs off a website's own row rather than off a canonical
    title, and that row stands for each of its canonical titles alike, so it belongs
    to every one of them.
    """
    if tmdb_episode_id is None:
        return set()
    own = session.exec(
        select(Title.id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(Episode.id == tmdb_episode_id, is_not_linked(Title)),
    ).all()
    if own:
        return set(own)
    linked = session.exec(
        select(TitleTmdbTitle.tmdb_title_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(
            TitleTmdbTitle,
            col(TitleTmdbTitle.title_id) == col(Season.title_id),
        )
        .where(Episode.id == tmdb_episode_id),
    ).all()
    return set(linked)


# TODO: Validate
class _EpisodeListingColumns(NamedTuple):
    link: Any
    tmdb_episode: Any
    tmdb_episode_id: Any
    listed_season_id: Any
    unlinked: Any


# TODO: Validate
def _episode_listing_columns() -> _EpisodeListingColumns:
    link = tmdb_episode_link()
    tmdb_episode = aliased(Episode)
    return _EpisodeListingColumns(
        link=link,
        tmdb_episode=tmdb_episode,
        tmdb_episode_id=tmdb_episode_id_column(Episode, link),
        listed_season_id=func.coalesce(
            col(tmdb_episode.season_id),
            col(Episode.season_id),
        ),
        unlinked=col(link.tmdb_episode_id).is_(None),
    )


# TODO: Validate
def _listed_season_title_ids(
    session: Session,
    channel_title: ChannelTitle,
    titles: Sequence[Title],
    tmdb_titles: Sequence[Title],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Map each season to the websites' rows carrying it.

    Which seasons a title has is a question about seasons rather than about
    episodes, so it is asked of the database as one: the rows come back a season
    apiece instead of an episode apiece, and a title of thirty thousand episodes
    costs what a title of thirty does.
    """
    title_order = {
        title.id: index for index, title in enumerate([*titles, *tmdb_titles])
    }
    site_title_ids = {title.id for title in titles}
    columns = _episode_listing_columns()

    carried = session.exec(
        select(columns.listed_season_id, Season.title_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.tmdb_episode,
            links_to(columns.tmdb_episode, columns.link),
        )
        .where(
            col(Season.title_id).in_(title_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            or_(
                columns.tmdb_episode_id.in_(
                    _title_episode_id_query(channel_title.tmdb_title_id),
                ),
                and_(
                    columns.unlinked,
                    col(Season.title_id).in_(site_title_ids),
                ),
            ),
        )
        .distinct(),
    ).all()

    season_title_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for season_id, title_id in sorted(
        carried,
        key=lambda pair: title_order[pair[1]],
    ):
        if title_id not in season_title_ids[season_id]:
            season_title_ids[season_id].append(title_id)
    return season_title_ids


# TODO: Validate
def _episode_links_by_tmdb_record_id(
    titles: Sequence[Title],
    listed_episode_ids: Collection[uuid.UUID],
    episode_source_filters: Mapping[
        tuple[uuid.UUID, uuid.UUID],
        ChannelEpisodeSourceFilter,
    ],
    wanted_episode_ids: Collection[uuid.UUID],
) -> tuple[
    dict[uuid.UUID, list[uuid.UUID]],
    dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]],
]:
    """Map each canonical episode of `wanted_episode_ids` to the rows carrying it."""
    episode_title_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for title in titles:
        for season in title.active_children:
            for episode in season.active_children:
                if episode.id not in listed_episode_ids:
                    continue
                episode_id = tmdb_record_id_of(episode)
                if episode_id not in wanted_episode_ids:
                    continue
                if title.id not in episode_title_ids[episode_id]:
                    episode_title_ids[episode_id].append(title.id)
                episode_source_filter = episode_source_filters.get(
                    (episode_id, title.id),
                )
                episode_links[episode_id].append(
                    WhitelistEpisodeLinkOutput.model_validate(
                        episode,
                        update={
                            "title_id": title.id,
                            "episode_id": episode.id,
                            "filtered": episode_source_filter is not None,
                            "expires_at": (
                                episode_source_filter.expires_at
                                if episode_source_filter
                                else None
                            ),
                        },
                        from_attributes=True,
                    ),
                )
    return episode_title_ids, episode_links


# TODO: Validate
def _title_episode_ids(
    session: Session,
    tmdb_title_id: uuid.UUID,
) -> set[uuid.UUID]:
    return set(session.exec(_title_episode_id_query(tmdb_title_id)).all())


# TODO: Validate
def _title_episode_id_query(tmdb_title_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    return (
        select(Episode.id)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(
            Title.id == tmdb_title_id,
            same_issuer_clause(col(Title.key), col(Season.key)),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _seasons_by_id(
    session: Session,
    loaded: Sequence[Season],
    season_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, Season]:
    """Return the row standing for each of `season_ids`, reading in what is missing."""
    seasons = {season.id: season for season in loaded}
    missing = set(season_ids) - seasons.keys()
    if missing:
        seasons.update(
            {
                season.id: season
                for season in session.exec(
                    select(Season).where(col(Season.id).in_(missing)),
                ).all()
            },
        )
    return seasons


# TODO: Validate
def _preload_episode_links(
    session: Session,
    seasons: Sequence[Season],
    episodes: Sequence[Episode],
) -> None:
    season_ids = [season.id for season in seasons]
    if not season_ids:
        return

    links_by_episode: dict[uuid.UUID, list[EpisodeTmdbEpisode]] = defaultdict(list)
    for link in session.exec(
        select(EpisodeTmdbEpisode)
        .join(Episode, col(EpisodeTmdbEpisode.episode_id) == col(Episode.id))
        .where(col(Episode.season_id).in_(season_ids)),
    ).all():
        links_by_episode[link.episode_id].append(link)

    for episode in episodes:
        set_committed_value(
            episode,
            "tmdb_episode_links",
            links_by_episode[episode.id],
        )


# TODO: Validate
def _episode_source_filters(
    channel_title: ChannelTitle,
) -> dict[tuple[uuid.UUID, uuid.UUID], ChannelEpisodeSourceFilter]:
    """Return the entries naming an episode on one website alone.

    Read by the episode and the website together, since that pair is what such
    an entry is about.
    """
    return {
        (
            episode_source_filter.tmdb_episode_id,
            episode_source_filter.title_id,
        ): episode_source_filter
        for episode_source_filter in channel_title.episode_source_filters
    }


# TODO: Validate
def _preload_tmdb_episodes(session: Session, episodes: Sequence[Episode]) -> None:
    episode_ids = [episode.id for episode in episodes]
    if not episode_ids:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(episode_ids))
        .options(
            selectinload(Episode.tmdb_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeTmdbEpisode.tmdb_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
class _SeasonEpisodeRow(NamedTuple):
    id: uuid.UUID
    tmdb_episode_id: uuid.UUID
    title_id: uuid.UUID
    sort_order: int | None


# TODO: Validate
def _season_episode_rows(
    session: Session,
    channel_title: ChannelTitle,
    season_id: uuid.UUID,
) -> list[_SeasonEpisodeRow]:
    titles = titles_from_channel_title(session, channel_title)
    tmdb_titles = tmdb_titles_from_channel_title(session, channel_title)
    if not titles and not tmdb_titles:
        raise HTTPException(status_code=404, detail="Title was not found on channel")

    title_order = {
        title.id: index for index, title in enumerate([*titles, *tmdb_titles])
    }
    site_title_ids = {title.id for title in titles}

    columns = _episode_listing_columns()

    rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Episode.sort_order,
            Season.title_id,
            columns.tmdb_episode_id,
            columns.unlinked,
        )
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.tmdb_episode,
            links_to(columns.tmdb_episode, columns.link),
        )
        .where(
            col(Season.title_id).in_(title_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            columns.listed_season_id == season_id,
        ),
    ).all()

    title_episode_ids = _title_episode_ids(session, channel_title.tmdb_title_id)
    listed = [
        _SeasonEpisodeRow(episode_id, tmdb_record_id, title_id, sort_order)
        for episode_id, sort_order, title_id, tmdb_record_id, unlinked in rows
        if tmdb_record_id in title_episode_ids
        or (unlinked and title_id in site_title_ids)
    ]
    listed.sort(
        key=lambda row: (
            title_order[row.title_id],
            str(row.id),
            str(row.tmdb_episode_id),
        ),
    )
    return listed


# TODO: Validate
def _episodes_by_id(
    session: Session,
    episode_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, Episode]:
    if not episode_ids:
        return {}
    episodes = session.exec(
        select(Episode)
        .where(col(Episode.id).in_(episode_ids))
        .options(
            selectinload(Episode.tmdb_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeTmdbEpisode.tmdb_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()
    return {episode.id: episode for episode in episodes}


# TODO: Validate
def channel_episodes_output(
    channel: Channel,
    channel_options: ChannelOptions,
    user: User | None,
    session: Session,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    output = ChannelEpisodesOutput(
        episodes=[],
        seasons={},
        titles={},
        sources={},
        plugins={},
    )

    start = time.time()

    builder = EpisodeQueryBuilder(session, channel, channel_options, user)
    results = builder.get_episodes()

    source_keys: dict[uuid.UUID, str] = {}
    for result in results:
        episode = result.episode
        season = episode.season
        title = season.title
        source = title.source
        plugin = source.plugin
        source_keys[episode.id] = source.key

        extras: dict[str, Any] = {
            "channel_id": result.channel_id,
            "channel_ids": result.channel_ids,
        }
        # An episode nothing was minted for it to be linked to is the episode
        # itself, so it is served under its own id rather than under nothing.
        fields = episode.model_dump()
        fields["tmdb_episode_id"] = tmdb_record_id_of(episode)
        if result.latest_watch:
            extras["watch_date"] = result.latest_watch.watch_date
            extras["verified"] = result.latest_watch.verified
            extras["episode_watch_id"] = result.latest_watch.id

        output.episodes.append(
            EpisodeWithDetails(**fields, **extras),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = ChannelEpisodeSeason.model_validate(
                season,
            )
        if season.title_id not in output.titles:
            output.titles[season.title_id] = ChannelEpisodeTitle.model_validate(title)
        # The website is read off the row itself rather than off the id column on
        # the listing, which a title leaves empty. Only listings are ever here,
        # so the two say the same thing and only one of them says it in a type.
        if source.id not in output.sources:
            output.sources[source.id] = ChannelEpisodeSource.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = ChannelEpisodePlugin.model_validate(
                plugin,
            )

    serve_as_tmdb_episodes(session, output.episodes)
    custom_source = apply_user_episode_urls(
        session,
        user,
        output.episodes,
        source_keys,
        builder.source_config,
        channel_options,
    )
    if custom_source:
        output.sources[custom_source.id] = ChannelEpisodeSource.model_validate(
            custom_source,
        )
        output.plugins[custom_source.plugin_id] = ChannelEpisodePlugin.model_validate(
            custom_source.plugin,
        )

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output
