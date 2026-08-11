# TODO: Validate
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import case, distinct, func
from sqlmodel import Session, col, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.canonical_shows.models import CanonicalShow
from app.channels import service
from app.channels.channel_scope import (
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelReadableShow,
    ExistingChannel,
    ReadableChannel,
)
from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel, ChannelFavorite, ChannelQueue, ChannelShow
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelFavoriteUpdate,
    ChannelListOutput,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelQueueAdminOutput,
    ChannelQueueAdminUpdate,
    ChannelQueueOutput,
    ChannelReadOptions,
    ChannelShowGroup,
    ChannelShowsOutput,
    ChannelShowStats,
    ChannelsPublic,
    ChannelUpdate,
    CombinedChannelInput,
    CombinedChannelOutput,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEpisodeOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
    WhitelistSourceOutput,
)
from app.episodes.models import Episode
from app.media.canonical_metadata import (
    fill_episodes,
    fill_seasons,
    fill_shows,
    fill_tmdb_urls,
    prefer_canonical_episodes,
    prefer_canonical_seasons,
    prefer_seasons,
    prefer_shows,
)
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.media.schemas import MediaOwner
from app.media.service import delete_record
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.users.service import get_or_create_plugin_user

# Some websites report an episode with no release date as the epoch, which would
# otherwise read as the title's own release.
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

