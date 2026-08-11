# TODO: Validate
"""Temporary benchmark: SQL source dedup vs the Python dedup it replaced."""

import random
import statistics
import time
from collections.abc import Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import literal
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.episode_selector.query_builder import EpisodeResult
from app.channels.episode_selector.show_counts import limit_shows
from app.channels.episode_selector.source_dedup import deduplicate_episodes
from app.channels.episode_selector.watch_filters import latest_watch_by_identifier
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.models import Visibility
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch
from tests.app.channels.utils import create_random_channel, create_random_channel_show
from tests.app.plugins.utils import create_random_plugin
from tests.app.sources.utils import create_random_source
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import create_random_user
from tests.app.utils.utils import build_random_model, random_past_timestamp

TITLE_COUNT = 40
SEASONS_PER_TITLE = 5
EPISODES_PER_SEASON = 80
WATCH_COUNT = 500
MINIMUM_DURATION = 300
MAXIMUM_DURATION = 3600
REPEATS = 7


# TODO: Validate
class UnguardedEpisodeQueryBuilder(EpisodeQueryBuilder):
    """SQL dedup with no single-source guard: the window runs unconditionally."""

    # TODO: Validate
    def _fetch_holds_copied_titles(self) -> bool:
        return True


# TODO: Validate
class LegacyEpisodeQueryBuilder(EpisodeQueryBuilder):
    """The reading this branch replaced: no SQL dedup, collapsed in Python after."""

    # TODO: Validate
    def _source_rank_column(self):  # noqa: ANN202
        return literal(1).label("source_rank")

    # TODO: Validate
    def _source_keys_by_episode(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, str]:
        if not episodes:
            return {}
        rows = self._session.exec(
            select(Episode.id, Source.key)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(col(Episode.id).in_([episode.id for episode in episodes])),
        ).all()
        return dict(rows)

    # TODO: Validate
    def _deduplicate_by_identifier(
        self,
        episodes: list[Episode],
    ) -> list[Episode]:
        source_keys = self._source_keys_by_episode(episodes)
        return deduplicate_episodes(episodes, source_keys, self._source_config)

    # TODO: Validate
    def get_episodes(self) -> list[EpisodeResult]:
        query: Select[tuple[Episode, UUID]] = self._base_query()
        query = self._join_whitelist(query)
        query = self._join_last_watched(query)
        query = self._join_saved_order(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._apply_channel_specific_blacklist(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_metadata_plugins(query)
        query = self._filter_disabled_sources(query)
        query = self._filter_by_watch_state(query)
        query = self._filter_by_ranges(query)
        query = self._sort_and_deduplicate(query)
        query = self._apply_limit(query)

        ordered_episodes: list[Episode] = []
        channels_by_episode: dict[UUID, list[UUID]] = {}
        for episode, channel_id in self._session.exec(query).all():
            if episode.id not in channels_by_episode:
                channels_by_episode[episode.id] = []
                ordered_episodes.append(episode)
            if channel_id not in channels_by_episode[episode.id]:
                channels_by_episode[episode.id].append(channel_id)

        ordered_episodes = self._deduplicate_by_identifier(ordered_episodes)
        ordered_episodes = limit_shows(
            self._session,
            self._user,
            ordered_episodes,
            self._channel_options,
        )
        ordered_episodes = ordered_episodes[: self._result_limit()]

        watches = (
            latest_watch_by_identifier(self._session, self._user, ordered_episodes)
            if self._user
            else {}
        )
        return [
            EpisodeResult(
                episode=episode,
                channel_id=channels_by_episode[episode.id][0],
                channel_ids=channels_by_episode[episode.id],
                latest_watch=watches.get(episode.episode_identifier),
            )
            for episode in ordered_episodes
        ]


# TODO: Validate
def _build_channel(
    session: Session,
    user: User,
    source_count: int,
) -> tuple[Channel, list[Episode]]:
    """A channel holding `TITLE_COUNT` titles, each copied onto `source_count` sources."""
    channel = create_random_channel(session, user=user.id, visibility=Visibility.public)
    sources = []
    for _ in range(source_count):
        plugin = create_random_plugin(session, user, visibility=Visibility.public)
        sources.append(create_random_source(session, plugin))

    episodes: list[Episode] = []
    for title_index in range(TITLE_COUNT):
        show_identifier = f"TMDB benchmark-title-{title_index}"
        first_show: Show | None = None
        for source in sources:
            show = create_random_show(session, source, show_identifier=show_identifier)
            first_show = first_show or show
            for season_number in range(1, SEASONS_PER_TITLE + 1):
                season = build_random_model(
                    Season,
                    show_id=show.id,
                    deleted_at=None,
                    season_number=season_number,
                    season_identifier=f"{show_identifier}-s{season_number}",
                )
                session.add(season)
                session.flush()
                episodes.extend(
                    build_random_model(
                        Episode,
                        season_id=season.id,
                        deleted_at=None,
                        episode_number=episode_number,
                        episode_identifier=(
                            f"{show_identifier}-s{season_number}-e{episode_number}"
                        ),
                        duration=random.randint(MINIMUM_DURATION, MAXIMUM_DURATION),  # noqa: S311
                        air_date=random_past_timestamp(),
                        release_date=random_past_timestamp(),
                    )
                    for episode_number in range(1, EPISODES_PER_SEASON + 1)
                )
        create_random_channel_show(session, channel, first_show, is_whitelist=False)
    session.add_all(episodes)
    session.flush()
    return channel, episodes


# TODO: Validate
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


# TODO: Validate
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
        limit=1000,
    )


# TODO: Validate
def _time_read(
    builder_class: type[EpisodeQueryBuilder],
    session: Session,
    channel: Channel,
    options: ChannelOptions,
    user: User,
) -> tuple[float, int]:
    start = time.perf_counter()
    results = builder_class(session, channel, options, user).get_episodes()
    return time.perf_counter() - start, len(results)


# TODO: Validate
def _compare(
    session: Session,
    channel: Channel,
    user: User,
    options: ChannelOptions,
    label: str,
) -> None:
    variants: dict[str, type[EpisodeQueryBuilder]] = {
        "guarded sql": EpisodeQueryBuilder,
        "unguarded sql": UnguardedEpisodeQueryBuilder,
        "python": LegacyEpisodeQueryBuilder,
    }
    times: dict[str, list[float]] = {name: [] for name in variants}
    counts: dict[str, int] = {}
    for repeat in range(REPEATS):
        for name, builder_class in variants.items():
            logger.info(f"[{label}] repeat {repeat} starting {name}")
            seconds, counts[name] = _time_read(
                builder_class,
                session,
                channel,
                options,
                user,
            )
            logger.info(f"[{label}] repeat {repeat} {name} {seconds * 1000:.0f}ms")
            times[name].append(seconds)

    report = " | ".join(
        f"{name} {statistics.median(times[name]) * 1000:.0f}ms "
        f"(min {min(times[name]) * 1000:.0f}ms, {counts[name]} eps)"
        for name in variants
    )
    logger.info(f"[{label}] {report}")


# TODO: Validate
def _filtered_query(
    builder: EpisodeQueryBuilder,
) -> Select[tuple[Episode, UUID]]:
    query: Select[tuple[Episode, UUID]] = builder._base_query()  # noqa: SLF001
    query = builder._join_whitelist(query)  # noqa: SLF001
    query = builder._join_last_watched(query)  # noqa: SLF001
    query = builder._join_saved_order(query)  # noqa: SLF001
    query = builder._filter_deleted_media(query)  # noqa: SLF001
    query = builder._filter_episodes_by_channels(query)  # noqa: SLF001
    query = builder._apply_channel_specific_blacklist(query)  # noqa: SLF001
    query = builder._filter_by_plugin_visibility(query)  # noqa: SLF001
    query = builder._filter_metadata_plugins(query)  # noqa: SLF001
    query = builder._filter_disabled_sources(query)  # noqa: SLF001
    query = builder._filter_by_watch_state(query)  # noqa: SLF001
    return builder._filter_by_ranges(query)  # noqa: SLF001


# TODO: Validate
def _time_query(session: Session, query: object, repeats: int = 5) -> float:
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        rows = session.exec(query).all()  # type: ignore[arg-type]
        times.append(time.perf_counter() - start)
    logger.info(f"    rows fetched: {len(rows)}")
    return statistics.median(times)


# TODO: Validate
def _isolate_unsorted_cost(
    session: Session,
    channel: Channel,
    user: User,
    label: str,
) -> None:
    """Split the unsorted regression into 'window cost' and 'no early exit' cost."""
    options = ChannelOptions()
    sql_builder = EpisodeQueryBuilder(session, channel, options, user)
    legacy_builder = LegacyEpisodeQueryBuilder(session, channel, options, user)

    windowed = sql_builder._sort_and_deduplicate(  # noqa: SLF001
        _filtered_query(sql_builder),
    ).limit(1000)
    plain_limited = legacy_builder._sort_and_deduplicate(  # noqa: SLF001
        _filtered_query(legacy_builder),
    ).limit(1000)
    plain_full = legacy_builder._sort_and_deduplicate(  # noqa: SLF001
        _filtered_query(legacy_builder),
    )

    logger.info(f"[{label}] no window + LIMIT 1000 (old)")
    old_seconds = _time_query(session, plain_limited)
    logger.info(f"[{label}] no window, no LIMIT (cost of seeing every row)")
    full_seconds = _time_query(session, plain_full)
    logger.info(f"[{label}] window + LIMIT 1000 (new)")
    new_seconds = _time_query(session, windowed)
    logger.info(
        f"[{label}] old {old_seconds * 1000:.0f}ms | "
        f"full scan {full_seconds * 1000:.0f}ms | "
        f"new {new_seconds * 1000:.0f}ms",
    )


# TODO: Validate
class TestDedupBenchmarkDuplicated:
    # TODO: Validate
    def test_three_sources_per_title(self, class_scoped_session: Session) -> None:
        session = class_scoped_session
        user = create_random_user(session)
        channel, episodes = _build_channel(session, user, source_count=3)
        _add_watches(session, user, episodes)
        logger.info(f"[3 sources] {len(episodes)} episode rows")

        _isolate_unsorted_cost(session, channel, user, "3 sources")
        _compare(session, channel, user, ChannelOptions(), "3 sources, unsorted")
        _compare(session, channel, user, _complex_options(), "3 sources, complex sort")


# TODO: Validate
class TestDedupBenchmarkSingleSource:
    # TODO: Validate
    def test_one_source_per_title(self, class_scoped_session: Session) -> None:
        session = class_scoped_session
        user = create_random_user(session)
        channel, episodes = _build_channel(session, user, source_count=1)
        _add_watches(session, user, episodes)
        logger.info(f"[1 source] {len(episodes)} episode rows")

        _isolate_unsorted_cost(session, channel, user, "1 source")
        _compare(session, channel, user, ChannelOptions(), "1 source, unsorted")
        _compare(session, channel, user, _complex_options(), "1 source, complex sort")
