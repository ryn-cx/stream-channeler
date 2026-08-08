# TODO: Validate

import random
import time

from loguru import logger
from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.models import Visibility
from app.seasons.models import Season
from app.users.models import User
from app.watches.models import Watch
from tests.app.channels.utils import create_random_channel, create_random_channel_show
from tests.app.plugins.utils import create_random_plugin
from tests.app.shows.utils import create_random_show
from tests.app.sources.utils import create_random_source
from tests.app.users.utils import create_random_user
from tests.app.utils.utils import build_random_model, random_past_timestamp

SHOW_COUNT = 20
SEASONS_PER_SHOW = 5
EPISODES_PER_SEASON = 100
EPISODE_COUNT = SHOW_COUNT * SEASONS_PER_SHOW * EPISODES_PER_SEASON
WATCH_COUNT = 500
MINIMUM_DURATION = 300
MAXIMUM_DURATION = 3600


def _build_channel(session: Session, user: User) -> tuple[Channel, list[Episode]]:
    plugin = create_random_plugin(session, user, visibility=Visibility.public)
    source = create_random_source(session, plugin)
    channel = create_random_channel(session, user=user.id, visibility=Visibility.public)

    episodes: list[Episode] = []
    for _ in range(SHOW_COUNT):
        show = create_random_show(session, source)
        create_random_channel_show(session, channel, show, is_whitelist=False)
        for season_number in range(1, SEASONS_PER_SHOW + 1):
            season = build_random_model(
                Season,
                show_id=show.id,
                deleted_at=None,
                season_number=season_number,
            )
            session.add(season)
            session.flush()
            episodes.extend(
                build_random_model(
                    Episode,
                    season_id=season.id,
                    deleted_at=None,
                    episode_number=episode_number,
                    duration=random.randint(MINIMUM_DURATION, MAXIMUM_DURATION),  # noqa: S311
                    air_date=random_past_timestamp(),
                    release_date=random_past_timestamp(),
                )
                for episode_number in range(1, EPISODES_PER_SEASON + 1)
            )
    session.add_all(episodes)
    session.flush()
    return channel, episodes


def _add_watches(session: Session, user: User, episodes: list[Episode]) -> None:
    watched = random.sample(episodes, WATCH_COUNT)
    session.add_all(
        build_random_model(
            Watch,
            user_id=user.id,
            episode_id=episode.id,
            episode_identifier=episode.episode_identifier,
            verified=index % 2 == 0,
            watch_date=random_past_timestamp(),
        )
        for index, episode in enumerate(watched)
    )
    session.flush()


def _complex_options() -> ChannelOptions:
    return ChannelOptions(
        sort_by=[
            {
                "model": "show",
                "field": "random",
                "direction": "ascending",
                "order": "interleave",
            },
            {
                "model": "season",
                "field": "sequential",
                "direction": "ascending",
                "order": "sequential",
            },
            {
                "model": "episode",
                "field": "sequential_zero_last",
                "direction": "ascending",
                "order": "sequential",
                "fuzziness": 3,
            },
            {
                "model": "episode",
                "field": "air_date",
                "direction": "descending",
                "order": "sequential",
                "aggregation": "max",
            },
        ],
        hide_watched=True,
        hide_partially_watched=True,
        minimum_duration=600,
        maximum_duration=3000,
        minimum_air_date_relative=3650,
        total_shows_count=10,
        started_shows_count=5,
        new_shows_count=5,
        limit=1000,
    )


class TestChannelReadBenchmark:
    def test_complex_read_of_ten_thousand_episodes(
        self,
        session_scoped_session: Session,
    ) -> None:
        session = session_scoped_session
        user = create_random_user(session)

        setup_start = time.perf_counter()
        channel, episodes = _build_channel(session, user)
        _add_watches(session, user, episodes)
        setup_seconds = time.perf_counter() - setup_start
        assert len(episodes) == EPISODE_COUNT

        read_start = time.perf_counter()
        builder = EpisodeQueryBuilder(session, channel, _complex_options(), user)
        results = builder.get_episodes()
        read_seconds = time.perf_counter() - read_start

        logger.info(
            f"Benchmark: {EPISODE_COUNT} episodes over {SHOW_COUNT} shows, "
            f"setup {setup_seconds:.2f}s, "
            f"read {read_seconds:.2f}s, "
            f"{len(results)} episodes returned",
        )
        assert results
