# TODO: Validate
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlmodel import col, func, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels import service
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelShow,
    ReadableChannel,
    SafeReadableChannels,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
)
from app.channels.models import (
    Channel,
    ChannelEpisodeWhiteList,
    ChannelQueue,
    ChannelSeasonWhiteList,
)
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelInput,
    ChannelMediaFilter,
    ChannelNameItem,
    ChannelNamesOutput,
    ChannelOutput,
    ChannelShowsOutput,
    EpisodeWithExtrasOutput,
    MultipleChannelOutputs,
    MultipleChannelQueueOutputs,
    MultipleSortOptionOutputs,
    SortOptionOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
    WhitelistStatusOutput,
)
from app.constants import MAX_ENTRIES_PER_PAGE
from app.media.models import Episode, Plugin, Season, Show, Source
from app.media.schemas import (
    EpisodeOutput,
    PluginOutput,
    SeasonOutput,
    ShowOutput,
    SourceOutput,
)
from app.models import Message
from app.users.dependencies import OptionalUser

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/sort-options")
def get_sort_options() -> MultipleSortOptionOutputs:
    """Get a list of all possible sorting options."""
    # Random needs to be added by hand because it does not rely on a specific field.
    data: list[SortOptionOutput] = []

    # For simplicity all of the other possible values are dynamically generated from the
    # model fields.
    skip_fields = ("extra", "id", "description", "data_timestamp")
    for model in (Episode, Season, Show, Source, Plugin):
        for field in model.model_fields:
            if field.endswith(("key", "url", "_at", "_id")) or field in skip_fields:
                continue

            label = f"{model.__name__} - {field.replace('_', ' ').title()}"
            model_name = model.__name__.lower()
            data.append(
                SortOptionOutput(
                    label=label,
                    value=f"value.{model_name}.{field}",
                ),
            )

    # Manually created special cases that also have special cases when looking up the
    # data in the database.
    data.append(
        SortOptionOutput(
            label="Show - Remaining Duration",
            value="sum.show-episodes.duration",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Remaining Episodes",
            value="count.show-episodes.id",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Last Watched",
            value="max.show-episodes.last_watched",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Latest Episode Date",
            value="max.show-episodes.air_date",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Recently Aired (Last Month)",
            value="value.show.recently_aired_month",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Recently Aired (Last Week)",
            value="value.show.recently_aired_week",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Episode - Random",
            value="value.episode.random",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Random",
            value="max.show-episodes.random",
        ),
    )

    # Sort everything by the label
    data.sort(key=lambda x: x.label)

    return MultipleSortOptionOutputs(data=data, count=len(data))


@router.get("/")
def get_channels(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = MAX_ENTRIES_PER_PAGE,
) -> MultipleChannelOutputs:
    """Read all channels."""
    statement = select(Channel).order_by(Channel.name).offset(skip).limit(limit)
    count_statement = select(func.count()).select_from(Channel)

    if not current_user.is_superuser:
        count_statement = count_statement.where(Channel.user_id == current_user.id)
        statement = statement.where(Channel.user_id == current_user.id)

    count = session.exec(count_statement).one()
    channels = session.exec(statement).all()

    return MultipleChannelOutputs(data=channels, count=count)  # pyright: ignore[reportArgumentType] - Pydantic casting


@router.get("/names")
def get_channel_names(
    channels: SafeReadableChannels,
    channel_ids: Annotated[list[uuid.UUID], Query()],
) -> ChannelNamesOutput:
    """Get channel names by IDs.

    Returns a mapping of channel IDs to their names. Uses the same permission checks as
    other channel endpoints (public channels, owned channels, or superuser access).
    Returns "Unknown Channel" for channels not found or without permission.
    """
    accessible_channels = {str(channel.id): channel.name for channel in channels}

    data: list[ChannelNameItem] = []
    for channel_id in channel_ids:
        channel_id_str = str(channel_id)
        name = accessible_channels.get(channel_id_str, "Unknown Channel")
        data.append(ChannelNameItem(id=channel_id_str, name=name))

    return ChannelNamesOutput(data=data)


