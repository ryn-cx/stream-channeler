# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from uuid import UUID

from sqlmodel import Session, col, delete

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSavedEpisodeOrder,
    ChannelSeasonFilter,
    ChannelShow,
    URLStatus,
)
from app.channels.schemas import (
    ChannelOutput,
    ChannelPublicOutput,
    SortOptionOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User


def channel_output(channel: Channel, viewer: User | None) -> ChannelOutput:
    output = ChannelOutput.model_validate(channel)
    if not channel.anonymous:
        return output
    if viewer and (viewer.is_superuser or viewer.id == channel.user_id):
        return output
    output.user_id = None
    return output


def public_channel_output(
    channel: Channel,
    username: str | None,
) -> ChannelPublicOutput:
    anonymous = channel.anonymous
    return ChannelPublicOutput(
        id=channel.id,
        user_id=None if anonymous else channel.user_id,
        name=channel.name,
        channel_number=channel.channel_number,
        visibility=channel.visibility,
        default_order=channel.default_order,
        description=channel.description,
        anonymous=anonymous,
        username=None if anonymous else username,
    )


def add_urls_to_channel_import_queue(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    output: list[ChannelQueue] = []
    # Remove duplicates without changing the order allowing the output order to match
    # the input order.
    unique_urls = dict.fromkeys(urls)
    for url in unique_urls:
        stripped_url = url.strip()
        queue_record = session.get(ChannelQueue, (channel.id, stripped_url))

        # If the entry already exists reset it to pending because the user may have
        # removed it from the channel or it may have failed to import for some reaosn.
        if queue_record:
            queue_record.status = URLStatus.PENDING
        else:
            queue_record = ChannelQueue(
                channel_id=channel.id,
                url=stripped_url,
                status=URLStatus.PENDING,
            )
            session.add(queue_record)

        output.append(queue_record)

    session.commit()
    return output


def update_whitelist(
    session: Session,
    channel_show: ChannelShow,
    config: WhitelistShowInput,
) -> None:
    """Update whitelist records for a channel show."""
    if config.is_whitelist is not None:
        channel_show.is_whitelist = config.is_whitelist

    existing_seasons = {season.season_id for season in channel_show.season_filters}
    existing_episodes = {episode.episode_id for episode in channel_show.episode_filters}

    for season in config.seasons:
        toggle_season_whitelist(
            session,
            channel_show,
            season.id,
            existing_seasons,
            marked=season.marked,
        )
    for episode in config.episodes:
        toggle_episode_whitelist(
            session,
            channel_show,
            episode.id,
            existing_episodes,
            marked=episode.marked,
            expires_at=episode.expires_at,
        )

    session.commit()


def toggle_season_whitelist(
    session: Session,
    channel_show: ChannelShow,
    season_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    if marked and season_id not in existing:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season_id,
            ),
        )
    elif not marked and season_id in existing:
        existing_season = ChannelSeasonFilter.get(session, channel_show, season_id)
        if existing_season:
            session.delete(existing_season)


def toggle_episode_whitelist(  # noqa: PLR0913 - mirrors toggle_season_whitelist plus expiry
    session: Session,
    channel_show: ChannelShow,
    episode_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    if marked and episode_id not in existing:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
                expires_at=expires_at,
            ),
        )
    elif marked and episode_id in existing:
        # Re-marking an existing entry updates its expiry.
        existing_episode = ChannelEpisodeFilter.get(session, channel_show, episode_id)
        if existing_episode:
            existing_episode.expires_at = expires_at
    elif not marked and episode_id in existing:
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            episode_id,
        )
        if existing_episode:
            session.delete(existing_episode)


def blacklist_episode_on_channel(
    session: Session,
    channel: Channel,
    show: Show,
    episode_id: UUID,
    expires_at: datetime | None = None,
) -> ChannelShow:
    """Blacklist a single episode for `channel`.

    Gets or creates the `ChannelShow` linking `channel` and `show`. A newly created
    `ChannelShow` is a filter-only show (`is_blacklist_only=True`) in blacklist mode, so
    the show's other episodes are not pulled into the channel. Adds (or updates the expiry
    of) a `ChannelEpisodeFilter` for the episode.
    """
    channel_show = ChannelShow.get(session, channel, show)
    if channel_show is None:
        channel_show = ChannelShow(
            channel_id=channel.id,
            show_id=show.id,
            is_whitelist=False,
            is_blacklist_only=True,
        )
        session.add(channel_show)

    existing_filter = ChannelEpisodeFilter.get(session, channel_show, episode_id)
    if existing_filter is None:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
                expires_at=expires_at,
            ),
        )
    else:
        existing_filter.expires_at = expires_at

    session.commit()
    session.refresh(channel_show)
    return channel_show


def set_channel_order(
    session: Session,
    channel: Channel,
    episode_ids: Sequence[UUID],
) -> None:
    session.exec(  # type: ignore[call-overload]
        delete(ChannelSavedEpisodeOrder).where(
            col(ChannelSavedEpisodeOrder.channel_id) == channel.id,
        ),
    )
    session.flush()
    for position, episode_id in enumerate(episode_ids):
        session.add(
            ChannelSavedEpisodeOrder(
                channel_id=channel.id,
                episode_id=episode_id,
                position=position,
            ),
        )
    session.commit()


@cache
def get_sort_options() -> list[SortOptionOutput]:
    """Build and cache the list of all possible sorting options."""
    options: list[SortOptionOutput] = [
        SortOptionOutput(
            label=f"{model.__name__} - {field_name.replace('_', ' ').title()}",
            # If this value does not match it should raise an error.
            model=model.__name__.lower(),  # type: ignore[arg-type]
            field=field_name,
        )
        for model in (Episode, Season, Show, Source, Plugin)
        for field_name in model.SORTABLE_FIELDS
    ]
    options.sort(key=lambda option: option.label)
    return options
