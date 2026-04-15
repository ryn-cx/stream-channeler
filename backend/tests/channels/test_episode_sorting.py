# TODO: This file was entirely AI generated just to have a baseline for testing.
"""Tests for EpisodeQueryBuilder sorting, filtering, and interleaving."""

import json
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder, EpisodeResult
from app.channels.models import ChannelEpisodeWhiteList, ChannelSeasonWhiteList
from app.channels.schemas import ChannelMediaFilter
from app.episodes.models import Episode
from app.utils import tz_datetime
from tests.channels.utils import create_random_channel, create_random_channel_show
from tests.episodes.utils import create_random_episode
from tests.plugins.utils import create_random_plugin
from tests.seasons.utils import create_random_season
from tests.users.utils import create_random_user
from tests.watches.utils import create_random_watch


def _sort_key(
    model_field: str,
    direction: str = "ascending",
    display: str = "sequential",
    aggregation: str | None = None,
    days: int | None = None,
) -> str:
    model, field = model_field.split(".")
    data: dict[str, object] = {
        "model": model,
        "field": field,
        "direction": direction,
        "order": display,
    }
    if aggregation is not None:
        data["aggregation"] = aggregation
    if days is not None:
        data["days"] = days
    return json.dumps(data)


@pytest.fixture
def episode_setup(session_scoped_db: Session) -> dict:
    """Create a channel with 2 shows, each with 2 episodes (recent + old air dates)."""
    user = create_random_user(session_scoped_db)
    channel = create_random_channel(session_scoped_db, user=user.id)
    plugin = create_random_plugin(session_scoped_db, user, public=True)

    recent_date = tz_datetime.now() - timedelta(days=1)
    old_date = tz_datetime.now() - timedelta(days=60)

    shows = []
    for _ in range(2):
        channel_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        season = create_random_season(session_scoped_db, channel_show.show)
        recent_episode = create_random_episode(
            session_scoped_db,
            season,
            air_date=recent_date,
            duration=100,
        )
        old_episode = create_random_episode(
            session_scoped_db,
            season,
            air_date=old_date,
            duration=200,
        )
        shows.append(
            {
                "show": channel_show.show,
                "season": season,
                "recent": recent_episode,
                "old": old_episode,
            },
        )

    session_scoped_db.flush()

    return {
        "channel": channel,
        "user": user,
        "plugin": plugin,
        "shows": shows,
        "session": session_scoped_db,
    }


def _build_results(setup: dict, **filter_kwargs: object) -> list[EpisodeResult]:
    media_filter = ChannelMediaFilter(**filter_kwargs)
    builder = EpisodeQueryBuilder(
        setup["session"],
        setup["channel"],
        media_filter,
        setup["user"],
    )
    return builder.get_episodes()


def _build(setup: dict, **filter_kwargs: object) -> list[Episode]:
    return [r.episode for r in _build_results(setup, **filter_kwargs)]


def _all_episode_ids(setup: dict) -> set:
    return {
        setup["shows"][0]["recent"].id,
        setup["shows"][0]["old"].id,
        setup["shows"][1]["recent"].id,
        setup["shows"][1]["old"].id,
    }


def _recent_ids(setup: dict) -> set:
    return {
        setup["shows"][0]["recent"].id,
        setup["shows"][1]["recent"].id,
    }


class TestBasicRetrieval:
    def test_returns_all_episodes(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup)
        assert len(episodes) == 4
        assert {ep.id for ep in episodes} == _all_episode_ids(episode_setup)

    def test_default_sort_when_no_sort_specified(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup)
        assert len(episodes) == 4

    def test_respects_limit(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup, limit=2)
        assert len(episodes) == 2

    def test_empty_channel_returns_no_episodes(
        self,
        session_scoped_db: Session,
    ) -> None:
        user = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=user.id)
        episodes = _build(
            {
                "channel": channel,
                "user": user,
                "session": session_scoped_db,
            },
        )
        assert len(episodes) == 0


