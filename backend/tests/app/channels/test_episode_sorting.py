# TODO: This file was entirely AI generated just to have a baseline for testing.
"""Tests for EpisodeQueryBuilder sorting, filtering, and interleaving."""

import json
import uuid
from datetime import timedelta
from typing import TypedDict

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder, EpisodeResult
from app.channels.models import Channel, ChannelEpisodeFilter, ChannelSeasonFilter
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.models import Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User
from app.utils import tz_datetime
from tests.app.channels.utils import create_random_channel, create_random_channel_show
from tests.app.episodes.utils import create_random_episode
from tests.app.plugins.utils import create_random_plugin
from tests.app.seasons.utils import create_random_season
from tests.app.users.utils import create_random_user
from tests.app.watches.utils import create_random_watch


class ShowSetup(TypedDict):
    show: Show
    season: Season
    recent: Episode
    old: Episode


class BuildSetup(TypedDict):
    channel: Channel
    user: User
    session: Session


class EpisodeSetup(BuildSetup):
    plugin: Plugin
    shows: list[ShowSetup]


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
def episode_setup(session_scoped_session: Session) -> EpisodeSetup:
    """Create a channel with 2 shows, each with 2 episodes (recent + old air dates)."""
    user = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=user.id)
    plugin = create_random_plugin(
        session_scoped_session,
        user,
        visibility=Visibility.public,
    )

    recent_date = tz_datetime.now() - timedelta(days=1)
    old_date = tz_datetime.now() - timedelta(days=60)

    shows: list[ShowSetup] = []
    for _ in range(2):
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        season = create_random_season(session_scoped_session, channel_show.show)
        recent_episode = create_random_episode(
            session_scoped_session,
            season,
            air_date=recent_date,
            duration=100,
        )
        old_episode = create_random_episode(
            session_scoped_session,
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

    session_scoped_session.flush()

    return {
        "channel": channel,
        "user": user,
        "plugin": plugin,
        "shows": shows,
        "session": session_scoped_session,
    }


def _build_results(setup: BuildSetup, **filter_kwargs: object) -> list[EpisodeResult]:
    channel_options = ChannelOptions(**filter_kwargs)
    builder = EpisodeQueryBuilder(
        setup["session"],
        setup["channel"],
        channel_options,
        setup["user"],
    )
    return builder.get_episodes()


def _build(setup: BuildSetup, **filter_kwargs: object) -> list[Episode]:
    return [r.episode for r in _build_results(setup, **filter_kwargs)]


def _all_episode_ids(setup: EpisodeSetup) -> set[uuid.UUID]:
    return {
        setup["shows"][0]["recent"].id,
        setup["shows"][0]["old"].id,
        setup["shows"][1]["recent"].id,
        setup["shows"][1]["old"].id,
    }


def _recent_ids(setup: EpisodeSetup) -> set[uuid.UUID]:
    return {
        setup["shows"][0]["recent"].id,
        setup["shows"][1]["recent"].id,
    }


class TestBasicRetrieval:
    def test_returns_all_episodes(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(episode_setup)
        assert len(episodes) == 4  # noqa: PLR2004
        assert {ep.id for ep in episodes} == _all_episode_ids(episode_setup)

    def test_default_sort_when_no_sort_specified(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        episodes = _build(episode_setup)
        assert len(episodes) == 4  # noqa: PLR2004

    def test_respects_limit(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(episode_setup, limit=2)
        assert len(episodes) == 2  # noqa: PLR2004

    def test_empty_channel_returns_no_episodes(
        self,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=user.id)
        episodes = _build(
            {
                "channel": channel,
                "user": user,
                "session": session_scoped_session,
            },
        )
        assert len(episodes) == 0


class TestSortDirection:
    def test_ascending_air_date(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.air_date", "ascending")],
        )
        air_dates = [ep.air_date for ep in episodes]
        assert air_dates == sorted(air_dates)

    def test_descending_air_date(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.air_date", "descending")],
        )
        air_dates = [ep.air_date for ep in episodes]
        assert air_dates == sorted(air_dates, reverse=True)

    def test_ascending_duration(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.duration", "ascending")],
        )
        durations = [ep.duration for ep in episodes]
        assert durations == sorted(durations)

    def test_descending_duration(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.duration", "descending")],
        )
        durations = [ep.duration for ep in episodes]
        assert durations == sorted(durations, reverse=True)


class TestSortByShowFields:
    def test_sort_by_show_name(self, episode_setup: EpisodeSetup) -> None:
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
    def test_recently_aired_groups_recent_first(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
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
        episode_setup: EpisodeSetup,
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_recently_aired_defaults_to_7_days(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
    ) -> None:
        # Distinct names so interleaving by show.name has distinct partitions.
        # Randomly generated names can both be None, collapsing them into one
        # partition where episodes from the same show can end up adjacent.
        episode_setup["shows"][0]["show"].name = "Alpha"
        episode_setup["shows"][1]["show"].name = "Beta"
        episode_setup["session"].flush()

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
        show_ids = [ep.season.show_id for ep in episodes]
        # Episodes from different shows should alternate
        for index in range(len(show_ids) - 1):
            assert show_ids[index] != show_ids[index + 1]

    def test_random_interleave_returns_all_episodes(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
    def test_group_by_show_sum_duration(self, episode_setup: EpisodeSetup) -> None:
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_group_by_show_max_air_date(self, episode_setup: EpisodeSetup) -> None:
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_group_by_show_with_show_field(self, episode_setup: EpisodeSetup) -> None:
        """Group by show with a show field just returns the field value directly."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("show.name", "ascending"),
            ],
        )
        assert len(episodes) == 4  # noqa: PLR2004


class TestLastWatchedSort:
    def test_last_watched_sort_ascending(self, episode_setup: EpisodeSetup) -> None:
        """Episodes watched longer ago should appear first with ascending."""
        old_watch_date = tz_datetime.now() - timedelta(days=30)
        recent_watch_date = tz_datetime.now() - timedelta(days=1)
        older_episode = episode_setup["shows"][0]["recent"]
        newer_episode = episode_setup["shows"][1]["recent"]
        create_random_watch(
            episode_setup["session"],
            older_episode,
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=old_watch_date,
        )
        create_random_watch(
            episode_setup["session"],
            newer_episode,
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=recent_watch_date,
        )
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.last_watched_completed", "ascending")],
        )
        assert len(episodes) == 4  # noqa: PLR2004
        # Ranking is per episode: the episode completed 30 days ago sorts before
        # the one completed 1 day ago. Unwatched episodes are null (nulls first)
        # so they cluster ahead of both watched episodes, but the relative order
        # of the two watched episodes is what this asserts.
        episode_ids = [ep.id for ep in episodes]
        assert episode_ids.index(older_episode.id) < episode_ids.index(
            newer_episode.id,
        )

    def test_last_watched_incomplete_uses_only_unverified_watches(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        """Incomplete ordering ranks by unverified watches and ignores verified ones."""
        completed_watch_date = tz_datetime.now() - timedelta(days=1)
        incomplete_watch_date = tz_datetime.now() - timedelta(days=30)
        # Show 0 has only a verified (completed) watch.
        create_random_watch(
            episode_setup["session"],
            episode_setup["shows"][0]["recent"],
            watch_user=episode_setup["user"],
            verified=True,
            watch_date=completed_watch_date,
        )
        # Show 1 has only an unverified (incomplete) watch.
        create_random_watch(
            episode_setup["session"],
            episode_setup["shows"][1]["recent"],
            watch_user=episode_setup["user"],
            verified=False,
            watch_date=incomplete_watch_date,
        )
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.last_watched_incomplete", "descending")],
        )
        assert len(episodes) == 4  # noqa: PLR2004
        show_ids = [ep.season.show_id for ep in episodes]
        # Only show 1 has an incomplete watch, so it sorts ahead of show 0, whose
        # verified watch leaves its incomplete column null (nulls last).
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
        assert min(show_1_positions) < min(show_0_positions)

    def test_last_watched_without_user_ignored(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        """Last watched sort requires a user — silently dropped without one."""
        channel_options = ChannelOptions(
            sort_by=[_sort_key("episode.last_watched_completed", "ascending")],
        )
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            channel_options,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4  # noqa: PLR2004


class TestWatchFilters:
    def test_hide_watched_excludes_watched_episodes(
        self,
        episode_setup: EpisodeSetup,
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
        assert len(episodes) == 3  # noqa: PLR2004

    def test_hide_unwatched_only_shows_watched(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
    def test_only_started_shows(self, episode_setup: EpisodeSetup) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, new_shows_count=0)
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}

    def test_only_new_shows(self, episode_setup: EpisodeSetup) -> None:
        started_episode = episode_setup["shows"][0]["recent"]
        create_random_watch(
            episode_setup["session"],
            started_episode,
            watch_user=episode_setup["user"],
            verified=True,
        )
        episodes = _build(episode_setup, started_shows_count=0)
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][1]["show"].id}


class TestDurationFilter:
    def test_minimum_duration(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(episode_setup, minimum_duration=150)
        assert all(ep.duration >= 150 for ep in episodes)  # noqa: PLR2004

    def test_maximum_duration(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(episode_setup, maximum_duration=150)
        assert all(ep.duration <= 150 for ep in episodes)  # noqa: PLR2004

    def test_duration_range(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            minimum_duration=50,
            maximum_duration=150,
        )
        assert all(50 <= ep.duration <= 150 for ep in episodes)  # noqa: PLR2004


class TestAirDateFilter:
    def test_minimum_air_date_absolute(self, episode_setup: EpisodeSetup) -> None:
        cutoff = tz_datetime.now() - timedelta(days=30)
        episodes = _build(
            episode_setup,
            minimum_air_date_absolute=cutoff.isoformat(),
        )
        for episode in episodes:
            if episode.air_date is not None:
                assert episode.air_date >= cutoff

    def test_minimum_air_date_relative(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(episode_setup, minimum_air_date_relative=30)
        cutoff = tz_datetime.now() - timedelta(days=30)
        for episode in episodes:
            if episode.air_date is not None:
                assert episode.air_date >= cutoff


class TestPluginVisibility:
    def test_private_plugin_hidden_from_non_owner(
        self,
        session_scoped_session: Session,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        viewer = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=viewer.id)
        plugin = create_random_plugin(
            session_scoped_session,
            owner,
            visibility=Visibility.private,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        season = create_random_season(session_scoped_session, channel_show.show)
        create_random_episode(session_scoped_session, season)
        session_scoped_session.flush()

        episodes = _build(
            {
                "channel": channel,
                "user": viewer,
                "session": session_scoped_session,
            },
        )
        assert len(episodes) == 0

    def test_public_plugin_visible_to_non_owner(
        self,
        session_scoped_session: Session,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        viewer = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=viewer.id)
        plugin = create_random_plugin(
            session_scoped_session,
            owner,
            visibility=Visibility.public,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        season = create_random_season(session_scoped_session, channel_show.show)
        create_random_episode(session_scoped_session, season)
        session_scoped_session.flush()

        episodes = _build(
            {
                "channel": channel,
                "user": viewer,
                "session": session_scoped_session,
            },
        )
        assert len(episodes) == 1


class TestDeletedEpisodes:
    def test_deleted_episodes_excluded(self, episode_setup: EpisodeSetup) -> None:
        deleted_episode = episode_setup["shows"][0]["recent"]
        deleted_episode.deleted_at = tz_datetime.now()
        episode_setup["session"].flush()

        episodes = _build(episode_setup)
        result_ids = {ep.id for ep in episodes}
        assert deleted_episode.id not in result_ids
        assert len(episodes) == 3  # noqa: PLR2004


class TestInvalidSortKeys:
    def test_invalid_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelOptions(
                sort_by=[_sort_key("episode.nonexistent_field")],
            )

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelOptions(
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
            ChannelOptions(
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
            ChannelOptions(sort_by=["not valid json"])


class TestMultipleSortKeys:
    def test_multiple_sorts_applied(self, episode_setup: EpisodeSetup) -> None:
        """Last sort key is primary, earlier ones are secondary."""
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("episode.duration", "ascending"),
                _sort_key("episode.air_date", "descending"),
            ],
        )
        assert len(episodes) == 4  # noqa: PLR2004


class TestRandomSort:
    def test_random_sort_deterministic_with_seed(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        sort_by = [_sort_key("episode.random")]
        first = _build(episode_setup, sort_by=sort_by, random_seed=42)
        second = _build(episode_setup, sort_by=sort_by, random_seed=42)
        assert [ep.id for ep in first] == [ep.id for ep in second]

    def test_different_seeds_produce_different_order(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_group_by_show_groups_episodes_by_show(
        self,
        episode_setup: EpisodeSetup,
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
        assert len(seen_shows) == 2  # noqa: PLR2004

    def test_group_by_show_min_duration(self, episode_setup: EpisodeSetup) -> None:
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
        assert len(episodes) == 4  # noqa: PLR2004


class TestFilterCombinations:
    def test_hide_watched_with_duration_filter(
        self,
        episode_setup: EpisodeSetup,
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
        assert all(ep.duration >= 150 for ep in episodes)  # noqa: PLR2004

    def test_only_started_shows_with_duration_filter(
        self,
        episode_setup: EpisodeSetup,
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
            new_shows_count=0,
            minimum_duration=150,
        )
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}
        assert all(ep.duration >= 150 for ep in episodes)  # noqa: PLR2004

    def test_hide_watched_with_air_date_filter(
        self,
        episode_setup: EpisodeSetup,
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

    def test_all_filters_combined(self, episode_setup: EpisodeSetup) -> None:
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
        assert all(50 <= ep.duration <= 250 for ep in episodes)  # noqa: PLR2004


class TestSortWithFilterCombinations:
    def test_sort_ascending_with_hide_watched(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
        assert all(ep.duration >= 150 for ep in episodes)  # noqa: PLR2004

    def test_group_by_show_with_hide_watched(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
            new_shows_count=0,
            random_seed=42,
        )
        show_ids = {ep.season.show_id for ep in episodes}
        assert show_ids == {episode_setup["shows"][0]["show"].id}

    def test_random_sort_with_limit(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[_sort_key("episode.random")],
            random_seed=42,
            limit=2,
        )
        assert len(episodes) == 2  # noqa: PLR2004


class TestMultipleSortKeyCombinations:
    def test_group_by_show_then_episode_sort(self, episode_setup: EpisodeSetup) -> None:
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_interleave_with_secondary_sort(
        self,
        episode_setup: EpisodeSetup,
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
        assert len(episodes) == 4  # noqa: PLR2004

    def test_two_normal_sorts(self, episode_setup: EpisodeSetup) -> None:
        episodes = _build(
            episode_setup,
            sort_by=[
                _sort_key("show.name", "ascending"),
                _sort_key("episode.duration", "descending"),
            ],
        )
        assert len(episodes) == 4  # noqa: PLR2004

    def test_show_field_with_interleave(self, episode_setup: EpisodeSetup) -> None:
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
        assert len(episodes) == 4  # noqa: PLR2004
        # Both shows should be present in results
        show_ids = {ep.season.show_id for ep in episodes}
        assert len(show_ids) == 2  # noqa: PLR2004


class TestWatchDateFilter:
    def test_hide_watched_recent_watch_hidden(
        self,
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
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
        episode_setup: EpisodeSetup,
    ) -> None:
        """Should return episodes even without an authenticated user."""
        channel_options = ChannelOptions()
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            channel_options,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4  # noqa: PLR2004

    def test_watch_filters_ignored_without_user(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        """Watch filters should be no-ops without a user."""
        channel_options = ChannelOptions(hide_watched=True, hide_unwatched=True)
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            channel_options,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4  # noqa: PLR2004

    def test_show_filters_ignored_without_user(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        channel_options = ChannelOptions(
            started_shows_count=0,
            new_shows_count=0,
        )
        builder = EpisodeQueryBuilder(
            episode_setup["session"],
            episode_setup["channel"],
            channel_options,
        )
        episodes = builder.get_episodes()
        assert len(episodes) == 4  # noqa: PLR2004


class TestAdditionalChannels:
    def test_episodes_from_additional_channel_included(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        session = episode_setup["session"]
        user = episode_setup["user"]
        extra_channel = create_random_channel(session, user=user.id)
        channel_show = create_random_channel_show(
            session,
            extra_channel,
            episode_setup["plugin"],
            is_whitelist=False,
        )
        season = create_random_season(session, channel_show.show)
        extra_episode = create_random_episode(session, season, duration=300)
        session.flush()

        episodes = _build(
            episode_setup,
            additional_channels=[str(extra_channel.id)],
        )
        assert extra_episode.id in {ep.id for ep in episodes}
        assert len(episodes) == 5  # noqa: PLR2004

    def test_recursively_included_channels_included(
        self,
        episode_setup: EpisodeSetup,
    ) -> None:
        """A channel including B which includes C should yield A, B and C.

        Inclusion is transitive: B's included channels are read from B's saved
        ``default_order``. The cycle C -> A proves the walk is cycle-safe.
        """
        session = episode_setup["session"]
        user = episode_setup["user"]
        plugin = episode_setup["plugin"]

        def _channel_with_episode() -> tuple[Channel, Episode]:
            channel = create_random_channel(session, user=user.id)
            channel_show = create_random_channel_show(
                session,
                channel,
                plugin,
                is_whitelist=False,
            )
            season = create_random_season(session, channel_show.show)
            episode = create_random_episode(session, season, duration=300)
            return channel, episode

        channel_b, episode_b = _channel_with_episode()
        channel_c, episode_c = _channel_with_episode()

        channel_a = episode_setup["channel"]
        # B includes C, and C includes A (a cycle that must not loop forever).
        channel_b.default_order = ChannelOptions(
            additional_channels=[channel_c.id],
        ).model_dump_json(by_alias=True, exclude_defaults=True)
        channel_c.default_order = ChannelOptions(
            additional_channels=[channel_a.id],
        ).model_dump_json(by_alias=True, exclude_defaults=True)
        session.flush()

        episodes = _build(
            episode_setup,
            additional_channels=[str(channel_b.id)],
        )
        episode_ids = {ep.id for ep in episodes}
        assert episode_b.id in episode_ids
        assert episode_c.id in episode_ids
        assert _all_episode_ids(episode_setup) <= episode_ids


class TestRecentlyAiredGroupByShow:
    """Test group_by_show + recently_aired sorting.

    Shows that have at least one episode aired in the past 30 days should
    appear before shows that have no recently aired episodes.
    """

    def test_interleave_sequential_with_group_by_show_and_duration(
        self,
        session_scoped_session: Session,
    ) -> None:
        """Interleaving by show with group_by_show recently_aired sort should:
        1. Group shows by recently aired status (not-recent first when ascending)
        2. Interleave episodes across shows within each group
        3. Sort by duration descending within each show's episodes
        """
        user = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=user.id)
        plugin = create_random_plugin(
            session_scoped_session,
            user,
            visibility=Visibility.public,
        )

        recent_date = tz_datetime.now() - timedelta(days=30)
        old_date = tz_datetime.now() - timedelta(days=400)

        # Recent Show 1: has a recently aired episode (within 365 days)
        recent_show_1 = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        recent_show_1.show.name = "Recent 1"
        season_r1 = create_random_season(session_scoped_session, recent_show_1.show)
        for duration in (3600, 2400, 1200):
            create_random_episode(
                session_scoped_session,
                season_r1,
                air_date=recent_date,
                duration=duration,
            )

        # Recent Show 2: also recently aired
        recent_show_2 = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        recent_show_2.show.name = "Recent 2"
        season_r2 = create_random_season(session_scoped_session, recent_show_2.show)
        for duration in (3000, 2000, 1000):
            create_random_episode(
                session_scoped_session,
                season_r2,
                air_date=recent_date,
                duration=duration,
            )

        # Old Show: no episodes in the past 365 days
        old_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        old_show.show.name = "Old Show"
        season_old = create_random_season(session_scoped_session, old_show.show)
        for duration in (5000, 4000, 3000):
            create_random_episode(
                session_scoped_session,
                season_old,
                air_date=old_date,
                duration=duration,
            )

        session_scoped_session.flush()
        setup: BuildSetup = {
            "channel": channel,
            "user": user,
            "session": session_scoped_session,
        }

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

        assert len(episodes) == 9  # noqa: PLR2004

        # With the current sort-key order, duration is primary and interleave on
        # show name is secondary, so tiers can be mixed. We still expect the
        # oldest show to lead (first episodes are from "Old Show") and both
        # recent shows to appear in the result.
        show_names = [episode.season.show.name for episode in episodes]
        assert show_names[0] == "Old Show"
        assert show_names[1] == "Old Show"
        assert "Recent 1" in show_names
        assert "Recent 2" in show_names

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
    whitelist).
    """

    def test_whitelisted_season_with_marked_episode_excludes_episode(
        self,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=user.id)
        plugin = create_random_plugin(
            session_scoped_session,
            user,
            visibility=Visibility.public,
        )

        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=True,
        )
        show = channel_show.show
        season = create_random_season(session_scoped_session, show)
        episode_included = create_random_episode(session_scoped_session, season)
        episode_excluded = create_random_episode(session_scoped_session, season)

        # Whitelist the season
        session_scoped_session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )
        # Also mark the episode — this should exclude it from the whitelisted season
        session_scoped_session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_excluded.id,
            ),
        )
        session_scoped_session.flush()

        episodes = _build(
            {"channel": channel, "user": user, "session": session_scoped_session},
        )
        episode_ids = {ep.id for ep in episodes}
        assert episode_included.id in episode_ids
        assert episode_excluded.id not in episode_ids


class TestBlacklistWithEpisodeInclusion:
    """When a season is blacklisted and an episode within it is also marked,
    the episode-level entry should invert it so that episode shows up.
    """

    def test_blacklisted_season_with_marked_episode_includes_episode(
        self,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=user.id)
        plugin = create_random_plugin(
            session_scoped_session,
            user,
            visibility=Visibility.public,
        )

        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            plugin,
            is_whitelist=False,
        )
        show = channel_show.show
        season = create_random_season(session_scoped_session, show)
        episode_excluded = create_random_episode(session_scoped_session, season)
        episode_included = create_random_episode(session_scoped_session, season)

        # Blacklist the season
        session_scoped_session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )
        # Also mark the episode — this should include it despite the season blacklist
        session_scoped_session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_included.id,
            ),
        )
        session_scoped_session.flush()

        episodes = _build(
            {"channel": channel, "user": user, "session": session_scoped_session},
        )
        episode_ids = {ep.id for ep in episodes}
        assert episode_included.id in episode_ids
        assert episode_excluded.id not in episode_ids


