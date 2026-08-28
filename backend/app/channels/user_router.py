# TODO: Validate


import time
import uuid
from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlmodel import col, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.canonical_media.episodes import (
    canonical_id_of,
)
from app.canonical_media.metadata import (
    serve_as_canonical_episodes,
)
from app.channels import service
from app.channels.channel_scope import (
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelCanonicalShow,
    ReadableChannel,
    ReadableChannelCanonicalShow,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
    apply_user_episode_urls,
)
from app.channels.models import (
    Channel,
    ChannelFavorite,
    ChannelQueue,
    ChannelShow,
)
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelFavoriteUpdate,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelQueueOutput,
    ChannelReadOptions,
    ChannelShowGroup,
    ChannelShowMembership,
    ChannelShowsOutput,
    ChannelsPublic,
    ChannelUpdate,
    CombinedChannelInput,
    CombinedChannelOutput,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEpisodeLinkOutput,
    WhitelistEpisodeOutput,
    WhitelistEpisodesOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
    WhitelistSourceOutput,
)
from app.channels.service import (
    _canonical_orders,
    _canonical_shows,
    _canonical_sources,
    _channel_show_stats,
    _episode_links_by_canonical_id,
    _episode_sort_key,
    _episode_source_filters,
    _episodes_by_id,
    _listed_season_show_ids,
    _season_episode_rows,
    _season_sort_key,
    _SeasonEpisodeRow,
    _seasons_by_id,
    _whitelist_media,
)
from app.media.service import delete_record
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.dependencies import ExistingShow
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.sources.service import get_or_create_custom_media_source
from app.users.dependencies import OptionalUser

channels_router = APIRouter(prefix="/channels", tags=["channels"])


# How many of a season's episodes are read at once on the filter page.
WHITELIST_EPISODE_PAGE = 100


# One row of a channel's show list: the title it is listed under and the website's
# non-canonical row standing for it, since a non-canonical row that mixes titles is a
# row under each of them.
ChannelShowRow = tuple[uuid.UUID, uuid.UUID]


# TODO: Validate
@channels_router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the `User`."""
    return service.create_channel(session, current_user, channel_in)


# TODO: Validate
@channels_router.get("")
def get_channels(
    session: SessionDep,
    current_user: OptionalUser,
    read_options: Annotated[ChannelReadOptions, Query()],
) -> ChannelsPublic:
    """Get `Channel`s."""
    return service.scoped_channel_list_output(session, current_user, read_options)


# TODO: Validate
@channels_router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by EditableChannel
def update_channel(
    session: SessionDep,
    channel: EditableChannel,
    channel_in: ChannelUpdate,
) -> Channel:
    """Update and return a `Channel` if it's editable by the `User`."""
    return channel_in.update(session, channel)


# TODO: Validate
@channels_router.delete("/{channel_id}")  # noqa: FAST003 - Used by EditableChannel
def delete_channel(session: SessionDep, channel: EditableChannel) -> Message:
    """Delete a `Channel` if it's editable by the `User`."""
    return delete_record(session, channel)


# TODO: Validate
@channels_router.get("/sort-options")
def get_sort_options() -> list[SortOptionOutput]:
    """Get a list of all possible sorting options."""
    return service.get_sort_options()


# TODO: Validate
@channels_router.post("/bulk-import-queue")
def bulk_import_queue_urls(
    session: SessionDep,
    current_user: CurrentUser,
    entries: dict[uuid.UUID, list[str]],
) -> Message:
    """Add URLs to multiple channels' import queues at once."""
    channels_by_id = {
        channel.id: channel
        for channel in session.exec(
            select(Channel)
            .where(col(Channel.id).in_(entries.keys()))
            .where(Channel.user_id == current_user.id),
        ).all()
    }
    total_urls = 0
    for channel_id, urls in entries.items():
        if channel := channels_by_id.get(channel_id):
            service.add_urls_to_channel_import_queue(
                session=session,
                urls=urls,
                channel=channel,
            )
            total_urls += len(urls)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel {channel_id} not found",
            )
    return Message(message=f"{total_urls} URLs added across {len(entries)} channels")


