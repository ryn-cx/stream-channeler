# TODO: Validate
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlmodel import col, func, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.channels import service
from app.channels.dependencies import (
    ExistingChannel,
    OwnedChannel,
    OwnedChannelReadableShow,
    ReadableChannel,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelAdminOutput,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelOptions,
    ChannelOutput,
    ChannelPublicListOutput,
    ChannelPublicOutput,
    ChannelQueueOutput,
    ChannelShowsOutput,
    ChannelUpdate,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEpisodeOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.media.service import delete_record
from app.models import Visibility
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.users.models import User

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOutput])
def get_channels(current_user: CurrentUser) -> list[Channel]:
    """List all `Channel`s owned by the current `User`."""
    return current_user.channels


@router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the current `User`."""
    channel = Channel.model_validate(channel_in, update={"user_id": current_user.id})
    session.add(channel)
    session.commit()
    return channel


@router.get("/sort-options")
def get_sort_options() -> list[SortOptionOutput]:
    """Get a list of all possible sorting options."""
    return service.get_sort_options()


@router.post("/bulk-import-queue")
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


@router.get("/public")
def get_public_channels(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> ChannelPublicListOutput:
    """List public `Channel`s with a positive admin score, highest score first.

    Channels with a `score` of `0` are hidden. Results are ordered by `score`
    descending, then by `id` ascending, and returned a page at a time.
    """
    public_and_scored = (
        Channel.visibility == Visibility.public,
        Channel.score >= 1,
    )
    count = session.exec(
        select(func.count()).select_from(Channel).where(*public_and_scored),
    ).one()
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(*public_and_scored)
        .order_by(col(Channel.score).desc(), col(Channel.id))
        .offset(offset)
        .limit(limit),
    ).all()
    data = [
        ChannelPublicOutput(
            id=channel.id,
            name=channel.name,
            channel_number=channel.channel_number,
            visibility=channel.visibility,
            default_order=channel.default_order,
            description=channel.description,
            anonymous=channel.anonymous,
            username=None if channel.anonymous else username,
        )
        for channel, username in rows
    ]
    return ChannelPublicListOutput(data=data, count=count)


@router.get("/all", dependencies=[Depends(get_current_active_superuser)])
def admin_list_channels(session: SessionDep) -> list[ChannelAdminOutput]:
    """List every `Channel` on the site along with its owner's username."""
    rows = session.exec(
        select(Channel, User.username).join(User, col(User.id) == Channel.user_id),
    ).all()
    return [
        ChannelAdminOutput.model_validate(channel, update={"username": username})
        for channel, username in rows
    ]


@router.get("/by-user/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def admin_list_user_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> list[ChannelAdminOutput]:
    """List every `Channel` owned by a single `User`."""
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(Channel.user_id == user_id),
    ).all()
    return [
        ChannelAdminOutput.model_validate(channel, update={"username": username})
        for channel, username in rows
    ]


