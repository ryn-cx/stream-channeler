# TODO: Validate
from collections.abc import Sequence

from sqlmodel import Session

from app.channels.models import (
    Channel,
    ChannelEpisodeWhiteList,
    ChannelQueue,
    ChannelSeasonWhiteList,
    ChannelShow,
    URLStatus,
)
from app.channels.schemas import ChannelQueueInput, WhitelistShowInput


def add_urls_to_channel_import_queue(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    queue_by_url = {queue.url: queue for queue in channel.queue}

    # Remove duplicates while preserving order
    unique_urls = dict.fromkeys(urls)

    output: list[ChannelQueue] = []
    for url in unique_urls:
        stripped_url = url.strip()
        existing_queue_entry = queue_by_url.get(stripped_url)

        queue_entry = ChannelQueueInput(
            url=stripped_url,
            status=URLStatus.PENDING,
        ).upsert(channel, existing_queue_entry)

        output.append(queue_entry)

    session.commit()
    return output


def update_whitelist(
    session: Session,
    channel_show: ChannelShow,
    config: WhitelistShowInput,
) -> None:
    """Update whitelist entries for a channel show, only modifying provided values."""
    if config.whitelist_mode is not None:
        channel_show.white_list_mode = config.whitelist_mode

    existing_seasons = {s.season_id for s in channel_show.season_white_list}
    existing_episodes = {e.episode_id for e in channel_show.episode_white_list}

    for season in config.seasons:
        _toggle_season(
            session,
            channel_show,
            season.id,
            season.enabled,
            existing_seasons,
        )
    for episode in config.episodes:
        _toggle_episode(
            session,
            channel_show,
            episode.id,
            episode.enabled,
            existing_episodes,
        )

    session.commit()


def _toggle_season(
    session: Session,
    channel_show: ChannelShow,
    season_id: object,
    enabled: bool,
    existing: set[object],
) -> None:
    if enabled and season_id not in existing:
        channel_show.season_white_list.append(
            ChannelSeasonWhiteList(
                channel_show_id=channel_show.id,
                season_id=season_id,
            ),
        )
    elif not enabled and season_id in existing:
        for entry in channel_show.season_white_list:
            if entry.season_id == season_id:
                session.delete(entry)
                break


def _toggle_episode(
    session: Session,
    channel_show: ChannelShow,
    episode_id: object,
    enabled: bool,
    existing: set[object],
) -> None:
    if enabled and episode_id not in existing:
        channel_show.episode_white_list.append(
            ChannelEpisodeWhiteList(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
            ),
        )
    elif not enabled and episode_id in existing:
        for entry in channel_show.episode_white_list:
            if entry.episode_id == episode_id:
                session.delete(entry)
                break