# TODO: Validate
@channels_router.get("/favorite-ids")
def get_favorite_channel_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited.

    Unreadable favorites are left in because this only drives the favorite toggle;
    the `favorites` scope of the list endpoint is what applies the read rules.
    """
    return list(
        session.exec(
            select(ChannelFavorite.channel_id).where(
                ChannelFavorite.user_id == current_user.id,
            ),
        ).all(),
    )


# TODO: Validate
@channels_router.post("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        session.add(ChannelFavorite(user_id=current_user.id, channel_id=channel.id))
        session.commit()
    return Message(message="Channel favorited successfully")


# TODO: Validate
@channels_router.patch("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def update_favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`.

    Favoriting the channel first if it isn't already, so personalizing it from the
    favorites view can never race against the favorite not yet existing.
    """
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        favorite = ChannelFavorite(user_id=current_user.id, channel_id=channel.id)
        session.add(favorite)
    favorite.name = favorite_in.name
    favorite.channel_number = favorite_in.channel_number
    session.commit()
    return Message(message="Favorite updated successfully")


# TODO: Validate
@channels_router.delete("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def unfavorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Remove a `Channel` from the `User`'s favorites."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Channel unfavorited successfully")


# TODO: Validate
@channels_router.get(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by ReadableChannel.
)
def get_channel_combined_channels(
    channel: ReadableChannel,
    session: SessionDep,
) -> list[CombinedChannelOutput]:
    """Return a `Channel`'s `CombinedChannel`s."""
    result: list[CombinedChannelOutput] = []
    for combined in channel.combined_channels:
        combined_channel = session.get(Channel, combined.combined_channel_id)
        result.append(
            CombinedChannelOutput(
                id=combined.combined_channel_id,
                name=combined_channel.name if combined_channel else None,
            ),
        )
    return result


# TODO: Validate
@channels_router.put(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by EditableChannel.
)
def update_channel_combined_channels(
    session: SessionDep,
    current_user: CurrentUser,
    channel: EditableChannel,
    combined_channels: list[CombinedChannelInput],
) -> Message:
    """Replace a `Channel`'s `CombinedChannel`s."""
    readable_ids = {
        readable.id
        for readable in readable_channels(
            session,
            current_user,
            [combined.id for combined in combined_channels],
        )
    }
    readable = [
        combined for combined in combined_channels if combined.id in readable_ids
    ]
    service.set_channel_combined_channels(session, channel, readable)
    return Message(message="Combined channels updated successfully")


# TODO: Validate
@channels_router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used by ReadableChannel.
def get_channel_episodes(
    channel: ReadableChannel,
    channel_options: Annotated[ChannelOptions, Query()],
    user: OptionalUser,
    session: SessionDep,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    output = ChannelEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
        channels={},
    )

    start = time.time()

    builder = EpisodeQueryBuilder(session, channel, channel_options, user)
    results = builder.get_episodes()
    output.has_more = builder.has_more

    unique_channel_ids = {
        channel_id for result in results for channel_id in result.channel_ids
    }
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = service.channel_output(channel_obj, user)

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
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        # The website is read off the row itself rather than off the id column on
        # the listing, which a title leaves empty. Only listings are ever here,
        # so the two say the same thing and only one of them says it in a type.
        if source.id not in output.sources:
            output.sources[source.id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

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
        output.sources[custom_source.id] = SourcePublic.model_validate(custom_source)
        output.plugins[custom_source.plugin_id] = PluginOutput.model_validate(
            custom_source.plugin,
        )

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/shows")  # noqa: FAST003
def get_channel_shows(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> ChannelShowsOutput:
    """Read all shows for a channel, including those from its child channels."""
    output = ChannelShowsOutput()

    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )
    channel_shows = session.exec(
        select(ChannelShow).where(col(ChannelShow.channel_id).in_(channel_ids)),
    ).all()
    # A `ChannelShow` is a title, so each one stands for every website's non-canonical
    # row of it.
    canonical_show_ids = {
        channel_show.canonical_show_id for channel_show in channel_shows
    }
    non_canonical_shows = service.shows_by_canonical_id(session, canonical_show_ids)

    # A title no website carries has only TMDB's own non-canonical row of it, and
    # leaving that out would leave the title out of the list it was added to, which is
    # the one place it would have shown that it is there at all.
    unwatchable = {
        canonical_show_id
        for canonical_show_id in canonical_show_ids
        if not non_canonical_shows[canonical_show_id]
    }
    non_canonical_shows.update(service.tmdb_shows_by_canonical_id(session, unwatchable))

    # A show can appear in several of the combined channels; deduplicate by the title it
    # is listed under and the non-canonical row it is. A show counts as a regular show
    # if any channel includes it normally, even when another channel only uses it for
    # filtering.
    regular_shows: dict[ChannelShowRow, ShowPublic] = {}
    filter_only_shows: dict[ChannelShowRow, ShowPublic] = {}
    # Regular shows kept per channel so they can be grouped by where they come from.
    shows_by_channel: dict[uuid.UUID, dict[ChannelShowRow, ShowPublic]] = {}
    channel_names: dict[uuid.UUID, str | None] = {}
    for channel_show in channel_shows:
        canonical_show_id = channel_show.canonical_show_id
        for show in non_canonical_shows[canonical_show_id]:
            source = show.source
            plugin = source.plugin

            # A non-canonical row is read as the title the channel holds rather than as
            # any other title it is of, since a listing that mixes titles is on a
            # channel under whichever of them was added. That is what gathers the
            # non-canonical rows of one title into the one row, and what the row's own
            # totals and missing fields are then filled in from.
            key = (canonical_show_id, show.id)
            update = {"canonical_show_id": canonical_show_id}

            if channel_show.is_blacklist_only:
                filter_only_shows.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
            else:
                regular_shows.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
                channel_group = shows_by_channel.setdefault(channel_show.channel_id, {})
                channel_group.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
                channel_names.setdefault(
                    channel_show.channel_id,
                    channel_show.channel.name,
                )

            # TMDB is not somewhere a title can be watched, so it is not one of the
            # sources the list is filtered by and its icon does not stand beside a title
            # as though it were. A title it is the only non-canonical row of is left
            # with no icon, which is what having nowhere to watch it looks like.
            if source.id not in output.sources and plugin.key != TMDB_PLUGIN_KEY:
                output.sources[source.id] = SourcePublic.model_validate(source)

    output.shows = list(regular_shows.values())
    output.filter_only_shows = [
        show for key, show in filter_only_shows.items() if key not in regular_shows
    ]

    # The channel the request was made on comes first; the rest follow by name.
    # TODO: Validate
    def group_sort_key(group_channel_id: uuid.UUID) -> tuple[bool, str]:
        is_not_primary = group_channel_id != channel.id
        return (is_not_primary, (channel_names.get(group_channel_id) or "").lower())

    output.groups = [
        ChannelShowGroup(
            channel_id=group_channel_id,
            channel_name=channel_names.get(group_channel_id),
            shows=sorted(
                shows_by_channel[group_channel_id].values(),
                key=lambda show: (show.name or "").lower(),
            ),
        )
        for group_channel_id in sorted(shows_by_channel, key=group_sort_key)
    ]

    # Every title the channel holds rather than every title its non-canonical rows are
    # of, since a non-canonical row that mixes titles is listed under whichever of them
    # the channel was told to hold.
    output.stats = _channel_show_stats(session, canonical_show_ids)
    output.canonical_sources = _canonical_sources(session, canonical_show_ids)
    output.canonical_shows = _canonical_shows(session, canonical_show_ids)

    return output


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    non_canonical_shows = service.shows_by_canonical_id(
        session,
        {channel_show.canonical_show_id for channel_show in channel.shows},
    )
    for channel_show in channel.shows:
        for show in non_canonical_shows[channel_show.canonical_show_id]:
            source = show.source
            if source.id not in sources:
                sources[source.id] = SourcePublic.model_validate(source)

    custom_source = get_or_create_custom_media_source(session)
    sources.setdefault(
        custom_source.id,
        SourcePublic.model_validate(custom_source),
    )

    return list(sources.values())


# FAST003 - Parameter is used by ReadableChannelCanonicalShow.
# TODO: Validate
@channels_router.get("/{channel_id}/whitelist/{canonical_show_id}")  # noqa: FAST003
def get_channel_whitelist(
    session: SessionDep,
    channel_show: ReadableChannelCanonicalShow,
) -> WhitelistShowOutput:
    """Read the sites and seasons of a title's filters in a channel.

    A filter is about the media rather than one website's non-canonical row of it, so
    every non-canonical row's seasons are listed, with the non-canonical rows of the
    same season collapsed into the one row the filter applies to. The episodes are read
    separately, a season at a time, since a title's whole catalogue is far more than the
    page opens on.
    """
    enabled_sources = {x.show_id for x in channel_show.source_filters}
    enabled_seasons = {x.season_id for x in channel_show.season_filters}

    shows = service.shows_for_channel_show(session, channel_show)
    tmdb_shows = service.tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    # The websites' rows carrying each season, so a row can name the sites it
    # came from.
    season_show_ids = _listed_season_show_ids(session, channel_show, shows, tmdb_shows)

    sources = [
        WhitelistSourceOutput(
            show_id=show.id,
            source_id=show.source.id,
            source_name=show.source.name,
            favicon_url=show.source.favicon_url,
            show=ShowPublic.model_validate(show),
            filtered=show.id in enabled_sources,
            is_tmdb=show.source.plugin.key == TMDB_PLUGIN_KEY,
        )
        for show in [*shows, *tmdb_shows]
    ]

    # The rows are the title's own seasons rather than the websites' non-canonical rows
    # of them: a filter names a season of the title, and the title holds seasons no
    # website carries - one TMDB has announced, one only another site fills - which are
    # still seasons for the user to see rather than rows to leave out for having nothing
    # under them yet.
    title_seasons = session.exec(
        select(Season).where(
            Season.show_id == channel_show.canonical_show_id,
            col(Season.deleted_at).is_(None),
        ),
    ).all()
    season_rows = _seasons_by_id(session, title_seasons, season_show_ids)

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
                    "show_ids": season_show_ids[season_id],
                },
            ),
        )

    for season in title_seasons:
        list_season(season.id)

    # A season the title has no row of is listed after the ones it does, in the
    # order the seasons themselves read in, so a page boundary and a listing
    # both fall the same way on every request.
    for season_id in sorted(
        season_show_ids,
        key=lambda key: _season_sort_key(season_rows[key]),
    ):
        list_season(season_id)

    return WhitelistShowOutput.model_validate(
        (shows or tmdb_shows)[0],
        update={
            "is_whitelist": channel_show.is_whitelist,
            "sources": sources,
            "seasons": seasons,
        },
    )