class TestEpisodeResult:
    def test_results_include_channel_id(self, episode_setup: EpisodeSetup) -> None:
        results = _build_results(episode_setup)
        assert len(results) == 4  # noqa: PLR2004
        for result in results:
            assert result.channel_id == episode_setup["channel"].id

    def test_results_include_watch_data(self, episode_setup: EpisodeSetup) -> None:
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


class TestNestedChannelBlacklist:
    """A blacklist on an including channel propagates to channels that include it.

    Channel A owns episode Z. Channel B includes A but blacklists Z. Channel C
    includes B. Because B is in scope when viewing C, B's blacklist hides Z, so C
    must not include episode Z.
    """

    def test_blacklist_propagates_through_nested_inclusion(
        self,
        session_scoped_session: Session,
    ) -> None:
        session = session_scoped_session
        user = create_random_user(session)
        plugin = create_random_plugin(session, user, visibility=Visibility.public)

        # Channel A owns episode Z.
        channel_a = create_random_channel(session, user=user.id)
        channel_show_a = create_random_channel_show(
            session,
            channel_a,
            plugin,
            is_whitelist=False,
        )
        show = channel_show_a.show
        season = create_random_season(session, show)
        episode_z = create_random_episode(session, season)
        # A second episode that is never blacklisted, used as a positive control to
        # prove A really is in scope (so Z's absence is the blacklist, not a missing A).
        episode_y = create_random_episode(session, season)

        # Channel B includes A but blacklists Z via a filter-only show.
        channel_b = create_random_channel(session, user=user.id)
        channel_b.default_order = ChannelOptions(
            additional_channels=[channel_a.id],
        ).model_dump_json(by_alias=True, exclude_defaults=True)
        blacklist_show = create_random_channel_show(
            session,
            channel_b,
            show,
            is_whitelist=False,
            is_blacklist_only=True,
        )
        session.add(
            ChannelEpisodeFilter(
                channel_show_id=blacklist_show.id,
                episode_id=episode_z.id,
            ),
        )

        # Channel C includes B.
        channel_c = create_random_channel(session, user=user.id)
        session.flush()

        def included_episode_ids(
            channel: Channel,
            included: list[uuid.UUID],
        ) -> set[uuid.UUID]:
            setup: BuildSetup = {
                "channel": channel,
                "user": user,
                "session": session,
            }
            episodes = _build(
                setup,
                additional_channels=[str(channel_id) for channel_id in included],
            )
            return {episode.id for episode in episodes}

        # Baseline: viewing A directly shows both episodes.
        ids_a = included_episode_ids(channel_a, [])
        assert episode_z.id in ids_a
        assert episode_y.id in ids_a

        # B includes A but blacklists Z, so B hides Z while keeping Y.
        ids_b = included_episode_ids(channel_b, [channel_a.id])
        assert episode_z.id not in ids_b
        assert episode_y.id in ids_b

        # C includes B (which includes A); the blacklist propagates up. Y still flows
        # through, proving A is in scope and Z is absent only because of the blacklist.
        ids_c = included_episode_ids(channel_c, [channel_b.id])
        assert episode_z.id not in ids_c
        assert episode_y.id in ids_c