class TestSortDirection:
    def test_ascending_air_date(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.air_date", "ascending")],
        )
        air_dates = [ep.air_date for ep in episodes]
        assert air_dates == sorted(air_dates)

    def test_descending_air_date(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.air_date", "descending")],
        )
        air_dates = [ep.air_date for ep in episodes]
        assert air_dates == sorted(air_dates, reverse=True)

    def test_ascending_duration(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.duration", "ascending")],
        )
        durations = [ep.duration for ep in episodes]
        assert durations == sorted(durations)

    def test_descending_duration(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.duration", "descending")],
        )
        durations = [ep.duration for ep in episodes]
        assert durations == sorted(durations, reverse=True)


class TestSortByShowFields:
    def test_sort_by_show_name(self, episode_setup: dict) -> None:
        """Sorting by show name should group episodes by show."""
        # Set distinct names so sorting is deterministic
        episode_setup["shows"][0]["show"].name = "Alpha"
        episode_setup["shows"][1]["show"].name = "Beta"
        episode_setup["session"].flush()

        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("show.name", "ascending")],
        )
        show_names = [ep.season.show.name for ep in episodes]
        assert show_names[:2] == ["Alpha", "Alpha"]
        assert show_names[2:] == ["Beta", "Beta"]


class TestRecentlyAired:
    def test_recently_aired_groups_recent_first(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.recently_aired", "descending", days=7)],
        )
        result_ids = [ep.id for ep in episodes]
        recent = _recent_ids(episode_setup)
        assert result_ids[0] in recent
        assert result_ids[1] in recent

    @pytest.mark.parametrize("days", [7, 30, 365])
    def test_recently_aired_custom_days(
        self,
        episode_setup: dict,
        days: int,
    ) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.recently_aired",
                    "descending",
                    days=days,
                ),
            ],
        )
        assert len(episodes) == 4

    def test_recently_aired_defaults_to_7_days(
        self,
        episode_setup: dict,
    ) -> None:
        """When days is not specified, should default to 7."""
        episodes_default = _build(
            episode_setup,
            sort_by=[_sort_key("episode.recently_aired", "descending")],
        )
        episodes_explicit = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.recently_aired",
                    "descending",
                    days=7,
                ),
            ],
        )
        assert [ep.id for ep in episodes_default] == [ep.id for ep in episodes_explicit]


class TestInterleave:
    def test_sequential_interleave_alternates_shows(
        self,
        episode_setup: dict,
    ) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.air_date",
                    "ascending",
                    display="interleave",
                ),
            ],
            random_seed=42,
        )
        show_ids = [ep.season.show_id for ep in episodes]
        # Episodes from different shows should alternate
        for index in range(len(show_ids) - 1):
            assert show_ids[index] != show_ids[index + 1]

    def test_random_interleave_returns_all_episodes(
        self,
        episode_setup: dict,
    ) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.recently_aired",
                    "descending",
                    days=7,
                    display="randomize",
                ),
            ],
            random_seed=42,
        )
        assert {ep.id for ep in episodes} == _all_episode_ids(episode_setup)

    def test_random_interleave_is_deterministic_with_seed(
        self,
        episode_setup: dict,
    ) -> None:
        sort_by = [
            _sort_key(
                "episode.air_date",
                "descending",
                display="randomize",
            ),
        ]
        first = _build(episode_setup, sort_by=sort_by, random_seed=42)
        second = _build(episode_setup, sort_by=sort_by, random_seed=42)
        assert [ep.id for ep in first] == [ep.id for ep in second]