# FAST003 - Parameters are used by ReadableChannelCanonicalShow.
# TODO: Validate
@channels_router.get(
    "/{channel_id}/whitelist/{canonical_show_id}/seasons/{season_id}/episodes",  # noqa: FAST003
)
def get_channel_whitelist_episodes(
    session: SessionDep,
    channel_show: ReadableChannelCanonicalShow,
    season_id: uuid.UUID,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=WHITELIST_EPISODE_PAGE)] = (
        WHITELIST_EPISODE_PAGE
    ),
) -> WhitelistEpisodesOutput:
    """Read one page of a season's episodes, as the filter page expands it.

    A filter is about the media rather than one website's non-canonical row of it, so
    the non-canonical rows of an episode are collapsed into the one row the filter
    applies to, and each non-canonical row is carried alongside as a link of its own.
    """
    enabled_episodes = {x.canonical_episode_id for x in channel_show.episode_filters}
    episode_expiries = {
        episode_filter.canonical_episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    # An episode is listed once under every season row carrying it, since two seasons
    # sharing an episode each have it to filter on. Only the non-canonical rows of it
    # under the same row are folded together.
    rows = _season_episode_rows(session, channel_show, season_id)
    representatives: dict[uuid.UUID, _SeasonEpisodeRow] = {}
    for row in rows:
        representatives.setdefault(row.canonical_episode_id, row)

    # Ordered and paged as the stored rows, since reading one as the schema is
    # work per episode and only the page being served is ever read.
    canonical_orders = _canonical_orders(session, representatives)
    page_rows = sorted(
        representatives.values(),
        key=lambda row: _episode_sort_key(
            row,
            canonical_orders.get(row.canonical_episode_id),
        ),
    )[offset : offset + limit]

    # Only the page being served is asked after: the links a row carries and the
    # reading of it as the media are both work per episode, and a season of a
    # thousand is not a season anybody reads at once.
    page_canonical_ids = {row.canonical_episode_id for row in page_rows}
    link_rows = [row for row in rows if row.canonical_episode_id in page_canonical_ids]
    episodes = _episodes_by_id(session, [row.id for row in link_rows])

    episode_source_filters = _episode_source_filters(channel_show)
    episode_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for row in link_rows:
        if row.show_id not in episode_show_ids[row.canonical_episode_id]:
            episode_show_ids[row.canonical_episode_id].append(row.show_id)
        episode_source_filter = episode_source_filters.get(
            (row.canonical_episode_id, row.show_id),
        )
        episode_links[row.canonical_episode_id].append(
            WhitelistEpisodeLinkOutput.model_validate(
                episodes[row.id],
                update={
                    "show_id": row.show_id,
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
                "canonical_episode_id": row.canonical_episode_id,
                "filtered": row.canonical_episode_id in enabled_episodes,
                "expires_at": episode_expiries.get(row.canonical_episode_id),
                "show_ids": episode_show_ids[row.canonical_episode_id],
                "links": episode_links[row.canonical_episode_id],
            },
        )
        for row in page_rows
    ]

    serve_as_canonical_episodes(session, page)

    return WhitelistEpisodesOutput(episodes=page, total_count=len(representatives))


# FAST003 - Parameter is used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.get(
    "/{channel_id}/whitelist/{canonical_show_id}/filtered-episodes",  # noqa: FAST003
)
def get_channel_whitelist_filtered_episodes(
    session: SessionDep,
    channel_show: EditableChannelCanonicalShow,
) -> list[WhitelistEpisodeOutput]:
    """Read the episodes of a title that an entry names, whatever season they are in.

    The entries are what is being listed rather than the title's catalogue, so
    this stays small however many episodes the title has, which is what lets the
    blacklist be read without paging through everything it does not name.
    """
    enabled_episodes = {x.canonical_episode_id for x in channel_show.episode_filters}
    if not enabled_episodes:
        return []

    episode_expiries = {
        episode_filter.canonical_episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    media = _whitelist_media(session, channel_show)

    episodes: list[WhitelistEpisodeOutput] = []
    seen_episodes: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for season in [*media.site_seasons, *media.tmdb_seasons]:
        for episode in season.active_children:
            if episode.id not in media.listed_episode_ids:
                continue
            canonical_episode_id = canonical_id_of(episode)
            if canonical_episode_id not in enabled_episodes:
                continue
            episode_season_id = media.episode_seasons[episode.id]
            if (episode_season_id, canonical_episode_id) in seen_episodes:
                continue
            seen_episodes.add((episode_season_id, canonical_episode_id))
            episodes.append(
                WhitelistEpisodeOutput.model_validate(
                    episode,
                    update={
                        "season_id": episode_season_id,
                        "canonical_episode_id": canonical_episode_id,
                        "filtered": True,
                        "expires_at": episode_expiries.get(canonical_episode_id),
                        "show_ids": [],
                        "links": [],
                    },
                ),
            )

    canonical_orders = _canonical_orders(session, enabled_episodes)
    episodes.sort(
        key=lambda episode: _episode_sort_key(
            episode,
            canonical_orders.get(episode.canonical_episode_id),
        ),
    )
    episode_show_ids, episode_links = _episode_links_by_canonical_id(
        [*media.shows, *media.tmdb_shows],
        media.listed_episode_ids,
        _episode_source_filters(channel_show),
        enabled_episodes,
    )
    for episode_output in episodes:
        episode_output.show_ids = episode_show_ids[episode_output.canonical_episode_id]
        episode_output.links = episode_links[episode_output.canonical_episode_id]

    serve_as_canonical_episodes(session, episodes)
    return episodes


# FAST003 - Parameter is used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.patch("/{channel_id}/whitelist/{canonical_show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: EditableChannelCanonicalShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    service.update_whitelist(session, channel_show, whitelist_config)
    # Build the response before any cleanup so it stays valid even if the
    # channel-show is removed below.
    output = get_channel_whitelist(session, channel_show)
    # A filter-only show that no longer hides anything serves no purpose, so drop it
    # to keep the channel's show list clean.
    if (
        channel_show.is_blacklist_only
        and not channel_show.source_filters
        and not channel_show.season_filters
        and not channel_show.episode_filters
    ):
        session.delete(channel_show)
        session.commit()
    return output


# FAST003 - Parameter is used by EditableChannel.
# TODO: Validate
@channels_router.post("/{channel_id}/blacklist-episode")  # noqa: FAST003
def blacklist_channel_episode(
    session: SessionDep,
    channel: EditableChannel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`.

    When the show is not already on the channel a filter-only `ChannelShow` is
    created so the episode can be hidden without making the whole show a member of the
    channel. An optional `expires_at` makes the blacklist temporary.
    """
    # Show's primary key is (source_id, key), so look it up by its id column.
    show = session.exec(
        select(Show).where(Show.id == blacklist_in.show_id),
    ).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    service.blacklist_episode_on_channel(
        session=session,
        channel=channel,
        show=show,
        episode_id=blacklist_in.episode_id,
        expires_at=blacklist_in.expires_at,
    )
    return Message(message="Episode blacklisted successfully")


# FAST003 - Parameter is used by UserChannel.
# TODO: Validate
@channels_router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: EditableChannel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    exclude: set[str] = set()
    if "random_seed" not in channel_options.model_fields_set:
        exclude.add("random_seed")
    channel.default_order = channel_options.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
        exclude=exclude,
    )
    session.commit()
    session.refresh(channel)
    return channel


# FAST003 - Parameter is used by EditableChannel.
# TODO: Validate
@channels_router.patch("/{channel_id}/order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_order(
    session: SessionDep,
    channel: EditableChannel,
    order_input: ChannelOrderInput,
) -> Channel:
    """Set the custom episode order for a `Channel`."""
    service.set_channel_order(session, channel, order_input.episode_ids)
    session.refresh(channel)
    return channel


# FAST003 - Parameter is used by ExistingShow.
# TODO: Validate
@channels_router.get("/for-show/{show_id}")  # noqa: FAST003
def get_channels_for_show(
    session: SessionDep,
    current_user: CurrentUser,
    show: ExistingShow,
) -> list[ChannelShowMembership]:
    """List the `User`'s `Channel`s, saying which already hold a title."""
    return service.channels_with_show_membership(session, current_user, show)


# FAST003 - Parameters are used by EditableChannel and ExistingShow.
# TODO: Validate
@channels_router.post("/{channel_id}/add-show/{show_id}")  # noqa: FAST003
def add_channel_show(
    session: SessionDep,
    channel: EditableChannel,
    show: ExistingShow,
) -> Message:
    """Put a title, on every website it is on, onto a `Channel`."""
    service.add_show_to_channel(session, channel, show)
    return Message(message=f"{show.name} added to channel successfully")


# FAST003 - Parameters are used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.delete("/{channel_id}/remove-show/{canonical_show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: EditableChannelCanonicalShow,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    shows = service.shows_for_channel_show(session, channel_show)
    # The title's own name is what is left to say when no website's non-canonical row of
    # it carries one, which is the case for a title only TMDB has a record of.
    canonical_show = session.exec(
        select(Show).where(Show.id == channel_show.canonical_show_id),
    ).first()
    name = next(
        (show.name for show in shows if show.name),
        canonical_show.name if canonical_show else None,
    )
    session.delete(channel_show)
    session.commit()
    return Message(message=f"{name} removed from channel successfully")


# TODO: Validate
@channels_router.get(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by UserChannel
    response_model=list[ChannelQueueOutput],
)
def get_channel_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
    )

    channels = session.exec(statement).all()

    return list(channels)


# TODO: Validate
@channels_router.post(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by UserChannel
    response_model=list[ChannelQueueOutput],
)
def create_channel_queue_urls(
    session: SessionDep,
    channel: EditableChannel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    return service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )


# TODO: Validate
@channels_router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used by UserChannel.
def delete_channel_queue_url(
    session: SessionDep,
    channel: EditableChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    queue_entry = session.exec(
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        .where(ChannelQueue.id == url_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


# TODO: Validate
@channels_router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used by UserChannel.
def clear_channel_completed_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Clear a channel's import queue."""
    for queue_entry in channel.queue:
        if queue_entry.status == service.URLStatus.IMPORTED:
            session.delete(queue_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")


# TODO: Validate
@channels_router.get("/{channel_id}")  # noqa: FAST003 - Used by ReadableChannel
def get_channel(channel: ReadableChannel, user: OptionalUser) -> ChannelOutput:
    """Get a `Channel` if it's readable by the `User`."""
    return service.channel_output(channel, user)


router = APIRouter()


router.include_router(channels_router)
