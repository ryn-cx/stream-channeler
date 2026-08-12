# TODO: Validate
import uuid

import pytest
from sqlmodel import Session, select

from app.channels.models import (
    ChannelEpisodeFilter,
    ChannelSeasonFilter,
)
from app.tools.import_queue import add_results_to_channel
from plugins.StreamChanneler import StreamChanneler
from plugins.utils.abstract_plugin import InvalidURLError
from tests.old_mess.app.channels.utils import create_random_channel
from tests.old_mess.app.episodes.utils import create_random_episode
from tests.old_mess.app.plugins.utils import create_random_plugin
from tests.old_mess.app.seasons.utils import create_random_season
from tests.old_mess.app.shows.utils import create_random_show
from tests.old_mess.app.sources.utils import create_random_source


# TODO: Validate
class TestStreamChannelerURLValidation:
    # TODO: Validate
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

    # TODO: Validate
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


# TODO: Validate
class TestImportShow:
    # TODO: Validate
    def test_import_show(self, function_scoped_session: Session) -> None:
        show = create_random_show(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show_identifier == show.show_identifier
        assert results[0].is_whitelist is False
        assert results[0].season_identifiers == []
        assert results[0].episode_identifiers == []

    # TODO: Validate
    def test_import_nonexistent_show(self, function_scoped_session: Session) -> None:
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/show/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


# TODO: Validate
class TestImportSeason:
    # TODO: Validate
    def test_import_season(self, function_scoped_session: Session) -> None:
        season = create_random_season(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/season/{season.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show_identifier == season.show.show_identifier
        assert results[0].is_whitelist is True
        assert results[0].season_identifiers == [season.season_identifier]
        assert results[0].episode_identifiers == []

    # TODO: Validate
    def test_import_nonexistent_season(self, function_scoped_session: Session) -> None:
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/season/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


# TODO: Validate
class TestImportEpisode:
    # TODO: Validate
    def test_import_episode(self, function_scoped_session: Session) -> None:
        episode = create_random_episode(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/episode/{episode.id}/"

        results = plugin.import_url(url)

        assert len(results) == 1
        assert results[0].show_identifier == episode.season.show.show_identifier
        assert results[0].is_whitelist is True
        assert results[0].season_identifiers == []
        assert results[0].episode_identifiers == [episode.episode_identifier]

    # TODO: Validate
    def test_import_nonexistent_episode(self, function_scoped_session: Session) -> None:
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/episode/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


# TODO: Validate
class TestImportSource:
    # TODO: Validate
    def test_import_source(self, function_scoped_session: Session) -> None:
        source = create_random_source(function_scoped_session)
        show_one = create_random_show(function_scoped_session, parent=source)
        show_two = create_random_show(function_scoped_session, parent=source)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/source/{source.id}/"

        results = plugin.import_url(url)

        result_identifiers = {result.show_identifier for result in results}
        assert len(results) == 2  # noqa: PLR2004
        assert show_one.show_identifier in result_identifiers
        assert show_two.show_identifier in result_identifiers
        assert all(result.is_whitelist is False for result in results)

    # TODO: Validate
    def test_import_nonexistent_source(self, function_scoped_session: Session) -> None:
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/source/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


# TODO: Validate
class TestImportPlugin:
    # TODO: Validate
    def test_import_plugin(self, function_scoped_session: Session) -> None:
        db_plugin = create_random_plugin(function_scoped_session)
        source_one = create_random_source(function_scoped_session, parent=db_plugin)
        source_two = create_random_source(function_scoped_session, parent=db_plugin)
        show_one = create_random_show(function_scoped_session, parent=source_one)
        show_two = create_random_show(function_scoped_session, parent=source_two)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/plugin/{db_plugin.id}/"

        results = plugin.import_url(url)

        result_identifiers = {result.show_identifier for result in results}
        assert len(results) == 2  # noqa: PLR2004
        assert show_one.show_identifier in result_identifiers
        assert show_two.show_identifier in result_identifiers
        assert all(result.is_whitelist is False for result in results)

    # TODO: Validate
    def test_import_nonexistent_plugin(self, function_scoped_session: Session) -> None:
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/plugin/{uuid.uuid4()}/"

        with pytest.raises(InvalidURLError):
            plugin.import_url(url)


# TODO: Validate
class TestAddResultsToChannel:
    # TODO: Validate
    def test_import_show_adds_to_channel(
        self,
        function_scoped_session: Session,
    ) -> None:
        show = create_random_show(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        assert len(channel.shows) == 1
        assert channel.shows[0].show_identifier == show.show_identifier
        assert channel.shows[0].is_whitelist is False

    # TODO: Validate
    def test_import_season_adds_to_channel_with_whitelist(
        self,
        function_scoped_session: Session,
    ) -> None:
        season = create_random_season(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/season/{season.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        assert len(channel.shows) == 1
        channel_show = channel.shows[0]
        assert channel_show.show_identifier == season.show.show_identifier
        assert channel_show.is_whitelist is True

        season_whitelist = function_scoped_session.exec(
            select(ChannelSeasonFilter).where(
                ChannelSeasonFilter.channel_show_id == channel_show.id,
            ),
        ).all()
        assert len(season_whitelist) == 1
        assert season_whitelist[0].season_identifier == season.season_identifier

    # TODO: Validate
    def test_import_episode_adds_to_channel_with_whitelist(
        self,
        function_scoped_session: Session,
    ) -> None:
        episode = create_random_episode(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/episode/{episode.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        assert len(channel.shows) == 1
        channel_show = channel.shows[0]
        assert channel_show.show_identifier == episode.season.show.show_identifier
        assert channel_show.is_whitelist is True

        episode_whitelist = function_scoped_session.exec(
            select(ChannelEpisodeFilter).where(
                ChannelEpisodeFilter.channel_show_id == channel_show.id,
            ),
        ).all()
        assert len(episode_whitelist) == 1
        assert episode_whitelist[0].episode_identifier == episode.episode_identifier

    # TODO: Validate
    def test_import_multiple_shows_from_source(
        self,
        function_scoped_session: Session,
    ) -> None:
        source = create_random_source(function_scoped_session)
        show_one = create_random_show(function_scoped_session, parent=source)
        show_two = create_random_show(function_scoped_session, parent=source)
        channel = create_random_channel(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/source/{source.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        channel_show_identifiers = {
            channel_show.show_identifier for channel_show in channel.shows
        }
        assert len(channel.shows) == 2  # noqa: PLR2004
        assert show_one.show_identifier in channel_show_identifiers
        assert show_two.show_identifier in channel_show_identifiers

    # TODO: Validate
    def test_import_show_already_in_channel(
        self,
        function_scoped_session: Session,
    ) -> None:
        show = create_random_show(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        plugin = StreamChanneler(function_scoped_session)
        url = f"streamchanneler.com/show/{show.id}/"

        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        # Import the same show again
        results = plugin.import_url(url)
        add_results_to_channel(function_scoped_session, results, channel)
        function_scoped_session.flush()

        assert len(channel.shows) == 1