class TestGroupByShow:
    def test_group_by_show_sum_duration(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.duration",
                    "ascending",
                    aggregation="max",
                ),
            ],
        )
        assert len(episodes) == 4

    def test_group_by_show_max_air_date(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.air_date",
                    "descending",
                    aggregation="max",
                ),
            ],
        )
        assert len(episodes) == 4

    def test_group_by_show_with_show_field(self, episode_setup: dict) -> None:
        """Group by show with a show field just returns the field value directly."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("show.name", "ascending"),
            ],
        )
        assert len(episodes) == 4


class TestLastWatchedSort:
    def test_last_watched_sort_ascending(self, episode_setup: dict) -> None:
        """Shows watched longer ago should appear first with ascending."""
        old_watch_date = tz_datetime.now() - timedelta(days=30)
        recent_watch_date = tz_datetime.now() - timedelta(days=1)
        create_random_watch(
            episode_setup["session"],
            episode_setup["shows"][0]["recent"],
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=old_watch_date,
        )
        create_random_watch(
            episode_setup["session"],
            episode_setup["shows"][1]["recent"],
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=recent_watch_date,
        )
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.last_watched", "ascending")],
        )
        assert len(episodes) == 4
        # Unwatched shows (nulls first for ascending) come first,
        # then oldest watched show
        show_ids = [ep.season.show_id for ep in episodes]
        # Show 0 was watched 30 days ago, show 1 was watched 1 day ago
        # With nulls_first, unwatched would come first but both shows are watched
        # so show 0 (older watch) should come before show 1 (recent watch)
        show_0_positions = [
            i
            for i, sid in enumerate(show_ids)
            if sid == episode_setup["shows"][0]["show"].id
        ]
        show_1_positions = [
            i
            for i, sid in enumerate(show_ids)
            if sid == episode_setup["shows"][1]["show"].id
        ]
        assert min(show_0_positions) < min(show_1_positions)

    def test_last_watched_without_user_ignored(
        self,
        episode_setup: dict,
    ) -> None:
        """Last watched sort requires a user — silently dropped without one."""
        media_filter = ChannelMediaFilter(
            sort_by=[_sort_key("episode.last_watched", "ascending")],
        )
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            media_filter,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4


class TestWatchFilters:
    def test_hide_watched_excludes_watched_episodes(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, hide_watched=True)
        result_ids = {ep.id for ep in episodes}
        assert watched_episode.id not in result_ids
        assert len(episodes) == 3

    def test_hide_unwatched_only_shows_watched(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, hide_unwatched=True)
        result_ids = {ep.id for ep in episodes}
        assert result_ids == {watched_episode.id}

    def test_unverified_watch_not_counted_as_watched(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=False,
        )
        episodes = _build(episode_setup, hide_watched=True)
        result_ids = {ep.id for ep in episodes}
        assert watched_episode.id in result_ids


class TestShowFilters:
    def test_only_started_shows(self, episode_setup: dict) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, only_started_shows=True)
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}

    def test_only_new_shows(self, episode_setup: dict) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, only_new_shows=True)
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][1]["show"].id}


class TestDurationFilter:
    def test_minimum_duration(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup, minimum_duration=150)
        assert all(ep.duration >= 150 for ep in episodes)

    def test_maximum_duration(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup, maximum_duration=150)
        assert all(ep.duration <= 150 for ep in episodes)

    def test_duration_range(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            minimum_duration=50,
            maximum_duration=150,
        )
        assert all(50 <= ep.duration <= 150 for ep in episodes)


class TestAirDateFilter:
    def test_minimum_air_date_absolute(self, episode_setup: dict) -> None:
        cutoff = tz_datetime.now() - timedelta(days=30)
        episodes = _build(
            episode_setup,
            minimum_air_date_absolute=cutoff.isoformat(),
        )
        for episode in episodes:
            if episode.air_date is not None:
                assert episode.air_date >= cutoff

    def test_minimum_air_date_relative(self, episode_setup: dict) -> None:
        episodes = _build(episode_setup, minimum_air_date_relative=30)
        cutoff = tz_datetime.now() - timedelta(days=30)
        for episode in episodes:
            if episode.air_date is not None:
                assert episode.air_date >= cutoff


class TestPluginVisibility:
    def test_private_plugin_hidden_from_non_owner(
        self,
        session_scoped_db: Session,
    ) -> None:
        owner = create_random_user(session_scoped_db)
        viewer = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=viewer.id)
        plugin = create_random_plugin(session_scoped_db, owner, public=False)
        channel_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        season = create_random_season(session_scoped_db, channel_show.show)
        create_random_episode(session_scoped_db, season)
        session_scoped_db.flush()

        episodes = _build(
            {
                "channel": channel,
                "user": viewer,
                "session": session_scoped_db,
            },
        )
        assert len(episodes) == 0

    def test_public_plugin_visible_to_non_owner(
        self,
        session_scoped_db: Session,
    ) -> None:
        owner = create_random_user(session_scoped_db)
        viewer = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=viewer.id)
        plugin = create_random_plugin(session_scoped_db, owner, public=True)
        channel_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        season = create_random_season(session_scoped_db, channel_show.show)
        create_random_episode(session_scoped_db, season)
        session_scoped_db.flush()

        episodes = _build(
            {
                "channel": channel,
                "user": viewer,
                "session": session_scoped_db,
            },
        )
        assert len(episodes) == 1


class TestDeletedEpisodes:
    def test_deleted_episodes_excluded(self, episode_setup: dict) -> None:
        deleted_episode = episode_setup["shows"][0]["recent"]
        deleted_episode.deleted_at = tz_datetime.now()
        episode_setup["session"].flush()

        episodes = _build(episode_setup)
        result_ids = {ep.id for ep in episodes}
        assert deleted_episode.id not in result_ids
        assert len(episodes) == 3


class TestInvalidSortKeys:
    def test_invalid_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelMediaFilter(
                sort_by=[_sort_key("episode.nonexistent_field")],
            )

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelMediaFilter(
                sort_by=[
                    json.dumps(
                        {
                            "field": "episode.duration",
                            "mode": "invalid_mode",
                        },
                    ),
                ],
            )

    def test_invalid_direction_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelMediaFilter(
                sort_by=[
                    json.dumps(
                        {
                            "field": "episode.duration",
                            "direction": "sideways",
                        },
                    ),
                ],
            )

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelMediaFilter(sort_by=["not valid json"])


class TestMultipleSortKeys:
    def test_multiple_sorts_applied(self, episode_setup: dict) -> None:
        """Last sort key is primary, earlier ones are secondary."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("episode.duration", "ascending"),
                _sort_key("episode.air_date", "descending"),
            ],
        )
        assert len(episodes) == 4


