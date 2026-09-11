# TODO: Validate


import uuid
from collections import defaultdict
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
    ChannelSeasonFilter,
    ChannelSourceFilter,
    ChannelTitle,
)
from app.channels.schemas import (
    BlacklistEpisodeInput,
    WhitelistEpisodeLinkOutput,
    WhitelistEpisodeOutput,
    WhitelistEpisodesOutput,
    WhitelistSeasonOutput,
    WhitelistSourceOutput,
    WhitelistTitleInput,
    WhitelistTitleOutput,
)
from app.channels.service.episodes import (
    _episode_links_by_tmdb_record_id,
    _episode_source_filters,
    _episodes_by_id,
    _listed_season_title_ids,
    _preload_episode_links,
    _season_episode_rows,
    _SeasonEpisodeRow,
    _seasons_by_id,
    _title_episode_ids,
    _tmdb_episode_id,
    _tmdb_title_ids_of_episode,
)
from app.channels.service.ordering import (
    _episode_sort_key,
    _season_sort_key,
    _tmdb_orders,
)
from app.channels.service.titles import (
    titles_from_channel_title,
    tmdb_titles_from_channel_title,
)
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.schemas import Message
from app.seasons.models import Season
from app.titles.models import Title
from app.titles.schemas import TitlePublic
from app.tmdb_media.episodes import (
    tmdb_record_id_of,
)
from app.tmdb_media.metadata import serve_as_tmdb_episodes
from app.tmdb_media.seasons import season_ids_by_episode

# How many of a season's episodes are read at once on the filter page.
WHITELIST_EPISODE_PAGE = 100


# TODO: Validate
def update_whitelist(
    session: Session,
    channel_title: ChannelTitle,
    config: WhitelistTitleInput,
) -> None:
    """Update whitelist records for a channel title."""
    if config.is_whitelist is not None:
        channel_title.is_whitelist = config.is_whitelist

    existing_sources = {source.title_id for source in channel_title.source_filters}
    existing_seasons = {season.season_id for season in channel_title.season_filters}
    existing_episodes = {
        episode.tmdb_episode_id for episode in channel_title.episode_filters
    }
    existing_episode_sources = {
        (episode_source.tmdb_episode_id, episode_source.title_id)
        for episode_source in channel_title.episode_source_filters
    }

    for source in config.sources:
        toggle_source_whitelist(
            session,
            channel_title,
            source.id,
            existing_sources,
            marked=source.marked,
        )
    for season in config.seasons:
        toggle_season_whitelist(
            session,
            channel_title,
            season.id,
            existing_seasons,
            marked=season.marked,
        )
    for episode in config.episodes:
        toggle_episode_whitelist(
            session,
            channel_title,
            _tmdb_episode_id(session, episode.id),
            existing_episodes,
            marked=episode.marked,
            expires_at=episode.expires_at,
        )
    for episode_source in config.episode_sources:
        toggle_episode_source_whitelist(
            session,
            channel_title,
            _tmdb_episode_id(session, episode_source.episode_id),
            episode_source.title_id,
            existing_episode_sources,
            marked=episode_source.marked,
            expires_at=episode_source.expires_at,
        )

    session.commit()


