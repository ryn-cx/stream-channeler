# TODO: Validate
import json
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

from fastapi import HTTPException
from loguru import logger
from sqlmodel import Session, col, select

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelOptions,
    ChannelReadOptions,
    HomeGuideChannel,
    HomeGuideEpisode,
    HomeGuideOutput,
    HomeGuidePlugin,
    HomeGuideSeason,
    HomeGuideTitle,
)
from app.channels.service.channels import scoped_channel_list_output
from app.channels.service.episodes import channel_episodes_output
from app.database import engine
from app.schemas import RecordScope


# TODO: Validate
def _home_channel_episodes(
    session: Session,
    channel: Channel,
    random_seed: int,
) -> ChannelEpisodesOutput:
    try:
        default_order = (
            json.loads(channel.default_order) if channel.default_order else {}
        )
        options = ChannelOptions.model_validate(
            {"limit": 20, "randomSeed": random_seed, **default_order},
        )
        return channel_episodes_output(channel, options, None, session)
    except ValueError, HTTPException:
        options = ChannelOptions(limit=10, random_seed=random_seed)
        return channel_episodes_output(channel, options, None, session)


# TODO: Validate
def _add_home_channel(
    output: HomeGuideOutput,
    channel: Channel,
    episodes: ChannelEpisodesOutput,
) -> None:
    output.channels.append(
        HomeGuideChannel(
            id=channel.id,
            name=channel.name,
            default_order=channel.default_order,
            episode_ids=[episode.id for episode in episodes.episodes],
            member_channel_ids={
                episode.id: episode.channel_ids
                for episode in episodes.episodes
                if episode.channel_ids != [channel.id]
            },
        ),
    )
    for episode in episodes.episodes:
        output.episodes.setdefault(
            episode.id,
            HomeGuideEpisode.model_validate(
                {
                    **episode.model_dump(),
                    "thumbnail_url": episode.thumbnail_url or episode.image_url,
                },
            ),
        )
    for season_id, season in episodes.seasons.items():
        output.seasons.setdefault(season_id, HomeGuideSeason.model_validate(season))
    for title_id, title in episodes.titles.items():
        output.titles.setdefault(title_id, HomeGuideTitle.model_validate(title))
    output.sources.update(episodes.sources)
    for plugin_id, plugin in episodes.plugins.items():
        output.plugins.setdefault(plugin_id, HomeGuidePlugin.model_validate(plugin))


# TODO: Validate
def build_home_guide() -> HomeGuideOutput:
    random_seed = random.randint(0, 2**31)  # noqa: S311
    with Session(engine) as session:
        listing = scoped_channel_list_output(
            session,
            None,
            ChannelReadOptions.model_validate(
                {
                    "scope": RecordScope.public,
                    "limit": 25,
                    "random_seed": random_seed,
                    "sort_options": "[]",
                    "filter_options": "[]",
                },
            ),
        )
        channels_by_id = {
            channel.id: channel
            for channel in session.exec(
                select(Channel).where(
                    col(Channel.id).in_([row.id for row in listing.data]),
                ),
            ).all()
        }
        output = HomeGuideOutput(
            channels=[],
            episodes={},
            seasons={},
            titles={},
            sources={},
            plugins={},
            total_count=listing.total_count,
        )
        for row in listing.data:
            channel = channels_by_id[row.id]
            _add_home_channel(
                output,
                channel,
                _home_channel_episodes(session, channel, random_seed),
            )
        return output


# TODO: Validate
class _HomeGuideCache:
    # TODO: Validate
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._prepared: HomeGuideOutput | None = None
        self._refill_future: Future[HomeGuideOutput] | None = None
        self._last_build_started = 0.0

    # TODO: Validate
    def _build(self) -> HomeGuideOutput:
        self._last_build_started = time.monotonic()
        return build_home_guide()

    # TODO: Validate
    def _schedule_refill(self) -> Future[HomeGuideOutput]:
        if self._refill_future is None:
            self._refill_future = self._executor.submit(self._refill)
        return self._refill_future

    # TODO: Validate
    def warm(self) -> None:
        with self._lock:
            self._schedule_refill()

    # TODO: Validate
    def serve(self) -> HomeGuideOutput:
        with self._lock:
            served = self._prepared
            pending = self._schedule_refill()
        return pending.result() if served is None else served

    # TODO: Validate
    @logger.catch(reraise=True)
    def _refill(self) -> HomeGuideOutput:
        try:
            time.sleep(max(0.0, self._last_build_started + 1 - time.monotonic()))
            prepared = self._build()
            with self._lock:
                self._prepared = prepared
            return prepared
        finally:
            with self._lock:
                self._refill_future = None


_home_guide_cache = _HomeGuideCache()


# TODO: Validate
def home_guide_output() -> HomeGuideOutput:
    return _home_guide_cache.serve()


# TODO: Validate
def warm_home_guide() -> None:
    _home_guide_cache.warm()