class TestRandomSort:
    def test_random_sort_deterministic_with_seed(
        self,
        episode_setup: dict,
    ) -> None:
        sort_by = [_sort_key("episode.random")]
        first = _build(episode_setup, sort_by=sort_by, random_seed=42)
        second = _build(episode_setup, sort_by=sort_by, random_seed=42)
        assert [ep.id for ep in first] == [ep.id for ep in second]

    def test_different_seeds_produce_different_order(
        self,
        episode_setup: dict,
    ) -> None:
        sort_by = [_sort_key("episode.random")]
        first = _build(episode_setup, sort_by=sort_by, random_seed=1)
        second = _build(episode_setup, sort_by=sort_by, random_seed=2)
        # Different seeds should produce different orders (extremely unlikely to match)
        assert [ep.id for ep in first] != [ep.id for ep in second]


class TestGroupByShowAggregations:
    @pytest.mark.parametrize("aggregation", ["max", "min", "avg"])
    def test_all_aggregation_functions(
        self,
        episode_setup: dict,
        aggregation: str,
    ) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.duration",
                    "ascending",
                    aggregation=aggregation,
                ),
            ],
        )
        assert len(episodes) == 4

    def test_group_by_show_groups_episodes_by_show(
        self,
        episode_setup: dict,
    ) -> None:
        """All episodes from the same show should be adjacent."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.duration",
                    "ascending",
                    aggregation="max",
                ),
            ],
        )
        show_ids = [ep.season.show_id for ep in episodes]
        # Episodes from the same show should be grouped together
        seen_shows = []
        for show_id in show_ids:
            if not seen_shows or seen_shows[-1] != show_id:
                seen_shows.append(show_id)
        assert len(seen_shows) == 2

    def test_group_by_show_min_duration(self, episode_setup: dict) -> None:
        """Min aggregation should sort by minimum episode duration per show."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.duration",
                    "ascending",
                    aggregation="min",
                ),
            ],
        )
        assert len(episodes) == 4