channels_router = APIRouter(prefix="/channels", tags=["channels"])
admin_router = APIRouter(
    prefix="/admin/channels",
    tags=["channels"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@channels_router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the `User`."""
    channel = Channel.model_validate(channel_in, update={"user_id": current_user.id})
    session.add(channel)
    session.commit()
    return channel


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
@admin_router.patch(
    "/{channel_id}",  # noqa: FAST003 - Used by ExistingChannel.
)
def admin_update_channel(
    session: SessionDep,
    channel: ExistingChannel,
    channel_in: ChannelAdminUpdate,
) -> ChannelListOutput:
    """Update any field on any `Channel` as an admin, including `score`."""
    channel.sqlmodel_update(channel_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(channel)
    username = session.get_one(User, channel.user_id).username
    return ChannelListOutput.model_validate(channel, update={"username": username})


# TODO: Validate
def _channel_queue_admin_output(
    channel: Channel,
    username: str | None,
    queue_entry: ChannelQueue,
) -> ChannelQueueAdminOutput:
    return ChannelQueueAdminOutput.model_validate(
        queue_entry,
        update={
            "channel_name": channel.name,
            "channel_number": channel.channel_number,
            "user_id": channel.user_id,
            "username": username,
        },
    )


# TODO: Validate
@admin_router.get("/queue")
def get_all_channel_queues(
    session: SessionDep,
    current_user: SuperUser,
    owner: MediaOwner | None = None,
) -> list[ChannelQueueAdminOutput]:
    """List every `Channel`'s import queue entries, scoped by owner."""
    selector = (
        select(ChannelQueue, Channel, User.username)
        .join(Channel, col(Channel.id) == ChannelQueue.channel_id)
        .join(User, col(User.id) == Channel.user_id)
        .order_by(col(ChannelQueue.created_at).desc())
    )
    if not owner:
        selector = selector.where(Channel.user_id == current_user.id)
    else:
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            selector = selector.where(Channel.user_id == plugin_user.id)
        else:
            selector = selector.where(
                col(Channel.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows = session.exec(selector).all()
    return [
        _channel_queue_admin_output(channel, username, queue_entry)
        for queue_entry, channel, username in rows
    ]


# TODO: Validate
@admin_router.patch("/queue/{queue_id}")
def admin_update_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    queue_entry.sqlmodel_update(queue_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(queue_entry)
    channel = session.get_one(Channel, queue_entry.channel_id)
    username = session.get_one(User, channel.user_id).username
    return _channel_queue_admin_output(channel, username, queue_entry)


# TODO: Validate
@admin_router.delete("/queue/{queue_id}")
def admin_delete_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


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

    unique_channel_ids = {
        channel_id for result in results for channel_id in result.channel_ids
    }
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = service.channel_output(channel_obj, user)

    for result in results:
        episode = result.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        extras: dict[str, Any] = {
            "channel_id": result.channel_id,
            "channel_ids": result.channel_ids,
        }
        if result.latest_watch:
            extras["watch_date"] = result.latest_watch.watch_date
            extras["verified"] = result.latest_watch.verified
            extras["episode_watch_id"] = result.latest_watch.id

        output.episodes.append(
            EpisodeWithDetails(**episode.model_dump(), **extras),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    # A card is about the media rather than one website's copy of it, so every row
    # reads as TMDB has it, with the website standing in only where TMDB has
    # nothing of its own to say.
    fill_episodes(session, output.episodes)
    fill_tmdb_urls(session, output.episodes)
    prefer_canonical_episodes(session, output.episodes)
    prefer_seasons(session, list(output.seasons.values()))
    prefer_shows(session, list(output.shows.values()))

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
    # A `ChannelShow` is a title, so each one stands for every website's copy of it.
    canonical_show_ids = {
        channel_show.canonical_show_id for channel_show in channel_shows
    }
    copies = service.shows_by_canonical_id(session, canonical_show_ids)

    # A title no website carries has only TMDB's own copy of it, and leaving that
    # out would leave the title out of the list it was added to, which is the one
    # place it would have shown that it is there at all.
    unwatchable = {
        canonical_show_id
        for canonical_show_id in canonical_show_ids
        if not copies[canonical_show_id]
    }
    copies.update(service.tmdb_shows_by_canonical_id(session, unwatchable))

    # A show can appear in several of the combined channels; deduplicate by show id.
    # A show counts as a regular show if any channel includes it normally, even when
    # another channel only uses it for filtering.
    regular_shows: dict[uuid.UUID, ShowPublic] = {}
    filter_only_shows: dict[uuid.UUID, ShowPublic] = {}
    # Regular shows kept per channel so they can be grouped by where they come from.
    shows_by_channel: dict[uuid.UUID, dict[uuid.UUID, ShowPublic]] = {}
    channel_names: dict[uuid.UUID, str | None] = {}
    for channel_show in channel_shows:
        for show in copies[channel_show.canonical_show_id]:
            source = show.source
            plugin = source.plugin

            # TMDB's plugin is private because its media is never browsed on its
            # own, but a title it is the only copy of is one the viewer put on
            # the channel themselves, so it is theirs to see here.
            if plugin.key != TMDB_PLUGIN_KEY and not plugin.is_readable(
                session,
                user,
            ):
                continue

            if channel_show.is_blacklist_only:
                filter_only_shows.setdefault(show.id, ShowPublic.model_validate(show))
            else:
                regular_shows.setdefault(show.id, ShowPublic.model_validate(show))
                channel_group = shows_by_channel.setdefault(channel_show.channel_id, {})
                channel_group.setdefault(show.id, ShowPublic.model_validate(show))
                channel_names.setdefault(
                    channel_show.channel_id,
                    channel_show.channel.name,
                )

            # TMDB is not somewhere a title can be watched, so it is not one of
            # the sources the list is filtered by and its icon does not stand
            # beside a title as though it were. A title it is the only copy of
            # is left with no icon, which is what having nowhere to watch it
            # looks like.
            if source.id not in output.sources and plugin.key != TMDB_PLUGIN_KEY:
                output.sources[source.id] = SourcePublic.model_validate(source)

    output.shows = list(regular_shows.values())
    output.filter_only_shows = [
        show
        for show_id, show in filter_only_shows.items()
        if show_id not in regular_shows
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

    # A grouped show is its own row, so the groups are filled alongside the lists.
    fill_shows(
        session,
        [
            *output.shows,
            *output.filter_only_shows,
            *(show for group in output.groups for show in group.shows),
        ],
    )

    output.stats = _channel_show_stats(
        session,
        {
            show.canonical_show_id
            for show in [*output.shows, *output.filter_only_shows]
            if show.canonical_show_id
        },
    )

    return output


# TODO: Validate
def _channel_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ChannelShowStats]:
    """Return what each title's seasons and episodes add up to.

    The same season and episode are carried by every website holding the title,
    so they are counted as the seasons and episodes they are rather than as the
    records holding them.
    """
    if not canonical_show_ids:
        return {}

    rows = session.exec(
        select(
            Show.canonical_show_id,
            func.count(distinct(col(Season.canonical_season_id))),
            func.count(distinct(col(Episode.canonical_episode_id))),
            func.min(
                case(
                    (col(Episode.release_date) > EPOCH, col(Episode.release_date)),
                ),
            ),
        )
        .join(Season, col(Season.show_id) == col(Show.id))
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            col(Show.canonical_show_id).in_(canonical_show_ids),
            col(Show.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Show.canonical_show_id)),
    ).all()

    return {
        canonical_show_id: ChannelShowStats(
            season_count=season_count,
            episode_count=episode_count,
            first_release_date=first_release_date,
        )
        for canonical_show_id, season_count, episode_count, first_release_date in rows
    }


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    copies = service.shows_by_canonical_id(
        session,
        {channel_show.canonical_show_id for channel_show in channel.shows},
    )
    for channel_show in channel.shows:
        for show in copies[channel_show.canonical_show_id]:
            source = show.source
            plugin = source.plugin

            if not plugin.is_readable(session, user):
                continue

            if source.id not in sources:
                sources[source.id] = SourcePublic.model_validate(source)

    return list(sources.values())


# TODO: Validate
def _copies_by_canonical_id(
    shows: Sequence[Show],
) -> tuple[dict[uuid.UUID, list[uuid.UUID]], dict[uuid.UUID, list[uuid.UUID]]]:
    """Map each canonical season and episode to the copies carrying it."""
    season_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for show in shows:
        for season in show.active_children:
            if show.id not in season_show_ids[season.canonical_season_id]:
                season_show_ids[season.canonical_season_id].append(show.id)
            for episode in season.active_children:
                if show.id not in episode_show_ids[episode.canonical_episode_id]:
                    episode_show_ids[episode.canonical_episode_id].append(show.id)
    return season_show_ids, episode_show_ids


# FAST003 - Parameter is used by UserChannelShow.
# TODO: Validate
@channels_router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def get_channel_whitelist(
    session: SessionDep,
    channel_show: EditableChannelReadableShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a title in a channel.

    A filter is about the media rather than one website's copy of it, so every
    copy's seasons and episodes are listed, with the copies of the same season or
    episode collapsed into the one row the filter applies to.
    """
    enabled_sources = {x.show_id for x in channel_show.source_filters}
    enabled_seasons = {x.canonical_season_id for x in channel_show.season_filters}
    enabled_episodes = {x.canonical_episode_id for x in channel_show.episode_filters}
    episode_expiries = {
        episode_filter.canonical_episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    seasons: list[WhitelistSeasonOutput] = []
    episodes: list[WhitelistEpisodeOutput] = []
    # The row each season and episode was listed under, so a later website's copy of
    # one is folded into the row already standing for it rather than listed again.
    season_rows: dict[uuid.UUID, uuid.UUID] = {}
    # An episode is listed once under every season row carrying it, since two
    # seasons sharing an episode each have it to filter on. Only the copies of it
    # under the same row are folded together.
    seen_episodes: set[tuple[uuid.UUID, uuid.UUID]] = set()

    shows = service.shows_for_channel_show(session, channel_show)
    # TMDB is not a website the title can be watched on, so it is not one of the
    # copies rows are built from and only stands for the seasons it has a record
    # of, which is all an announced season no site has filled yet can be named by.
    # A title no website carries at all has nothing else to be listed from, so
    # there its record is the whole of what there is rather than the remainder.
    tmdb_shows = service.tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    # The websites' copies carrying each season and episode, so a row can name the
    # sites it came from.
    season_show_ids, episode_show_ids = _copies_by_canonical_id(
        [*shows, *tmdb_shows],
    )

    sources = [
        WhitelistSourceOutput(
            show_id=show.id,
            source_id=show.source.id,
            source_name=show.source.name,
            favicon_url=show.source.favicon_url,
            filtered=show.id in enabled_sources,
            is_tmdb=show.source.plugin.key == TMDB_PLUGIN_KEY,
        )
        for show in [*shows, *tmdb_shows]
    ]

    # A season TMDB has a record of that no website carries is still a season of
    # the title, so it is listed for the user to know it is there rather than left
    # out for having nothing to watch under it. TMDB catalogues its episodes rather
    # than carrying them, so they name no site of their own.
    site_seasons = [season for show in shows for season in show.active_children]
    site_canonical_seasons = {season.canonical_season_id for season in site_seasons}
    tmdb_only_seasons = [
        season
        for tmdb_show in tmdb_shows
        for season in tmdb_show.active_children
        if season.canonical_season_id not in site_canonical_seasons
    ]

    for season in [*site_seasons, *tmdb_only_seasons]:
        if season.canonical_season_id not in season_rows:
            season_rows[season.canonical_season_id] = season.id
            seasons.append(
                WhitelistSeasonOutput.model_validate(
                    season,
                    update={
                        "filtered": season.canonical_season_id in enabled_seasons,
                        "show_ids": season_show_ids[season.canonical_season_id],
                    },
                ),
            )
        season_row_id = season_rows[season.canonical_season_id]
        for episode in season.active_children:
            if (season_row_id, episode.canonical_episode_id) in seen_episodes:
                continue
            seen_episodes.add((season_row_id, episode.canonical_episode_id))
            episodes.append(
                WhitelistEpisodeOutput.model_validate(
                    episode,
                    update={
                        "season_id": season_row_id,
                        "filtered": episode.canonical_episode_id in enabled_episodes,
                        "expires_at": episode_expiries.get(
                            episode.canonical_episode_id,
                        ),
                        "show_ids": episode_show_ids[episode.canonical_episode_id],
                    },
                ),
            )

    fill_seasons(session, seasons)
    fill_episodes(session, episodes)
    # A filter is about the media rather than one website's copy of it, so the
    # rows read as TMDB has the media, with the website only standing in for what
    # TMDB has no record of.
    prefer_canonical_seasons(session, seasons)
    prefer_canonical_episodes(session, episodes)

    return fill_shows(
        session,
        [
            WhitelistShowOutput.model_validate(
                (shows or tmdb_shows)[0],
                update={
                    "is_whitelist": channel_show.is_whitelist,
                    "sources": sources,
                    "seasons": seasons,
                    "episodes": episodes,
                },
            ),
        ],
    )[0]


# FAST003 - Parameter is used by UserChannelShow.
# TODO: Validate
@channels_router.patch("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: EditableChannelReadableShow,
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


# FAST003 - Parameters are used by EditableChannelReadableShow.
# TODO: Validate
@channels_router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: EditableChannelReadableShow,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    shows = service.shows_for_channel_show(session, channel_show)
    # The title's own name is what is left to say when no website's copy of it
    # carries one, which is the case for a title only TMDB has a record of.
    canonical_show = session.get(CanonicalShow, channel_show.canonical_show_id)
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
router.include_router(admin_router)
