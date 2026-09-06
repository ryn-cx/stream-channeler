# TODO: Validate


import time
import uuid
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from typing import Any, NamedTuple
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    canonical_id_of,
    links_of,
    links_to,
)
from app.canonical_media.filters import (
    is_canonical,
)
from app.canonical_media.keys import same_issuer_clause
from app.canonical_media.metadata import serve_as_canonical_episodes
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
    titles_for_channel_title,
    tmdb_titles_for_channel_title,
)
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.seasons.models import Season
from app.titles.models import Title, TitleCanonicalTitle
from app.users.models import User


# TODO: Validate
def _canonical_episode_id(session: Session, episode_id: UUID) -> UUID | None:
    """Return the canonical episode `episode_id` stands for, which a filter names.

    A row standing for nothing is the episode itself, so it names itself. A row
    standing for more than one names none of them, since a filter holds one
    episode and there is no saying which of them was meant.
    """
    canonical_link = canonical_episode_link()
    named = session.exec(
        select(canonical_episode_id_column(Episode, canonical_link))  # type: ignore[call-overload]
        .select_from(Episode)
        .outerjoin(canonical_link, links_of(Episode, canonical_link))
        .where(Episode.id == episode_id),
    ).all()
    if len(named) != 1:
        return None
    return named[0]


