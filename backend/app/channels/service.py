# TODO: Validate
from collections.abc import Sequence
from functools import cache
from uuid import UUID

from sqlmodel import Session

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSeasonFilter,
    ChannelShow,
    URLStatus,
)
from app.channels.schemas import (
    SortOptionOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


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


def toggle_episode_whitelist(
    session: Session,
    channel_show: ChannelShow,
    episode_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    if marked and episode_id not in existing:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
            ),
        )
    elif not marked and episode_id in existing:
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            episode_id,
        )
        if existing_episode:
            session.delete(existing_episode)


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