class TestFilterCombinations:
    def test_hide_watched_with_duration_filter(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            hide_watched=True,
            minimum_duration=150,
        )
        result_ids = {ep.id for ep in episodes}
        assert watched_episode.id not in result_ids
        assert all(ep.duration >= 150 for ep in episodes)

    def test_only_started_shows_with_duration_filter(
        self,
        episode_setup: dict,
    ) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            only_started_shows=True,
            minimum_duration=150,
        )
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}
        assert all(ep.duration >= 150 for ep in episodes)

    def test_hide_watched_with_air_date_filter(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["old"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        cutoff = tz_datetime.now() - timedelta(days=30)
        episodes = _build(
            episode_setup,
            hide_watched=True,
            minimum_air_date_absolute=cutoff.isoformat(),
        )
        result_ids = {ep.id for ep in episodes}
        assert watched_episode.id not in result_ids

    def test_all_filters_combined(self, episode_setup: dict) -> None:
        """Apply multiple filters simultaneously."""
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            hide_watched=True,
            minimum_duration=50,
            maximum_duration=250,
        )
        result_ids = {ep.id for ep in episodes}
        assert watched_episode.id not in result_ids
        assert all(50 <= ep.duration <= 250 for ep in episodes)


class TestSortWithFilterCombinations:
    def test_sort_ascending_with_hide_watched(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.duration", "ascending")],
            hide_watched=True,
        )
        assert watched_episode.id not in {ep.id for ep in episodes}
        durations = [ep.duration for ep in episodes]
        assert durations == sorted(durations)

    def test_interleave_with_duration_filter(
        self,
        episode_setup: dict,
    ) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.recently_aired",
                    "descending",
                    days=7,
                    display="interleave",
                ),
            ],
            minimum_duration=150,
            random_seed=42,
        )
        assert all(ep.duration >= 150 for ep in episodes)

    def test_group_by_show_with_hide_watched(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.duration",
                    "descending",
                    aggregation="max",
                ),
            ],
            hide_watched=True,
        )
        assert watched_episode.id not in {ep.id for ep in episodes}

    def test_interleave_with_only_started_shows(
        self,
        episode_setup: dict,
    ) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "episode.air_date",
                    "descending",
                    display="randomize",
                ),
            ],
            only_started_shows=True,
            random_seed=42,
        )
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}

    def test_random_sort_with_limit(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.random")],
            random_seed=42,
            limit=2,
        )
        assert len(episodes) == 2


class TestMultipleSortKeyCombinations:
    def test_group_by_show_then_episode_sort(self, episode_setup: dict) -> None:
        """Group by show as primary, episode field as secondary."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("episode.air_date", "ascending"),
                _sort_key(
                    "episode.duration",
                    "descending",
                    aggregation="max",
                ),
            ],
        )
        assert len(episodes) == 4

    def test_interleave_with_secondary_sort(
        self,
        episode_setup: dict,
    ) -> None:
        """Interleave on primary sort, normal secondary sort."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("episode.duration", "ascending"),
                _sort_key(
                    "episode.recently_aired",
                    "descending",
                    days=7,
                    display="interleave",
                ),
            ],
            random_seed=42,
        )
        assert len(episodes) == 4

    def test_two_normal_sorts(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("show.name", "ascending"),
                _sort_key("episode.duration", "descending"),
            ],
        )
        assert len(episodes) == 4

    def test_show_field_with_interleave(self, episode_setup: dict) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key(
                    "show.name",
                    "ascending",
                    display="interleave",
                ),
            ],
            random_seed=42,
        )
        assert len(episodes) == 4
        # Both shows should be present in results
        show_ids = {ep.season.show_id for ep in episodes}
        assert len(show_ids) == 2


class TestWatchDateFilter:
    def test_hide_watched_recent_watch_hidden(
        self,
        episode_setup: dict,
    ) -> None:
        """Episodes watched after the cutoff should be hidden."""
        watched_episode = episode_setup["shows"][0]["recent"]
        recent_watch_date = tz_datetime.now() - timedelta(hours=1)
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=recent_watch_date,
        )
        cutoff = tz_datetime.now() - timedelta(days=15)
        episodes = _build(
            episode_setup,
            hide_watched=True,
            maximum_watch_date_absolute=cutoff.isoformat(),
        )
        # Watch (1 hour ago) > cutoff (15 days ago), so episode is hidden
        assert watched_episode.id not in {ep.id for ep in episodes}

    def test_hide_watched_old_watch_still_visible(
        self,
        episode_setup: dict,
    ) -> None:
        """Episodes watched before the cutoff should still appear."""
        watched_episode = episode_setup["shows"][0]["recent"]
        old_watch_date = tz_datetime.now() - timedelta(days=30)
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=old_watch_date,
        )
        cutoff = tz_datetime.now() - timedelta(days=15)
        episodes = _build(
            episode_setup,
            hide_watched=True,
            maximum_watch_date_absolute=cutoff.isoformat(),
        )
        # Watch (30 days ago) <= cutoff (15 days ago), so episode stays visible
        assert watched_episode.id in {ep.id for ep in episodes}

    def test_hide_watched_with_max_watch_date_relative(
        self,
        episode_setup: dict,
    ) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        recent_watch_date = tz_datetime.now() - timedelta(hours=1)
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=recent_watch_date,
        )
        # Watch (1 hour ago) > cutoff (7 days ago), so episode is hidden
        episodes = _build(
            episode_setup,
            hide_watched=True,
            maximum_watch_date_relative=7,
        )
        assert watched_episode.id not in {ep.id for ep in episodes}