# TODO: Validate
def toggle_source_whitelist(
    session: Session,
    channel_title: ChannelTitle,
    title_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    """Mark or unmark one website's row for the title `channel_title` is about."""
    if marked and title_id not in existing:
        channel_title.source_filters.append(
            ChannelSourceFilter(
                channel_title_id=channel_title.id,
                title_id=title_id,
            ),
        )
    elif not marked and title_id in existing:
        existing_source = ChannelSourceFilter.get(session, channel_title, title_id)
        if existing_source:
            session.delete(existing_source)


# TODO: Validate
def toggle_season_whitelist(
    session: Session,
    channel_title: ChannelTitle,
    season_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    """Add or drop the filter naming the season `season_id`."""
    if marked and season_id not in existing:
        channel_title.season_filters.append(
            ChannelSeasonFilter(
                channel_title_id=channel_title.id,
                season_id=season_id,
            ),
        )
    elif not marked and season_id in existing:
        existing_season = ChannelSeasonFilter.get(session, channel_title, season_id)
        if existing_season:
            session.delete(existing_season)


# TODO: Validate
def toggle_episode_whitelist(  # noqa: PLR0913 - mirrors toggle_season_whitelist plus expiry
    session: Session,
    channel_title: ChannelTitle,
    tmdb_episode_id: UUID | None,
    existing: set[UUID],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    """Add, re-expire or drop the filter naming `tmdb_episode_id`."""
    if tmdb_episode_id is None:
        return
    if marked and tmdb_episode_id not in existing:
        channel_title.episode_filters.append(
            ChannelEpisodeFilter(
                channel_title_id=channel_title.id,
                tmdb_episode_id=tmdb_episode_id,
                expires_at=expires_at,
            ),
        )
    elif marked and tmdb_episode_id in existing:
        # Re-marking an existing entry updates its expiry.
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_title,
            tmdb_episode_id,
        )
        if existing_episode:
            existing_episode.expires_at = expires_at
    elif not marked and tmdb_episode_id in existing:
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_title,
            tmdb_episode_id,
        )
        if existing_episode:
            session.delete(existing_episode)


# TODO: Validate
def toggle_episode_source_whitelist(  # noqa: PLR0913 - mirrors toggle_episode_whitelist plus the website
    session: Session,
    channel_title: ChannelTitle,
    tmdb_episode_id: UUID | None,
    title_id: UUID,
    existing: set[tuple[UUID, UUID]],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    """Add, re-expire or drop the entry naming `tmdb_episode_id` on `title_id`."""
    if tmdb_episode_id is None:
        return
    key = (tmdb_episode_id, title_id)
    if marked and key not in existing:
        channel_title.episode_source_filters.append(
            ChannelEpisodeSourceFilter(
                channel_title_id=channel_title.id,
                tmdb_episode_id=tmdb_episode_id,
                title_id=title_id,
                expires_at=expires_at,
            ),
        )
        return
    if key not in existing:
        return
    existing_entry = ChannelEpisodeSourceFilter.get(
        session,
        channel_title,
        tmdb_episode_id,
        title_id,
    )
    if not existing_entry:
        return
    if marked:
        # Re-marking an existing entry updates its expiry.
        existing_entry.expires_at = expires_at
    else:
        session.delete(existing_entry)


# TODO: Validate
def blacklist_episode_on_channel(
    session: Session,
    channel: Channel,
    title: Title,
    episode_id: UUID,
    expires_at: datetime | None = None,
) -> list[ChannelTitle]:
    """Blacklist a single episode for `channel`.

    Gets or creates the `ChannelTitle` for the canonical title the episode belongs
    to, which is the episode's own answer rather than its row's: a row that mixes
    titles holds episodes of each of them, and hiding one of its episodes is about
    the canonical title that episode belongs to. An episode nothing was minted for
    it to stand for has no canonical title of its own to answer with, and its row
    stands for each of its canonical titles alike, so the episode is hidden under
    every one of them. A newly created `ChannelTitle` is a filter-only title
    (`is_blacklist_only=True`) in blacklist mode, so the canonical title's other
    episodes are not pulled into the channel. Adds (or updates the expiry of) a
    `ChannelEpisodeFilter` for the episode, which covers that episode on every
    website the canonical title is on.
    """
    tmdb_episode_id = _tmdb_episode_id(session, episode_id)
    tmdb_title_ids = _tmdb_title_ids_of_episode(
        session,
        tmdb_episode_id,
    ) or set(title.tmdb_title_ids)

    channel_titles: list[ChannelTitle] = []
    for tmdb_title_id in tmdb_title_ids:
        channel_title = ChannelTitle.get(session, channel, tmdb_title_id)
        if channel_title is None:
            channel_title = ChannelTitle(
                channel_id=channel.id,
                tmdb_title_id=tmdb_title_id,
                is_whitelist=False,
                is_blacklist_only=True,
            )
            session.add(channel_title)

        existing_filter = ChannelEpisodeFilter.get(
            session,
            channel_title,
            tmdb_episode_id,
        )
        if existing_filter is None:
            channel_title.episode_filters.append(
                ChannelEpisodeFilter(
                    channel_title_id=channel_title.id,
                    tmdb_episode_id=tmdb_episode_id,
                    expires_at=expires_at,
                ),
            )
        else:
            existing_filter.expires_at = expires_at
        channel_titles.append(channel_title)

    session.commit()
    for channel_title in channel_titles:
        session.refresh(channel_title)
    return channel_titles


# TODO: Validate
class _WhitelistMedia(NamedTuple):
    """The rows a title's filters are read against, gathered once per request."""

    titles: list[Title]
    tmdb_titles: list[Title]
    site_seasons: list[Season]
    tmdb_seasons: list[Season]
    # Which season each episode belongs to, keyed by the website's own row.
    episode_seasons: dict[uuid.UUID, uuid.UUID]
    # The rows that stand for one of the title's own episodes, and so are the
    # ones a filter can name.
    listed_episode_ids: set[uuid.UUID]


# TODO: Validate
def _whitelist_media(
    session: Session,
    channel_title: ChannelTitle,
) -> _WhitelistMedia:
    """Gather the websites' rows for the title `channel_title` is about."""
    titles = titles_from_channel_title(session, channel_title)
    # TMDB is not a website the title can be watched on, so it is not one of the
    # non-canonical rows the rows are built from, and only stands for the seasons it has
    # a record of, which is all an announced season no site has filled yet can be named
    # by. A title no website carries at all has nothing else to be listed from, so there
    # its record is the whole of what there is rather than the remainder.
    tmdb_titles = tmdb_titles_from_channel_title(session, channel_title)
    if not titles and not tmdb_titles:
        raise HTTPException(status_code=404, detail="Title was not found on channel")

    # Every season and episode under those rows is walked below, which is a query
    # a season unless they are asked for together up front.
    session.exec(
        select(Title)
        .where(col(Title.id).in_([title.id for title in [*titles, *tmdb_titles]]))
        .options(selectinload(Title.seasons).selectinload(Season.episodes)),
    ).all()

    site_seasons = [season for title in titles for season in title.active_children]
    tmdb_seasons = [season for title in tmdb_titles for season in title.active_children]
    all_episodes = [
        episode
        for season in [*site_seasons, *tmdb_seasons]
        for episode in season.active_children
    ]
    _preload_episode_links(session, site_seasons + tmdb_seasons, all_episodes)
    # Which season an episode belongs to is the canonical episode's answer, since
    # a site can file an episode under a season the canonical hierarchy does not,
    # which is what puts a site's finale in another site's specials.
    episode_seasons = season_ids_by_episode(session, all_episodes)
    # Where a website files two titles under one listing it carries another title's
    # episodes as well. What a channel offers is the title's own episodes, so a
    # non-canonical row's episode is listed only where the episode it is linked to is
    # one of them. An episode that is linked to nothing is one the title had no record
    # of to match it against, and the link its listing carries is the only word there is
    # on what title it belongs to, so it is listed too.
    title_episode_ids = _title_episode_ids(session, channel_title.tmdb_title_id)
    site_season_ids = {season.id for season in site_seasons}
    listed_episode_ids = {
        episode.id
        for episode in all_episodes
        if tmdb_record_id_of(episode) in title_episode_ids
        or (
            not episode.tmdb_episode_links and episode.season_id in site_season_ids
        )
    }
    return _WhitelistMedia(
        titles=titles,
        tmdb_titles=tmdb_titles,
        site_seasons=site_seasons,
        tmdb_seasons=tmdb_seasons,
        episode_seasons=episode_seasons,
        listed_episode_ids=listed_episode_ids,
    )


# TODO: Validate
def channel_whitelist_output(
    session: Session,
    channel_title: ChannelTitle,
) -> WhitelistTitleOutput:
    """Read the sites and seasons of a title's filters in a channel.

    A filter is about the media rather than one website's non-canonical row of it, so
    every non-canonical row's seasons are listed, with the non-canonical rows of the
    same season collapsed into the one row the filter applies to. The episodes are read
    separately, a season at a time, since a title's whole catalogue is far more than the
    page opens on.
    """
    enabled_sources = {x.title_id for x in channel_title.source_filters}
    enabled_seasons = {x.season_id for x in channel_title.season_filters}

    titles = titles_from_channel_title(session, channel_title)
    tmdb_titles = tmdb_titles_from_channel_title(session, channel_title)
    if not titles and not tmdb_titles:
        raise HTTPException(status_code=404, detail="Title was not found on channel")

    # The websites' rows carrying each season, so a row can name the sites it
    # came from.
    season_title_ids = _listed_season_title_ids(
        session,
        channel_title,
        titles,
        tmdb_titles,
    )

    sources = [
        WhitelistSourceOutput(
            title_id=title.id,
            source_id=title.source.id,
            source_key=title.source.key,
            favicon_url=title.source.favicon_url,
            title=TitlePublic.model_validate(title),
            filtered=title.id in enabled_sources,
            is_tmdb=title.source.plugin.key == TMDB_PLUGIN_KEY,
        )
        for title in [*titles, *tmdb_titles]
    ]

    # The rows are the title's own seasons rather than the websites' non-canonical rows
    # of them, since a filter names a season of the title.
    title_seasons = session.exec(
        select(Season).where(
            Season.title_id == channel_title.tmdb_title_id,
            col(Season.deleted_at).is_(None),
        ),
    ).all()
    season_rows = _seasons_by_id(session, title_seasons, season_title_ids)

    seasons: list[WhitelistSeasonOutput] = []
    listed_seasons: set[uuid.UUID] = set()

    # TODO: Validate
    def list_season(season_id: uuid.UUID) -> None:
        if season_id in listed_seasons:
            return
        listed_seasons.add(season_id)
        seasons.append(
            WhitelistSeasonOutput.model_validate(
                season_rows[season_id],
                update={
                    "filtered": season_id in enabled_seasons,
                    "title_ids": season_title_ids[season_id],
                },
            ),
        )

    for season in title_seasons:
        if season.id in season_title_ids:
            list_season(season.id)

    # A season the title has no row of is listed after the ones it does, in the
    # order the seasons themselves read in, so a page boundary and a listing
    # both fall the same way on every request.
    for season_id in sorted(
        season_title_ids,
        key=lambda key: _season_sort_key(season_rows[key]),
    ):
        list_season(season_id)

    return WhitelistTitleOutput.model_validate(
        (titles or tmdb_titles)[0],
        update={
            "is_whitelist": channel_title.is_whitelist,
            "sources": sources,
            "seasons": seasons,
        },
    )


# TODO: Validate
def channel_whitelist_episodes_output(
    session: Session,
    channel_title: ChannelTitle,
    season_id: uuid.UUID,
    offset: int = 0,
    limit: int = WHITELIST_EPISODE_PAGE,
) -> WhitelistEpisodesOutput:
    """Read one page of a season's episodes, as the filter page expands it.

    A filter is about the media rather than one website's non-canonical row of it, so
    the non-canonical rows of an episode are collapsed into the one row the filter
    applies to, and each non-canonical row is carried alongside as a link of its own.
    """
    enabled_episodes = {x.tmdb_episode_id for x in channel_title.episode_filters}
    episode_expiries = {
        episode_filter.tmdb_episode_id: episode_filter.expires_at
        for episode_filter in channel_title.episode_filters
    }

    # An episode is listed once under every season row carrying it, since two seasons
    # sharing an episode each have it to filter on. Only the non-canonical rows of it
    # under the same row are folded together.
    rows = _season_episode_rows(session, channel_title, season_id)
    representatives: dict[uuid.UUID, _SeasonEpisodeRow] = {}
    for row in rows:
        representatives.setdefault(row.tmdb_episode_id, row)

    # Ordered and paged as the stored rows, since reading one as the schema is
    # work per episode and only the page being served is ever read.
    tmdb_orders = _tmdb_orders(session, representatives)
    page_rows = sorted(
        representatives.values(),
        key=lambda row: _episode_sort_key(
            row,
            tmdb_orders.get(row.tmdb_episode_id),
        ),
    )[offset : offset + limit]

    # Only the page being served is asked after: the links a row carries and the
    # reading of it as the media are both work per episode, and a season of a
    # thousand is not a season anybody reads at once.
    page_tmdb_record_ids = {row.tmdb_episode_id for row in page_rows}
    link_rows = [row for row in rows if row.tmdb_episode_id in page_tmdb_record_ids]
    episodes = _episodes_by_id(session, [row.id for row in link_rows])

    episode_source_filters = _episode_source_filters(channel_title)
    episode_title_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for row in link_rows:
        if row.title_id not in episode_title_ids[row.tmdb_episode_id]:
            episode_title_ids[row.tmdb_episode_id].append(row.title_id)
        episode_source_filter = episode_source_filters.get(
            (row.tmdb_episode_id, row.title_id),
        )
        episode_links[row.tmdb_episode_id].append(
            WhitelistEpisodeLinkOutput.model_validate(
                episodes[row.id],
                update={
                    "title_id": row.title_id,
                    "episode_id": row.id,
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

    page = [
        WhitelistEpisodeOutput.model_validate(
            episodes[row.id],
            update={
                "season_id": season_id,
                "tmdb_episode_id": row.tmdb_episode_id,
                "filtered": row.tmdb_episode_id in enabled_episodes,
                "expires_at": episode_expiries.get(row.tmdb_episode_id),
                "title_ids": episode_title_ids[row.tmdb_episode_id],
                "links": episode_links[row.tmdb_episode_id],
            },
        )
        for row in page_rows
    ]

    serve_as_tmdb_episodes(session, page)

    return WhitelistEpisodesOutput(episodes=page, total_count=len(representatives))


# TODO: Validate
def filtered_whitelist_episodes(
    session: Session,
    channel_title: ChannelTitle,
) -> list[WhitelistEpisodeOutput]:
    """Read the episodes of a title that an entry names, whatever season they are in.

    The entries are what is being listed rather than the title's catalogue, so
    this stays small however many episodes the title has, which is what lets the
    blacklist be read without paging through everything it does not name.
    """
    enabled_episodes = {x.tmdb_episode_id for x in channel_title.episode_filters}
    if not enabled_episodes:
        return []

    episode_expiries = {
        episode_filter.tmdb_episode_id: episode_filter.expires_at
        for episode_filter in channel_title.episode_filters
    }

    media = _whitelist_media(session, channel_title)

    episodes: list[WhitelistEpisodeOutput] = []
    seen_episodes: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for season in [*media.site_seasons, *media.tmdb_seasons]:
        for episode in season.active_children:
            if episode.id not in media.listed_episode_ids:
                continue
            tmdb_episode_id = tmdb_record_id_of(episode)
            if tmdb_episode_id not in enabled_episodes:
                continue
            episode_season_id = media.episode_seasons[episode.id]
            if (episode_season_id, tmdb_episode_id) in seen_episodes:
                continue
            seen_episodes.add((episode_season_id, tmdb_episode_id))
            episodes.append(
                WhitelistEpisodeOutput.model_validate(
                    episode,
                    update={
                        "season_id": episode_season_id,
                        "tmdb_episode_id": tmdb_episode_id,
                        "filtered": True,
                        "expires_at": episode_expiries.get(tmdb_episode_id),
                        "title_ids": [],
                        "links": [],
                    },
                ),
            )

    tmdb_orders = _tmdb_orders(session, enabled_episodes)
    episodes.sort(
        key=lambda episode: _episode_sort_key(
            episode,
            tmdb_orders.get(episode.tmdb_episode_id),
        ),
    )
    episode_title_ids, episode_links = _episode_links_by_tmdb_record_id(
        [*media.titles, *media.tmdb_titles],
        media.listed_episode_ids,
        _episode_source_filters(channel_title),
        enabled_episodes,
    )
    for episode_output in episodes:
        episode_output.title_ids = episode_title_ids[
            episode_output.tmdb_episode_id
        ]
        episode_output.links = episode_links[episode_output.tmdb_episode_id]

    serve_as_tmdb_episodes(session, episodes)
    return episodes


# TODO: Validate
def update_whitelist_output(
    session: Session,
    whitelist_config: WhitelistTitleInput,
    channel_title: ChannelTitle,
) -> WhitelistTitleOutput:
    """Update the whitelist/blacklist for a title in a channel."""
    update_whitelist(session, channel_title, whitelist_config)
    # Build the response before any cleanup so it stays valid even if the
    # channel-title is removed below.
    output = channel_whitelist_output(session, channel_title)
    # A filter-only title that no longer hides anything serves no purpose, so drop it
    # to keep the channel's title list clean.
    if (
        channel_title.is_blacklist_only
        and not channel_title.source_filters
        and not channel_title.season_filters
        and not channel_title.episode_filters
    ):
        session.delete(channel_title)
        session.commit()
    return output


# TODO: Validate
def blacklist_episode_by_title_id(
    session: Session,
    channel: Channel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`.

    When the title is not already on the channel a filter-only `ChannelTitle` is
    created so the episode can be hidden without making the whole title a member of the
    channel. An optional `expires_at` makes the blacklist temporary.
    """
    # Title's primary key is (source_id, key), so look it up by its id column.
    title = session.exec(
        select(Title).where(Title.id == blacklist_in.title_id),
    ).first()
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")

    blacklist_episode_on_channel(
        session=session,
        channel=channel,
        title=title,
        episode_id=blacklist_in.episode_id,
        expires_at=blacklist_in.expires_at,
    )
    return Message(message="Episode blacklisted successfully")