# TODO: Validate
def _canonical_title_ids_of_episode(
    session: Session,
    canonical_episode_id: UUID | None,
) -> set[UUID]:
    """Return the canonical titles `canonical_episode_id` belongs to.

    An episode of a canonical title belongs to that title alone. An episode that
    stands for nothing hangs off a website's own row rather than off a canonical
    title, and that row stands for each of its canonical titles alike, so it belongs
    to every one of them.
    """
    if canonical_episode_id is None:
        return set()
    own = session.exec(
        select(Title.id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(Episode.id == canonical_episode_id, is_canonical(Title)),
    ).all()
    if own:
        return set(own)
    linked = session.exec(
        select(TitleCanonicalTitle.canonical_title_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(
            TitleCanonicalTitle,
            col(TitleCanonicalTitle.title_id) == col(Season.title_id),
        )
        .where(Episode.id == canonical_episode_id),
    ).all()
    return set(linked)


# TODO: Validate
class _EpisodeListingColumns(NamedTuple):
    link: Any
    canonical_episode: Any
    canonical_episode_id: Any
    listed_season_id: Any
    unlinked: Any


# TODO: Validate
def _episode_listing_columns() -> _EpisodeListingColumns:
    """Return what an `Episode` row is listed as, as columns to select or filter on.

    A row standing for exactly one episode is listed as that episode and under
    the season holding it; a row standing for none or for several answers for
    itself, since neither of the others is an episode it can be folded into.
    """
    link = canonical_episode_link()
    canonical_episode = aliased(Episode)
    return _EpisodeListingColumns(
        link=link,
        canonical_episode=canonical_episode,
        canonical_episode_id=canonical_episode_id_column(Episode, link),
        listed_season_id=func.coalesce(
            col(canonical_episode.season_id),
            col(Episode.season_id),
        ),
        unlinked=col(link.canonical_episode_id).is_(None),
    )


# TODO: Validate
def _listed_season_title_ids(
    session: Session,
    channel_title: ChannelTitle,
    titles: Sequence[Title],
    tmdb_titles: Sequence[Title],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Map each season to the websites' rows carrying it.

    A season a website announced and never filled is named by that website
    alone, since there is no episode under it to say who carries it.

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
            columns.canonical_episode,
            links_to(columns.canonical_episode, columns.link),
        )
        .where(
            col(Season.title_id).in_(title_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            or_(
                columns.canonical_episode_id.in_(
                    _title_episode_id_query(channel_title.canonical_title_id),
                ),
                and_(
                    columns.unlinked,
                    col(Season.title_id).in_(site_title_ids),
                ),
            ),
        )
        .distinct(),
    ).all()

    announced = session.exec(
        select(Season.id, Season.title_id).where(
            col(Season.title_id).in_(title_order),
            col(Season.deleted_at).is_(None),
            ~exists(
                select(Episode.id)
                .where(
                    col(Episode.season_id) == col(Season.id),
                    col(Episode.deleted_at).is_(None),
                )
                .correlate(Season),
            ),
        ),
    ).all()

    season_title_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for season_id, title_id in sorted(
        [*carried, *announced],
        key=lambda pair: title_order[pair[1]],
    ):
        if title_id not in season_title_ids[season_id]:
            season_title_ids[season_id].append(title_id)
    return season_title_ids


# TODO: Validate
def _episode_links_by_canonical_id(
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
                episode_id = canonical_id_of(episode)
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
    canonical_title_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Return the episodes the title itself holds, as against a website's own.

    A website files seasons under a title the title has no record of, and a
    canonical season is minted for each so its episodes have somewhere to hang,
    which leaves rows under the title that the title does not hold. They are
    told apart by who issued the season, the way `EpisodeQueryBuilder` tells
    them apart.
    """
    return set(session.exec(_title_episode_id_query(canonical_title_id)).all())


# TODO: Validate
def _title_episode_id_query(canonical_title_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    return (
        select(Episode.id)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(
            Title.id == canonical_title_id,
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

    links_by_episode: dict[uuid.UUID, list[EpisodeCanonicalEpisode]] = defaultdict(list)
    for link in session.exec(
        select(EpisodeCanonicalEpisode)
        .join(Episode, col(EpisodeCanonicalEpisode.episode_id) == col(Episode.id))
        .where(col(Episode.season_id).in_(season_ids)),
    ).all():
        links_by_episode[link.episode_id].append(link)

    for episode in episodes:
        set_committed_value(
            episode,
            "canonical_episode_links",
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
            episode_source_filter.canonical_episode_id,
            episode_source_filter.title_id,
        ): episode_source_filter
        for episode_source_filter in channel_title.episode_source_filters
    }


# TODO: Validate
def _preload_canonical_episodes(session: Session, episodes: Sequence[Episode]) -> None:
    """Read in the episode each of `episodes` is linked to, in one query.

    `Episode.tmdb_id` walks from a row to the episode it is linked to, which is a
    query apiece where the rows are read one at a time. An `Episode` is keyed on
    its season and its own key rather than on `id`, so the walk cannot be
    answered out of the session and has to be asked for together up front.
    """
    episode_ids = [episode.id for episode in episodes]
    if not episode_ids:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(episode_ids))
        .options(
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
class _SeasonEpisodeRow(NamedTuple):
    id: uuid.UUID
    canonical_episode_id: uuid.UUID
    title_id: uuid.UUID
    sort_order: int | None


# TODO: Validate
def _season_episode_rows(
    session: Session,
    channel_title: ChannelTitle,
    season_id: uuid.UUID,
) -> list[_SeasonEpisodeRow]:
    titles = titles_for_channel_title(session, channel_title)
    tmdb_titles = tmdb_titles_for_channel_title(session, channel_title)
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
            columns.canonical_episode_id,
            columns.unlinked,
        )
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.canonical_episode,
            links_to(columns.canonical_episode, columns.link),
        )
        .where(
            col(Season.title_id).in_(title_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            columns.listed_season_id == season_id,
        ),
    ).all()

    title_episode_ids = _title_episode_ids(session, channel_title.canonical_title_id)
    listed = [
        _SeasonEpisodeRow(episode_id, canonical_id, title_id, sort_order)
        for episode_id, sort_order, title_id, canonical_id, unlinked in rows
        if canonical_id in title_episode_ids
        or (unlinked and title_id in site_title_ids)
    ]
    listed.sort(
        key=lambda row: (
            title_order[row.title_id],
            str(row.id),
            str(row.canonical_episode_id),
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
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
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
        fields["canonical_episode_id"] = canonical_id_of(episode)
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

    serve_as_canonical_episodes(session, output.episodes)
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