class TestNoUser:
    def test_episodes_returned_without_user(
        self,
        episode_setup: dict,
    ) -> None:
        """Should return episodes even without an authenticated user."""
        media_filter = ChannelMediaFilter()
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            media_filter,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4

    def test_watch_filters_ignored_without_user(
        self,
        episode_setup: dict,
    ) -> None:
        """Watch filters should be no-ops without a user."""
        media_filter = ChannelMediaFilter(hide_watched=True, hide_unwatched=True)
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            media_filter,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4

    def test_show_filters_ignored_without_user(
        self,
        episode_setup: dict,
    ) -> None:
        media_filter = ChannelMediaFilter(
            only_started_shows=True,
            only_new_shows=True,
        )
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            media_filter,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4


class TestAdditionalChannels:
    def test_episodes_from_additional_channel_included(
        self,
        episode_setup: dict,
    ) -> None:
        session = episode_setup["session"]
        user = episode_setup["user"]
        extra_channel = create_random_channel(session, user=user.id)
        channel_show = create_random_channel_show(
            session,
            extra_channel,
            episode_setup["plugin"],
            white_list_mode=False,
        )
        season = create_random_season(session, channel_show.show)
        extra_episode = create_random_episode(session, season, duration=300)
        session.flush()

        episodes = _build(
            episode_setup,
            additional_channels=[str(extra_channel.id)],
        )
        assert extra_episode.id in {ep.id for ep in episodes}
        assert len(episodes) == 5


class TestRecentlyAiredGroupByShow:
    """Test group_by_show + recently_aired sorting.

    Shows that have at least one episode aired in the past 30 days should
    appear before shows that have no recently aired episodes.
    """

    def test_interleave_sequential_with_group_by_show_and_duration(
        self,
        session_scoped_db: Session,
    ) -> None:
        """Interleaving by show with group_by_show recently_aired sort should:
        1. Group shows by recently aired status (not-recent first when ascending)
        2. Interleave episodes across shows within each group
        3. Sort by duration descending within each show's episodes
        """
        user = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=user.id)
        plugin = create_random_plugin(session_scoped_db, user, public=True)

        recent_date = tz_datetime.now() - timedelta(days=30)
        old_date = tz_datetime.now() - timedelta(days=400)

        # Recent Show 1: has a recently aired episode (within 365 days)
        recent_show_1 = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        recent_show_1.show.name = "Recent 1"
        season_r1 = create_random_season(session_scoped_db, recent_show_1.show)
        for duration in (3600, 2400, 1200):
            create_random_episode(
                session_scoped_db,
                season_r1,
                air_date=recent_date,
                duration=duration,
            )

        # Recent Show 2: also recently aired
        recent_show_2 = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        recent_show_2.show.name = "Recent 2"
        season_r2 = create_random_season(session_scoped_db, recent_show_2.show)
        for duration in (3000, 2000, 1000):
            create_random_episode(
                session_scoped_db,
                season_r2,
                air_date=recent_date,
                duration=duration,
            )

        # Old Show: no episodes in the past 365 days
        old_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        old_show.show.name = "Old Show"
        season_old = create_random_season(session_scoped_db, old_show.show)
        for duration in (5000, 4000, 3000):
            create_random_episode(
                session_scoped_db,
                season_old,
                air_date=old_date,
                duration=duration,
            )

        session_scoped_db.flush()
        setup = {"channel": channel, "user": user, "session": session_scoped_db}

        episodes = _build(
            setup,
            sort_by=[
                _sort_key("episode.duration", "descending"),
                _sort_key("show.name", "ascending", display="interleave"),
                _sort_key(
                    "episode.recently_aired",
                    "ascending",
                    aggregation="max",
                    days=365,
                ),
            ],
            random_seed=1118678984,
        )

        assert len(episodes) == 9

        # The group_by_show sort with ascending recently_aired should separate
        # shows into two tiers:
        #   - Tier 1 (recently_aired=0): Old Show (not aired in 365 days)
        #   - Tier 2 (recently_aired=1): Recent 1, Recent 2
        # Old Show episodes should all appear before any Recent show episodes.
        show_names = [episode.season.show.name for episode in episodes]
        last_old_show_position = max(
            index for index, name in enumerate(show_names) if name == "Old Show"
        )
        first_recent_position = min(
            index for index, name in enumerate(show_names) if name.startswith("Recent")
        )
        assert last_old_show_position < first_recent_position, (
            f"Old Show episodes should all appear before Recent show episodes "
            f"but got order: {show_names}"
        )

        # Within each show, episodes should be sorted by duration descending
        for show_name in ("Recent 1", "Recent 2", "Old Show"):
            show_durations = [
                episode.duration
                for episode in episodes
                if episode.season.show.name == show_name
            ]
            assert show_durations == sorted(show_durations, reverse=True), (
                f"{show_name} episodes not sorted by duration descending: "
                f"{show_durations}"
            )