@router.patch(
    "/admin/{channel_id}",  # noqa: FAST003 - Used by ExistingChannel.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_update_channel(
    session: SessionDep,
    channel: ExistingChannel,
    channel_in: ChannelAdminUpdate,
) -> ChannelAdminOutput:
    """Update any field on any `Channel` as an admin, including `score`."""
    channel.sqlmodel_update(channel_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(channel)
    username = session.get_one(User, channel.user_id).username
    return ChannelAdminOutput.model_validate(channel, update={"username": username})


@router.get("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by ReadableChannel
def get_channel(channel: ReadableChannel) -> Channel:
    """Get a `Channel` if it's readable by the current `User`."""
    return channel


@router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by OwnedChannel.
def update_channel(
    session: SessionDep,
    channel: OwnedChannel,
    channel_in: ChannelUpdate,
) -> Channel:
    """Update a `Channel` if it's owned by the current `User`."""
    return channel_in.update(session, channel)


@router.delete("/{channel_id}")  # noqa: FAST003 - Used by OwnedChannel.
def delete_channel(session: SessionDep, channel: OwnedChannel) -> Message:
    """Delete a `Channel` if it's owned by the current `User`."""
    return delete_record(session, channel)


@router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used by ReadableChannel.
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
        output.channels[channel_obj.id] = ChannelOutput.model_validate(channel_obj)

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

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/shows")  # noqa: FAST003
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

    # A show can appear in several of the combined channels; deduplicate by show id.
    # A show counts as a regular show if any channel includes it normally, even when
    # another channel only uses it for filtering.
    regular_shows: dict[uuid.UUID, ShowPublic] = {}
    filter_only_shows: dict[uuid.UUID, ShowPublic] = {}
    for channel_show in channel_shows:
        show = channel_show.show
        source = show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        if channel_show.is_blacklist_only:
            filter_only_shows.setdefault(show.id, ShowPublic.model_validate(show))
        else:
            regular_shows.setdefault(show.id, ShowPublic.model_validate(show))

        if source.id not in output.sources:
            output.sources[source.id] = SourcePublic.model_validate(source)

    output.shows = list(regular_shows.values())
    output.filter_only_shows = [
        show
        for show_id, show in filter_only_shows.items()
        if show_id not in regular_shows
    ]

    return output


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    for channel_show in channel.shows:
        source = channel_show.show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        if source.id not in sources:
            sources[source.id] = SourcePublic.model_validate(source)

    return list(sources.values())


# FAST003 - Parameter is used by UserChannelShow.
@router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def get_channel_whitelist(
    channel_show: OwnedChannelReadableShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a show in a channel."""
    enabled_season_ids = {x.season_id for x in channel_show.season_filters}
    enabled_episode_ids = {x.episode_id for x in channel_show.episode_filters}
    episode_expiries = {
        episode_filter.episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    seasons: list[WhitelistSeasonOutput] = []
    episodes: list[WhitelistEpisodeOutput] = []

    for season in channel_show.show.seasons:
        seasons.append(
            WhitelistSeasonOutput.model_validate(
                season,
                update={"filtered": season.id in enabled_season_ids},
            ),
        )
        episodes.extend(
            WhitelistEpisodeOutput.model_validate(
                episode,
                update={
                    "filtered": episode.id in enabled_episode_ids,
                    "expires_at": episode_expiries.get(episode.id),
                },
            )
            for episode in season.episodes
        )

    return WhitelistShowOutput.model_validate(
        channel_show.show,
        update={
            "is_whitelist": channel_show.is_whitelist,
            "seasons": seasons,
            "episodes": episodes,
        },
    )


# FAST003 - Parameter is used by UserChannelShow.
@router.patch("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: OwnedChannelReadableShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    service.update_whitelist(session, channel_show, whitelist_config)
    # Build the response before any cleanup so it stays valid even if the
    # channel-show is removed below.
    output = get_channel_whitelist(channel_show)
    # A filter-only show that no longer hides anything serves no purpose, so drop it
    # to keep the channel's show list clean.
    if (
        channel_show.is_blacklist_only
        and not channel_show.season_filters
        and not channel_show.episode_filters
    ):
        session.delete(channel_show)
        session.commit()
    return output


# FAST003 - Parameter is used by OwnedChannel.
@router.post("/{channel_id}/blacklist-episode")  # noqa: FAST003
def blacklist_channel_episode(
    session: SessionDep,
    channel: OwnedChannel,
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
@router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: OwnedChannel,
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


# FAST003 - Parameters are used by OwnedChannelReadableShow.
@router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: OwnedChannelReadableShow,
) -> Message:
    """Remove a `Show` from a `Channel`."""
    session.delete(channel_show)
    session.commit()
    return Message(
        message=f"{channel_show.show.name} removed from channel successfully",
    )


# FAST003 - Parameter is used by UserChannel.
@router.get("/{channel_id}/import-queue", response_model=list[ChannelQueueOutput])  # noqa: FAST003
def get_channel_queue(
    session: SessionDep,
    channel: OwnedChannel,
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


# FAST003 - Parameter is used by UserChannel.
@router.post("/{channel_id}/import-queue", response_model=list[ChannelQueueOutput])  # noqa: FAST003
def create_channel_queue_urls(
    session: SessionDep,
    channel: OwnedChannel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    data = service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )
    return data  # noqa: RET504 - TODO: Remove unnecessary assignment before return


@router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used by UserChannel.
def delete_channel_queue_url(
    session: SessionDep,
    channel: OwnedChannel,
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


@router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used by UserChannel.
def clear_channel_completed_queue(
    session: SessionDep,
    channel: OwnedChannel,
) -> Message:
    """Clear a channel's import queue."""
    for existing_record in channel.queue:
        if existing_record.status == service.URLStatus.IMPORTED:
            session.delete(existing_record)

    session.commit()
    return Message(message="Import queue cleared successfully")
