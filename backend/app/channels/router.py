# TODO: Validate
import time
import uuid
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from typing import Annotated, Any, NamedTuple

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import and_, distinct, exists, func, or_
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    canonical_id_of,
    links_of,
    links_to,
)
from app.canonical_media.filters import is_canonical, is_non_canonical
from app.canonical_media.keys import same_issuer_clause, tmdb_key_clause
from app.canonical_media.metadata import (
    fill_episodes,
    fill_tmdb_urls,
    prefer_canonical_episodes,
)
from app.canonical_media.seasons import season_ids_by_episode
from app.channels import service
from app.channels.channel_scope import (
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelCanonicalShow,
    ExistingChannel,
    ReadableChannel,
    ReadableChannelCanonicalShow,
)
from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import (
    Channel,
    ChannelEpisodeSourceFilter,
    ChannelFavorite,
    ChannelQueue,
    ChannelShow,
)
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelAdminCreate,
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
    ChannelShowMembership,
    ChannelShowsOutput,
    ChannelShowStats,
    ChannelsPublic,
    ChannelUpdate,
    CombinedChannelInput,
    CombinedChannelOutput,
    EpisodeWithDetails,
    MediaOwner,
    SortOptionOutput,
    WhitelistEpisodeLinkOutput,
    WhitelistEpisodeOutput,
    WhitelistEpisodesOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
    WhitelistSourceOutput,
)
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.media.service import delete_record
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.dependencies import ReadableShow
from app.shows.models import Show, ShowCanonicalShow
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.users.service import get_or_create_plugin_user

# How many of a season's episodes are read at once on the filter page.
WHITELIST_EPISODE_PAGE = 100

# An episode the website never ordered sits after every episode it did.
_UNORDERED = float("inf")

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
    return service.create_channel(session, current_user, channel_in)


# TODO: Validate
@admin_router.post("", response_model=ChannelOutput)
def admin_create_channel(
    session: SessionDep,
    channel_in: ChannelAdminCreate,
) -> Channel:
    """Create a `Channel` owned by any `User`, with its `score`, as an admin."""
    return service.admin_create_channel(session, channel_in)


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
    channel = service.admin_update_channel(session, channel, channel_in)
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

    # An episode is the media rather than one website's non-canonical row of it, so
    # every row reads as TMDB has it, with the website standing in only where TMDB has
    # nothing of its own to say. A listing is linked to however many titles a website
    # mixed into it and has no one title to read as, so it is served as the website
    # stored it.
    fill_episodes(session, output.episodes)
    fill_tmdb_urls(session, output.episodes)
    prefer_canonical_episodes(session, output.episodes)

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# One row of a channel's show list: the title it is listed under and the website's
# non-canonical row standing for it, since a non-canonical row that mixes titles is a
# row under each of them.
ChannelShowRow = tuple[uuid.UUID, uuid.UUID]


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

            # TMDB's plugin is private because its media is never browsed on its own,
            # but a title it is the only non-canonical row of is one the viewer put on
            # the channel themselves, so it is theirs to see here.
            if plugin.key != TMDB_PLUGIN_KEY and not plugin.is_readable(
                session,
                user,
            ):
                continue

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


# TODO: Validate
def _canonical_shows(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ShowPublic]:
    """Return the title itself for each title the channel holds, keyed by it.

    A title is named by whoever catalogued it, which is TMDB wherever TMDB has a
    record of it, and that is the name it is read under rather than whatever any
    one website called its own row for it.
    """
    if not canonical_show_ids:
        return {}

    canonical_shows = session.exec(
        select(Show).where(col(Show.id).in_(canonical_show_ids)),
    ).all()
    return {
        canonical_show.id: ShowPublic.model_validate(canonical_show)
        for canonical_show in canonical_shows
    }


# TODO: Validate
def _canonical_sources(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, SourcePublic]:
    """Return the source each title itself was written by, keyed by the title.

    Which is TMDB wherever TMDB has a record of the title, and nothing where a
    website's listing is linked to a row minted for it to point at rather than of
    a title anything catalogued. Every row has a source now, including the minted
    ones, so what tells the two apart is who issued the key.
    """
    if not canonical_show_ids:
        return {}

    canonical_shows = session.exec(
        select(Show).where(
            col(Show.id).in_(canonical_show_ids),
            tmdb_key_clause(col(Show.key)),
        ),
    ).all()
    return {
        canonical_show.id: SourcePublic.model_validate(canonical_show.source)
        for canonical_show in canonical_shows
    }


