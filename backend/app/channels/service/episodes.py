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
    ChannelShow,
)
from app.channels.schemas import (
    ChannelEpisodePlugin,
    ChannelEpisodeSeason,
    ChannelEpisodeShow,
    ChannelEpisodeSource,
    ChannelEpisodesOutput,
    ChannelOptions,
    EpisodeWithDetails,
    WhitelistEpisodeLinkOutput,
)
from app.channels.service.shows import (
    shows_for_channel_show,
    tmdb_shows_for_channel_show,
)
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
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
def _canonical_show_ids_of_episode(
    session: Session,
    canonical_episode_id: UUID | None,
) -> set[UUID]:
    """Return the canonical shows `canonical_episode_id` belongs to.

    An episode of a canonical show belongs to that show alone. An episode that
    stands for nothing hangs off a website's own row rather than off a canonical
    show, and that row stands for each of its canonical shows alike, so it belongs
    to every one of them.
    """
    if canonical_episode_id is None:
        return set()
    own = session.exec(
        select(Show.id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(Episode.id == canonical_episode_id, is_canonical(Show)),
    ).all()
    if own:
        return set(own)
    linked = session.exec(
        select(ShowCanonicalShow.canonical_show_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Season.show_id))
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
def _listed_season_show_ids(
    session: Session,
    channel_show: ChannelShow,
    shows: Sequence[Show],
    tmdb_shows: Sequence[Show],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Map each season to the websites' rows carrying it.

    A season a website announced and never filled is named by that website
    alone, since there is no episode under it to say who carries it.

    Which seasons a title has is a question about seasons rather than about
    episodes, so it is asked of the database as one: the rows come back a season
    apiece instead of an episode apiece, and a title of thirty thousand episodes
    costs what a title of thirty does.
    """
    show_order = {show.id: index for index, show in enumerate([*shows, *tmdb_shows])}
    site_show_ids = {show.id for show in shows}
    columns = _episode_listing_columns()

    carried = session.exec(
        select(columns.listed_season_id, Season.show_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.canonical_episode,
            links_to(columns.canonical_episode, columns.link),
        )
        .where(
            col(Season.show_id).in_(show_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            or_(
                columns.canonical_episode_id.in_(
                    _title_episode_id_query(channel_show.canonical_show_id),
                ),
                and_(
                    columns.unlinked,
                    col(Season.show_id).in_(site_show_ids),
                ),
            ),
        )
        .distinct(),
    ).all()

    announced = session.exec(
        select(Season.id, Season.show_id).where(
            col(Season.show_id).in_(show_order),
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

    season_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for season_id, show_id in sorted(
        [*carried, *announced],
        key=lambda pair: show_order[pair[1]],
    ):
        if show_id not in season_show_ids[season_id]:
            season_show_ids[season_id].append(show_id)
    return season_show_ids


# TODO: Validate
def _episode_links_by_canonical_id(
    shows: Sequence[Show],
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
    episode_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for show in shows:
        for season in show.active_children:
            for episode in season.active_children:
                if episode.id not in listed_episode_ids:
                    continue
                episode_id = canonical_id_of(episode)
                if episode_id not in wanted_episode_ids:
                    continue
                if show.id not in episode_show_ids[episode_id]:
                    episode_show_ids[episode_id].append(show.id)
                episode_source_filter = episode_source_filters.get(
                    (episode_id, show.id),
                )
                episode_links[episode_id].append(
                    WhitelistEpisodeLinkOutput.model_validate(
                        episode,
                        update={
                            "show_id": show.id,
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
    return episode_show_ids, episode_links


# TODO: Validate
def _title_episode_ids(
    session: Session,
    canonical_show_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Return the episodes the title itself holds, as against a website's own.

    A website files seasons under a title the title has no record of, and a
    canonical season is minted for each so its episodes have somewhere to hang,
    which leaves rows under the title that the title does not hold. They are
    told apart by who issued the season, the way `EpisodeQueryBuilder` tells
    them apart.
    """
    return set(session.exec(_title_episode_id_query(canonical_show_id)).all())


# TODO: Validate
def _title_episode_id_query(canonical_show_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    return (
        select(Episode.id)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(
            Show.id == canonical_show_id,
            same_issuer_clause(col(Show.key), col(Season.key)),
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
    channel_show: ChannelShow,
) -> dict[tuple[uuid.UUID, uuid.UUID], ChannelEpisodeSourceFilter]:
    """Return the entries naming an episode on one website alone.

    Read by the episode and the website together, since that pair is what such
    an entry is about.
    """
    return {
        (
            episode_source_filter.canonical_episode_id,
            episode_source_filter.show_id,
        ): episode_source_filter
        for episode_source_filter in channel_show.episode_source_filters
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
    show_id: uuid.UUID
    sort_order: int | None


# TODO: Validate
def _season_episode_rows(
    session: Session,
    channel_show: ChannelShow,
    season_id: uuid.UUID,
) -> list[_SeasonEpisodeRow]:
    shows = shows_for_channel_show(session, channel_show)
    tmdb_shows = tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    show_order = {show.id: index for index, show in enumerate([*shows, *tmdb_shows])}
    site_show_ids = {show.id for show in shows}

    columns = _episode_listing_columns()

    rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Episode.sort_order,
            Season.show_id,
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
            col(Season.show_id).in_(show_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            columns.listed_season_id == season_id,
        ),
    ).all()

    title_episode_ids = _title_episode_ids(session, channel_show.canonical_show_id)
    listed = [
        _SeasonEpisodeRow(episode_id, canonical_id, show_id, sort_order)
        for episode_id, sort_order, show_id, canonical_id, unlinked in rows
        if canonical_id in title_episode_ids or (unlinked and show_id in site_show_ids)
    ]
    listed.sort(
        key=lambda row: (
            show_order[row.show_id],
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
        shows={},
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
        show = season.show
        source = show.source
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
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ChannelEpisodeShow.model_validate(show)
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
