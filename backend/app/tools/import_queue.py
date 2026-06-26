# TODO: Validate

import traceback
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, select

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSeasonFilter,
    ChannelShow,
    URLStatus,
)
from app.database import automatically_import_models, engine
from app.episodes.models import Episode
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
automatically_import_models()


def import_queue(session: Session) -> None:
    statement = select(ChannelQueue).where(
        col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
    )
    results = session.exec(statement)
    queue_items = list(results)

    # Move YouTube URLs to the end of the queue
    youtube_items = [item for item in queue_items if "youtube.com" in item.url.lower()]
    non_youtube_items = [
        item for item in queue_items if "youtube.com" not in item.url.lower()
    ]
    queue_items = non_youtube_items + youtube_items

    # Each item runs in its own transaction so a failure marks just that item
    # as FAILED without rolling back other items, and the FAILED status is
    # persisted (avoiding infinite retries from the SELECT above).
    for queue_item in queue_items:
        logger.info(f"Importing URL: {queue_item.url}")
        for plugin in plugins:
            if not plugin.is_valid_url_format(queue_item.url):
                continue
            if not plugin.implements("import_url"):
                continue
            try:
                queue_item.status = URLStatus.IMPORTING
                plugin_instance = plugin(session)
                import_results = plugin_instance.import_url(queue_item.url)
                add_results_to_channel(session, import_results, queue_item.channel)
            except InvalidURLError:
                logger.warning(f"Invalid URL {plugin.__name__}: {queue_item.url}")
                note = "Invalid URL."
            # BLE001 - capture all exceptions so one bad URL can't stall the queue.
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"Error importing {plugin.__name__}: {queue_item.url}",
                )
                # Rollback first so partial import work is discarded, then
                # re-mark FAILED on the now-expired row so the next commit
                # actually persists the status.
                session.rollback()
                note = "".join(
                    traceback.format_exception(type(e), e, e.__traceback__),
                )
            else:
                queue_item.status = URLStatus.IMPORTED
                session.commit()
                break
            queue_item.status = URLStatus.FAILED
            queue_item.note = note
            session.commit()
            break
        else:
            logger.warning(f"No valid plugin found for URL: {queue_item.url}")
            queue_item.status = URLStatus.FAILED
            queue_item.note = "No valid plugin found."
            session.commit()


def add_results_to_channel(
    session: Session,
    results: list[URLImportResult],
    channel: Channel,
) -> None:
    existing_channel_shows = {show.show_id: show for show in channel.shows}
    for result in results:
        if existing_channel_show := existing_channel_shows.get(result.show.id):
            _extend_channel_show(session, existing_channel_show, result)
        else:
            _create_channel_show(session, channel, result)


def _create_channel_show(
    session: Session,
    channel: Channel,
    result: URLImportResult,
) -> None:
    channel_show = ChannelShow(
        channel_id=channel.id,
        show_id=result.show.id,
        is_whitelist=result.is_whitelist,
        is_blacklist_only=False,
    )
    channel.shows.append(channel_show)

    for season in result.seasons:
        session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )

    for episode in result.episodes:
        session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode.id,
            ),
        )


def _extend_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
) -> None:
    """Merge an import into an existing `ChannelShow`.

    Explicitly importing a show promotes a filter-only show (created when an episode
    was blacklisted from an included channel) into a full member, adopts the mode the
    import asks for (whole-show import => blacklist/opt-out, season/episode import =>
    whitelist/opt-in), and preserves the user's existing blacklist:

    - In blacklist mode the blacklisted episodes are simply the entries on the blacklist.
    - In whitelist mode they are the inverse: episodes are whitelisted, except a
      blacklisted episode whose season is whitelisted gets an episode filter so it stays
      hidden (and a blacklisted episode is never whitelisted).
    """
    existing_channel_show.is_blacklist_only = False

    was_whitelist = existing_channel_show.is_whitelist
    existing_season_ids: set[UUID] = {
        season_filter.season_id
        for season_filter in existing_channel_show.season_filters
    }
    existing_episode_ids: set[UUID] = {
        episode_filter.episode_id
        for episode_filter in existing_channel_show.episode_filters
    }
    # Existing episode filters are a blacklist only while the show is in blacklist mode.
    blacklisted_episode_ids: set[UUID] = (
        set() if was_whitelist else existing_episode_ids
    )

    result_season_ids: set[UUID] = {season.id for season in result.seasons}
    result_episode_ids: set[UUID] = {episode.id for episode in result.episodes}

    if result.is_whitelist:
        season_ids = (
            (existing_season_ids if was_whitelist else set()) | result_season_ids
        )
        whitelisted_episode_ids = (
            (existing_episode_ids if was_whitelist else set()) | result_episode_ids
        ) - blacklisted_episode_ids
        # A blacklisted episode whose season is now whitelisted needs an episode filter
        # to stay hidden; one whose season isn't whitelisted is already excluded.
        season_by_blacklisted_episode = _season_ids_for_episodes(
            session,
            blacklisted_episode_ids,
        )
        exclusion_episode_ids = {
            episode_id
            for episode_id, season_id in season_by_blacklisted_episode.items()
            if season_id in season_ids
        }
        episode_ids = whitelisted_episode_ids | exclusion_episode_ids
    else:
        # Opt-out: show everything except the (merged) blacklist.
        season_ids = set()
        episode_ids = blacklisted_episode_ids | result_episode_ids

    existing_channel_show.is_whitelist = result.is_whitelist
    _replace_filters(session, existing_channel_show, season_ids, episode_ids)


def _season_ids_for_episodes(
    session: Session,
    episode_ids: set[UUID],
) -> dict[UUID, UUID]:
    """Map each episode id to its season id."""
    if not episode_ids:
        return {}
    rows = session.exec(
        select(Episode.id, Episode.season_id).where(col(Episode.id).in_(episode_ids)),
    ).all()
    return dict(rows)


def _replace_filters(
    session: Session,
    channel_show: ChannelShow,
    season_ids: set[UUID],
    episode_ids: set[UUID],
) -> None:
    """Replace a channel show's season/episode filters with the given sets."""
    for season_filter in list(channel_show.season_filters):
        session.delete(season_filter)
    for episode_filter in list(channel_show.episode_filters):
        session.delete(episode_filter)
    # Flush the deletes before re-inserting so reused primary keys don't collide.
    session.flush()
    for season_id in season_ids:
        session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season_id,
            ),
        )
    for episode_id in episode_ids:
        session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
            ),
        )


if __name__ == "__main__":
    with Session(engine) as session:
        import_queue(session)