# TODO: Validate
def _channel_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ChannelShowStats]:
    """Return what each title's seasons and episodes add up to.

    The same season and episode are carried by every website holding the title,
    so they are counted as the seasons and episodes they are rather than as the
    records holding them. Which title an episode counts towards is the episode's
    own answer, so a listing that mixes titles counts each of its episodes only
    towards the title that episode belongs to. An episode nothing was minted for
    it to be linked to has no such answer and counts towards the title its
    website's listing is linked to, under that website's own season.
    """
    if not canonical_show_ids:
        return {}

    canonical_episode = aliased(Episode)
    canonical_link = canonical_episode_link()
    rows = session.exec(
        select(
            Season.show_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(canonical_episode.id))),
        )
        .select_from(Season)
        .join(
            canonical_episode,
            col(canonical_episode.season_id) == col(Season.id),
        )
        .join(canonical_link, links_to(canonical_episode, canonical_link))
        .join(Episode, col(Episode.id) == col(canonical_link.episode_id))
        .where(
            is_canonical(canonical_episode),
            col(Season.show_id).in_(canonical_show_ids),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.show_id)),
    ).all()

    counts = {
        canonical_show_id: [season_count, episode_count]
        for canonical_show_id, season_count, episode_count in rows
    }
    for canonical_show_id, season_count, episode_count in _linked_show_stats(
        session,
        canonical_show_ids,
    ):
        totals = counts.setdefault(canonical_show_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    for canonical_show_id, season_count, episode_count in _standalone_show_stats(
        session,
        canonical_show_ids,
    ):
        totals = counts.setdefault(canonical_show_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    return {
        canonical_show_id: ChannelShowStats(
            season_count=season_count,
            episode_count=episode_count,
        )
        for canonical_show_id, (season_count, episode_count) in counts.items()
    }


# TODO: Validate
def _standalone_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what a title that is its own listing holds.

    A title nothing else has a record of is the row that is the record, and that row is
    where it is watched, so its seasons and episodes are its own rather than
    non-canonical rows of anything and no link reaches them. TMDB's rows are left out: a
    title TMDB wrote is counted by what the websites carrying it hold.
    """
    return session.exec(
        select(
            Season.show_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Season)
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            col(Season.show_id).in_(canonical_show_ids),
            is_canonical(Show),
            Plugin.key != TMDB_PLUGIN_KEY,
            col(Show.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.show_id)),
    ).all()


# TODO: Validate
def _linked_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what the episodes no title has a record of add up to.

    Counted apart from the title's own seasons and episodes because there is
    nothing shared for them to be counted as: a website's record of one of these
    is the only record of it, so two websites carrying the same unmatched episode
    count as two.
    """
    linked_season = aliased(Season)
    linked_show = aliased(Show)
    return session.exec(
        select(
            ShowCanonicalShow.canonical_show_id,
            func.count(distinct(col(linked_season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Episode)
        .join(linked_season, col(linked_season.id) == col(Episode.season_id))
        .join(linked_show, col(linked_show.id) == col(linked_season.show_id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(linked_show.id))
        .where(
            col(ShowCanonicalShow.canonical_show_id).in_(canonical_show_ids),
            is_canonical(Episode),
            is_non_canonical(linked_show),
            col(Episode.deleted_at).is_(None),
            col(linked_season.deleted_at).is_(None),
            col(linked_show.deleted_at).is_(None),
        )
        .group_by(col(ShowCanonicalShow.canonical_show_id)),
    ).all()


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
    non_canonical_shows = service.shows_by_canonical_id(
        session,
        {channel_show.canonical_show_id for channel_show in channel.shows},
    )
    for channel_show in channel.shows:
        for show in non_canonical_shows[channel_show.canonical_show_id]:
            source = show.source
            plugin = source.plugin

            if not plugin.is_readable(session, user):
                continue

            if source.id not in sources:
                sources[source.id] = SourcePublic.model_validate(source)

    return list(sources.values())


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
class _WhitelistMedia(NamedTuple):
    """The rows a title's filters are read against, gathered once per request."""

    shows: list[Show]
    tmdb_shows: list[Show]
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
    channel_show: ChannelShow,
) -> _WhitelistMedia:
    """Gather the websites' rows for the title `channel_show` is about."""
    shows = service.shows_for_channel_show(session, channel_show)
    # TMDB is not a website the title can be watched on, so it is not one of the
    # non-canonical rows the rows are built from, and only stands for the seasons it has
    # a record of, which is all an announced season no site has filled yet can be named
    # by. A title no website carries at all has nothing else to be listed from, so there
    # its record is the whole of what there is rather than the remainder.
    tmdb_shows = service.tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    # Every season and episode under those rows is walked below, which is a query
    # a season unless they are asked for together up front.
    session.exec(
        select(Show)
        .where(col(Show.id).in_([show.id for show in [*shows, *tmdb_shows]]))
        .options(selectinload(Show.seasons).selectinload(Season.episodes)),
    ).all()

    site_seasons = [season for show in shows for season in show.active_children]
    tmdb_seasons = [season for show in tmdb_shows for season in show.active_children]
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
    title_episode_ids = _title_episode_ids(session, channel_show.canonical_show_id)
    site_season_ids = {season.id for season in site_seasons}
    listed_episode_ids = {
        episode.id
        for episode in all_episodes
        if canonical_id_of(episode) in title_episode_ids
        or (
            not episode.canonical_episode_links and episode.season_id in site_season_ids
        )
    }
    return _WhitelistMedia(
        shows=shows,
        tmdb_shows=tmdb_shows,
        site_seasons=site_seasons,
        tmdb_seasons=tmdb_seasons,
        episode_seasons=episode_seasons,
        listed_episode_ids=listed_episode_ids,
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
def _canonical_orders(
    session: Session,
    canonical_episode_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, float]:
    """Read where each canonical episode sits, keyed by its id.

    A row is listed under the number the episode itself carries rather than the number
    the website gave its non-canonical row, so it is ordered on that same number. Two
    websites number an episode differently, and one of them numbering a recap or a
    double-length episode its own way is what puts a non-canonical row's own order out
    of step with the episode being listed.
    """
    if not canonical_episode_ids:
        return {}
    rows = session.exec(
        select(Episode.id, Episode.episode_number, Episode.sort_order).where(
            col(Episode.id).in_(set(canonical_episode_ids)),
        ),
    ).all()
    orders: dict[uuid.UUID, float] = {}
    for episode_id, episode_number, sort_order in rows:
        order = episode_number if episode_number is not None else sort_order
        if order is not None:
            orders[episode_id] = float(order)
    return orders


# TODO: Validate
def _episode_sort_key(
    episode: Episode | WhitelistEpisodeOutput | _SeasonEpisodeRow,
    order: float | None = None,
) -> tuple[float, str]:
    """Order an episode by where the episode sits, then by its own identifier.

    `order` is where the canonical row puts it, which is what the row is labelled
    with; where there is none, the website's own order stands in. A row nothing
    ordered sits after the ones something did, and the identifier settles the
    rest, so a page boundary falls in the same place on every request rather than
    wherever the database happened to answer in.
    """
    if order is None:
        order = _UNORDERED if episode.sort_order is None else float(episode.sort_order)
    return order, str(episode.id)


# TODO: Validate
def _season_sort_key(season: Season) -> tuple[bool, int, str]:
    number = (
        season.season_number if season.season_number is not None else season.sort_order
    )
    return number is None, number or 0, str(season.id)


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


# TODO: Validate
def _season_episode_rows(
    session: Session,
    channel_show: ChannelShow,
    season_id: uuid.UUID,
) -> list[_SeasonEpisodeRow]:
    shows = service.shows_for_channel_show(session, channel_show)
    tmdb_shows = service.tmdb_shows_for_channel_show(session, channel_show)
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

    fill_episodes(session, page)
    # A filter is about the media rather than one website's non-canonical row of it, so
    # the rows read as TMDB has the media, with the website only standing in for what
    # TMDB has no record of.
    prefer_canonical_episodes(session, page)

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

    fill_episodes(session, episodes)
    prefer_canonical_episodes(session, episodes)
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


# FAST003 - Parameter is used by ReadableShow.
# TODO: Validate
@channels_router.get("/for-show/{show_id}")  # noqa: FAST003
def get_channels_for_show(
    session: SessionDep,
    current_user: CurrentUser,
    show: ReadableShow,
) -> list[ChannelShowMembership]:
    """List the `User`'s `Channel`s, saying which already hold a title."""
    return service.channels_with_show_membership(session, current_user, show)


# FAST003 - Parameters are used by EditableChannel and ReadableShow.
# TODO: Validate
@channels_router.post("/{channel_id}/add-show/{show_id}")  # noqa: FAST003
def add_channel_show(
    session: SessionDep,
    channel: EditableChannel,
    show: ReadableShow,
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
router.include_router(admin_router)