@router.get("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used in dependencies
def get_channel(channel: ReadableChannel) -> Channel:
    """Read a specific channel."""
    return channel


@router.post("/", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelInput,
) -> Channel:
    """Create a new channel."""
    return service.create_channel(session, current_user.id, channel_in)


@router.put("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used in dependencies
def update_channel(
    session: SessionDep,
    channel_in: ChannelInput,
    current_user: CurrentUser,
    channel: EditableChannel,
) -> Channel:
    """Update an existing channel."""
    return service.update_channel(session, current_user, channel_in, channel)


@router.delete("/{channel_id}")  # noqa: FAST003 - Used in dependencies
def delete_channel(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Delete a channel."""
    session.delete(channel)
    session.commit()
    return Message(message="Channel deleted successfully")


@router.post("/{channel_id}/import-queue")  # noqa: FAST003 - Used in dependencies
def add_urls_to_channel_import_queue(
    session: SessionDep,
    channel: EditableChannel,
    urls: list[str],
) -> MultipleChannelQueueOutputs:
    """Add URLs to a channel's import queue."""
    data = service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )
    return MultipleChannelQueueOutputs(data=data, count=len(data))  # pyright: ignore[reportArgumentType] - Pydantic casting


@router.get("/{channel_id}/import-queue")  # noqa: FAST003 - Used in dependencies
def get_channel_import_queue(
    session: SessionDep,
    channel: EditableChannel,
    skip: int = 0,
    limit: int = MAX_ENTRIES_PER_PAGE,
) -> MultipleChannelQueueOutputs:
    """Read the URLs in a channel's import queue."""
    count_statement = (
        select(func.count())
        .select_from(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        .offset(skip)
        .limit(limit)
    )

    statement = statement.order_by(col(ChannelQueue.created_at).desc())

    channels = session.exec(statement).all()

    return MultipleChannelQueueOutputs(
        data=channels,  # pyright: ignore[reportArgumentType] - Pydantic casting
        count=count,
    )


@router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used in dependencies
def delete_url_from_channel_import_queue(
    session: SessionDep,
    channel: EditableChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    for existing_entry in channel.queue:
        if existing_entry.id == url_id:
            url = existing_entry.url
            session.delete(existing_entry)
            session.commit()
            return Message(message=f"{url} removed from import queue successfully")

    raise HTTPException(status_code=404, detail="URL not found")


@router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used in dependencies
def clear_completed_channel_import_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Clear a channel's import queue."""
    for existing_entry in channel.queue:
        if existing_entry.status == service.URLStatus.IMPORTED:
            session.delete(existing_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")


@router.post("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003 - Used in dependencies
def set_channel_show_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: EditableChannelShow,
) -> WhitelistShowOutput:
    """Set the whitelist/blacklist for a show in a channel."""
    channel_show.white_list_mode = whitelist_config.whitelist_mode

    channel_show.season_white_list.clear()
    channel_show.episode_white_list.clear()
    # TODO: Is this still required?
    session.flush()

    channel_show.season_white_list.extend(
        [
            ChannelSeasonWhiteList(channel_show_id=channel_show.id, season_id=season.id)
            for season in whitelist_config.seasons
            if season.enabled
        ],
    )

    channel_show.episode_white_list.extend(
        [
            ChannelEpisodeWhiteList(
                channel_show_id=channel_show.id,
                episode_id=episode.id,
            )
            for season in whitelist_config.seasons
            for episode in season.episodes
            if episode.enabled
        ],
    )

    session.commit()

    return get_channel_show_whitelist(channel_show)


@router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003 - Used in dependencies
def get_channel_show_whitelist(
    channel_show: EditableChannelShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a show in a channel."""
    seasons: list[SeasonOutput] = []
    episodes: list[EpisodeOutput] = []

    for season in channel_show.show.seasons:
        seasons.append(SeasonOutput.model_validate(season))

        episodes.extend(
            EpisodeOutput.model_validate(episode) for episode in season.episodes
        )

    return WhitelistShowOutput.model_validate(
        channel_show.show,
        update={
            "whitelist_mode": channel_show.white_list_mode,
            "enabled_season_ids": [x.season_id for x in channel_show.season_white_list],
            "enabled_episode_ids": [
                x.episode_id for x in channel_show.episode_white_list
            ],
            "seasons": seasons,
            "episodes": episodes,
        },
    )


@router.post("/{channel_id}/swap-whitelist-status/{episode_id}")  # noqa: FAST003 - Used in dependencies
def swap_episode_whitelist_status(
    session: SessionDep,
    channel: EditableChannel,
    episode_id: uuid.UUID,
) -> WhitelistStatusOutput:
    """Toggle the whitelist status for an episode in a channel."""
    episode = session.exec(select(Episode).where(Episode.id == episode_id)).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # TODO: Benchmark this loop vs going to the database directly
    channel_show = None
    for channel_show_temp in channel.shows:
        if channel_show_temp.show_id == episode.season.show_id:
            channel_show = channel_show_temp
            break

    if not channel_show:
        raise HTTPException(status_code=404, detail="Show not found in channel")

    # TODO: Benchmark this loop vs going to the database directly
    for episode_whitelist in channel_show.episode_white_list:
        if episode_whitelist.episode_id == episode_id:
            session.delete(episode_whitelist)
            session.commit()
            return WhitelistStatusOutput(visible=(not channel_show.white_list_mode))

    new_whitelist = ChannelEpisodeWhiteList(
        channel_show_id=channel_show.id,
        episode_id=episode_id,
    )
    session.add(new_whitelist)
    session.commit()
    return WhitelistStatusOutput(visible=channel_show.white_list_mode)


@router.get("/{channel_id}/shows")  # noqa: FAST003 - Used in dependencies
def get_channel_shows(channel: ReadableChannel) -> ChannelShowsOutput:
    """Read all shows for a channel."""
    output = ChannelShowsOutput()

    for channel_show in channel.shows:
        show = channel_show.show
        source = show.source

        output.shows.append(ShowOutput.model_validate(show))

        if source.id not in output.sources:
            output.sources[source.id] = SourceOutput.model_validate(source)

    output.shows.sort(key=lambda s: s.name)

    return output


# TODO: Extensive benchmarking once sufficient data is gathered for testing.
@router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used in dependencies
def get_channel_episodes(
    channel: ReadableChannel,
    media_filter: Annotated[ChannelMediaFilter, Query()],
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

    builder = EpisodeQueryBuilder(session, channel, media_filter, user)
    episodes = builder.get_episodes()
    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    episode_channels = builder.get_episode_channels(episodes)
    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    watches = builder.get_episode_latest_watch_date(episodes)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    unique_channel_ids = set(episode_channels.values())
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = ChannelOutput.model_validate(channel_obj)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    for episode in episodes:
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        # Add last watched information and channel_id to the episodes after finding
        # the episodes because it is much faster for channels with tens of thousands
        # of episodes.
        if watches.get(episode.id):
            output.episodes.append(
                EpisodeWithExtrasOutput(
                    **episode.model_dump(),
                    watch_date=watches[episode.id].watch_date,
                    verified=watches[episode.id].verified,
                    episode_watch_id=watches[episode.id].id,
                    channel_id=episode_channels[episode.id],
                ),
            )
        else:
            output.episodes.append(
                EpisodeWithExtrasOutput(
                    **episode.model_dump(),
                    channel_id=episode_channels[episode.id],
                ),
            )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowOutput.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourceOutput.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    return output


# FAST003 - Used in dependencies
@router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def remove_channel_show(
    channel: ReadableChannel,
    session: SessionDep,
    show_id: str,
) -> Message:
    """Remove a show from a channel."""
    if not (show := session.exec(select(Show).where(Show.id == show_id)).first()):
        raise HTTPException(status_code=404, detail="Show not found")

    # TODO: Benchmark performance options.
    for channel_show in channel.shows:
        if channel_show.show == show:
            session.delete(channel_show)
            session.commit()
            return Message(message=f"{show.name} removed from channel successfully")

    raise HTTPException(status_code=404, detail="Show not found in channel")


@router.patch("/{channel_id}/default-order")  # noqa: FAST003 - Used in dependencies
def update_channel_default_order(
    session: SessionDep,
    channel: EditableChannel,
    media_filter: Annotated[ChannelMediaFilter, Query()],
) -> Message:
    """Update the default sort order for a channel."""
    channel.default_order = media_filter.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
    )
    session.commit()
    return Message(message="Default order updated successfully")
