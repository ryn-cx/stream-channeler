import uuid

import pytest
from sqlmodel import Session, select

from app.channels.models import (
    ChannelEpisodeWhiteList,
    ChannelSeasonWhiteList,
)
from app.plugins.plugins.StreamChanneler import StreamChanneler
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError
from app.tools.import_queue import add_results_to_channel
from tests.channels.utils import create_random_channel
from tests.episodes.utils import create_random_episode
from tests.plugins.utils import create_random_plugin
from tests.seasons.utils import create_random_season
from tests.shows.utils import create_random_show
from tests.sources.utils import create_random_source


class TestStreamChannelerURLValidation:
    @pytest.mark.parametrize(
        "url",
        [
            "streamchanneler.com/show/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/season/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/episode/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/source/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/plugin/00000000-0000-0000-0000-000000000000/",
            "localhost/show/00000000-0000-0000-0000-000000000000/",
            "localhost/episode/00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_valid_url_format(self, url: str) -> None:
        assert StreamChanneler.is_valid_url_format(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "example.com/show/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/invalid/00000000-0000-0000-0000-000000000000/",
            "streamchanneler.com/show/not-a-uuid/",
            "streamchanneler.com/show/",
        ],
    )
    def test_invalid_url_format(self, url: str) -> None:
        assert StreamChanneler.is_valid_url_format(url) is False


class TestImportShow:
    def test_import_show(self, function_scoped_db: Session) -> None:
        show = create_random_show(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show.id == show.id
        assert results[0].whitelist_mode is False
        assert results[0].seasons == []
        assert results[0].episodes == []

    def test_import_nonexistent_show(self, function_scoped_db: Session) -> None:
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/show/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


class TestImportSeason:
    def test_import_season(self, function_scoped_db: Session) -> None:
        season = create_random_season(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/season/{season.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show.id == season.show_id
        assert results[0].whitelist_mode is True
        assert len(results[0].seasons) == 1
        assert results[0].seasons[0].id == season.id
        assert results[0].episodes == []

    def test_import_nonexistent_season(self, function_scoped_db: Session) -> None:
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/season/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


class TestImportEpisode:
    def test_import_episode(self, function_scoped_db: Session) -> None:
        episode = create_random_episode(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/episode/{episode.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show.id == episode.season.show_id
        assert results[0].whitelist_mode is True
        assert results[0].seasons == []
        assert len(results[0].episodes) == 1
        assert results[0].episodes[0].id == episode.id

    def test_import_nonexistent_episode(self, function_scoped_db: Session) -> None:
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/episode/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


class TestImportSource:
    def test_import_source(self, function_scoped_db: Session) -> None:
        source = create_random_source(function_scoped_db)
        show_one = create_random_show(function_scoped_db, parent=source)
        show_two = create_random_show(function_scoped_db, parent=source)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/source/{source.id}/"

        results = plugin.import_url(url)

        result_show_ids = {result.show.id for result in results}
        assert len(results) == 2
        assert show_one.id in result_show_ids
        assert show_two.id in result_show_ids
        assert all(result.whitelist_mode is False for result in results)

    def test_import_nonexistent_source(self, function_scoped_db: Session) -> None:
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/source/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


class TestImportPlugin:
    def test_import_plugin(self, function_scoped_db: Session) -> None:
        db_plugin = create_random_plugin(function_scoped_db)
        source_one = create_random_source(function_scoped_db, parent=db_plugin)
        source_two = create_random_source(function_scoped_db, parent=db_plugin)
        show_one = create_random_show(function_scoped_db, parent=source_one)
        show_two = create_random_show(function_scoped_db, parent=source_two)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/plugin/{db_plugin.id}/"

        results = plugin.import_url(url)

        result_show_ids = {result.show.id for result in results}
        assert len(results) == 2
        assert show_one.id in result_show_ids
        assert show_two.id in result_show_ids
        assert all(result.whitelist_mode is False for result in results)

    def test_import_nonexistent_plugin(self, function_scoped_db: Session) -> None:
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/plugin/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


class TestAddResultsToChannel:
    def test_import_show_adds_to_channel(self, function_scoped_db: Session) -> None:
        show = create_random_show(function_scoped_db)
        channel = create_random_channel(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        assert len(channel.shows) == 1
        assert channel.shows[0].show_id == show.id
        assert channel.shows[0].white_list_mode is False

    def test_import_season_adds_to_channel_with_whitelist(
        self,
        function_scoped_db: Session,
    ) -> None:
        season = create_random_season(function_scoped_db)
        channel = create_random_channel(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/season/{season.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        assert len(channel.shows) == 1
        channel_show = channel.shows[0]
        assert channel_show.show_id == season.show_id
        assert channel_show.white_list_mode is True

        season_whitelist = function_scoped_db.exec(
            select(ChannelSeasonWhiteList).where(
                ChannelSeasonWhiteList.channel_show_id == channel_show.id,
            ),
        ).all()
        assert len(season_whitelist) == 1
        assert season_whitelist[0].season_id == season.id

    def test_import_episode_adds_to_channel_with_whitelist(
        self,
        function_scoped_db: Session,
    ) -> None:
        episode = create_random_episode(function_scoped_db)
        channel = create_random_channel(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/episode/{episode.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        assert len(channel.shows) == 1
        channel_show = channel.shows[0]
        assert channel_show.show_id == episode.season.show_id
        assert channel_show.white_list_mode is True

        episode_whitelist = function_scoped_db.exec(
            select(ChannelEpisodeWhiteList).where(
                ChannelEpisodeWhiteList.channel_show_id == channel_show.id,
            ),
        ).all()
        assert len(episode_whitelist) == 1
        assert episode_whitelist[0].episode_id == episode.id

    def test_import_multiple_shows_from_source(
        self,
        function_scoped_db: Session,
    ) -> None:
        source = create_random_source(function_scoped_db)
        show_one = create_random_show(function_scoped_db, parent=source)
        show_two = create_random_show(function_scoped_db, parent=source)
        channel = create_random_channel(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/source/{source.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        channel_show_ids = {channel_show.show_id for channel_show in channel.shows}
        assert len(channel.shows) == 2
        assert show_one.id in channel_show_ids
        assert show_two.id in channel_show_ids

    def test_import_show_already_in_channel(
        self,
        function_scoped_db: Session,
    ) -> None:
        show = create_random_show(function_scoped_db)
        channel = create_random_channel(function_scoped_db)
        plugin = StreamChanneler(function_scoped_db)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        # Import the same show again
        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_db, results, channel)
        function_scoped_db.flush()

        assert len(channel.shows) == 1