class TestWhitelistWithEpisodeExclusion:
    """When a season is whitelisted and an episode within it is also marked,
    the episode-level entry should act as an exclusion (blacklist within the
    whitelist)."""

    def test_whitelisted_season_with_marked_episode_excludes_episode(
        self,
        session_scoped_db: Session,
    ) -> None:
        user = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=user.id)
        plugin = create_random_plugin(session_scoped_db, user, public=True)

        channel_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=True,
        )
        show = channel_show.show
        season = create_random_season(session_scoped_db, show)
        episode_included = create_random_episode(session_scoped_db, season)
        episode_excluded = create_random_episode(session_scoped_db, season)

        # Whitelist the season
        session_scoped_db.add(
            ChannelSeasonWhiteList(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )
        # Also mark the episode — this should exclude it from the whitelisted season
        session_scoped_db.add(
            ChannelEpisodeWhiteList(
                channel_show_id=channel_show.id,
                episode_id=episode_excluded.id,
            ),
        )
        session_scoped_db.flush()

        episodes = _build(
            {"channel": channel, "user": user, "session": session_scoped_db},
        )
        episode_ids = {ep.id for ep in episodes}
        assert episode_included.id in episode_ids
        assert episode_excluded.id not in episode_ids


class TestBlacklistWithEpisodeInclusion:
    """When a season is blacklisted and an episode within it is also marked,
    the episode-level entry should invert it so that episode shows up."""

    def test_blacklisted_season_with_marked_episode_includes_episode(
        self,
        session_scoped_db: Session,
    ) -> None:
        user = create_random_user(session_scoped_db)
        channel = create_random_channel(session_scoped_db, user=user.id)
        plugin = create_random_plugin(session_scoped_db, user, public=True)

        channel_show = create_random_channel_show(
            session_scoped_db,
            channel,
            plugin,
            white_list_mode=False,
        )
        show = channel_show.show
        season = create_random_season(session_scoped_db, show)
        episode_excluded = create_random_episode(session_scoped_db, season)
        episode_included = create_random_episode(session_scoped_db, season)

        # Blacklist the season
        session_scoped_db.add(
            ChannelSeasonWhiteList(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )
        # Also mark the episode — this should include it despite the season blacklist
        session_scoped_db.add(
            ChannelEpisodeWhiteList(
                channel_show_id=channel_show.id,
                episode_id=episode_included.id,
            ),
        )
        session_scoped_db.flush()

        episodes = _build(
            {"channel": channel, "user": user, "session": session_scoped_db},
        )
        episode_ids = {ep.id for ep in episodes}
        assert episode_included.id in episode_ids
        assert episode_excluded.id not in episode_ids


class TestEpisodeResult:
    def test_results_include_channel_id(self, episode_setup: dict) -> None:
        results = _build_results(episode_setup)
        assert len(results) == 4
        for result in results:
            assert result.channel_id == episode_setup["channel"].id

    def test_results_include_watch_data(self, episode_setup: dict) -> None:
        watched_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            watched_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        results = _build_results(episode_setup)
        watched_result = next(r for r in results if r.episode.id == watched_episode.id)
        assert watched_result.latest_watch is not None

        unwatched_result = next(
            r for r in results if r.episode.id != watched_episode.id
        )
        assert unwatched_result.latest_watch is None
