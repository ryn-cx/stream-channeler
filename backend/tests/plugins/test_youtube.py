# TODO: Validate
# TODO: Tests that test the return type of the import

from typing import override

import pytest
from sqlmodel import Session

from app.media.models import Episode, Season, Show, Source
from app.plugins.utils.abstract_plugin import InvalidURLError
from app.plugins.YouTube import YouTube
from tests.plugins.plugin_validator import (
    PluginValidator,
    PluginValidatorBase,
)
from tests.plugins.validator import Validator

# TODO: Add test_is_valid_url_format


class YouTubeValidator(PluginValidator):
    skip_test_update_source = True
    plugin_class = YouTube

    # 1. Get plugin
    # 2. Validate URL. TODO: Can probably be oprimized away by querying show/season
    #    values directly.
    # 3. Check if show exists.
    # 4. Preload Channel
    # 5. Preload Playlist
    # 6. Preload Video
    IMPORT_URL_QUERY_COUNT = 6

    # 1. Get plugin
    # 2. Validate URL. TODO: Can probably be oprimized away by querying show/season
    #    values directly.
    # 3. Check if show exists.
    EXISTING_URL_QUERY_COUNT = 3

    # 1. Get plugin (__preload_plugin)
    # 2. Get Sources/Shows/Season/Episode (_add_all_to_preload_cache)
    # 3. Preload Playlist (__preload_playlist_files)
    # 4. Preload files (_preload_show_season_episode_files)
    # 5-6. Preload Channel (_preload_show)
    UPDATE_SHOW_QUERY_COUNT = 6
    UPDATE_SEASON_QUERY_COUNT = 6
    UPDATE_EPISODE_QUERY_COUNT = 6

    @override
    def _import_url_validator(self) -> Validator:
        output = super()._import_url_validator()
        # Source.data_timestamp is based on when the Source is created.
        output.incremented(Source, "data_timestamp")
        # Update at is based on the current date and when the last episode was added to
        # a playlist so it will increase.
        output.incremented(Season, "update_at")
        return output

    @override
    def _update_show_validator(self, show: Show) -> Validator:
        output = super()._update_show_validator(show)
        # Show update_at should always increment because the next update is based on
        # when the last update occurred.
        output.incremented(Show, "update_at")
        return output

    @override
    def _update_season_validator(self, season: Season) -> Validator:
        output = super()._update_season_validator(season)
        # Season update_at is set based on the distance between the last episode and the
        # current time so it will aways be incremented.
        output.incremented(season.id, "update_at")
        output.remove(season.id, "update_at")
        output.changed(season.id, "update_at")
        return output

    def _update_episode_validator(self, episode: Episode) -> Validator:
        output = super()._update_episode_validator(episode)
        # The same video can appear in multiple playlists. If one of these videos is
        # updated all of them are updated and not just the one for the specific season.
        output.incremented(episode.key, "data_timestamp")
        output.incremented(episode.key, "modified_at")
        return output


class Test16CharacterPlaylist(YouTubeValidator):
    url = "youtube.com/playlist?list=PL374F6CD60916C2C7"

    def test_return_value(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        assert len(results) == 1
        result = results[0]
        assert result.show.key == "UCeAS7YuMOKpz39PD07O2p_w"
        assert len(result.seasons) == 1
        season = result.seasons[0]
        assert season.key == "PL374F6CD60916C2C7"


class Test32CharacterPlaylist(YouTubeValidator):
    # This URL will also test having an episode that is in multiple playlists as the
    # video "Me at the zoo" is in this playlist and the channel uploads playlist.
    url = "youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"

    def test_return_value(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        assert len(results) == 1
        result = results[0]
        assert result.show.key == "UC4QobU6STFB0P71PMvOGN5A"
        assert len(result.seasons) == 1
        season = result.seasons[0]
        assert season.key == "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"


class TestNamedChannelPlaylists(YouTubeValidator):
    url = "youtube.com/jawed/playlists"

    def test_return_value(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        result = results[0]
        assert result.show.key == "UC4QobU6STFB0P71PMvOGN5A"
        assert len(result.seasons) == 1
        assert result.seasons[0].key == "UU4QobU6STFB0P71PMvOGN5A"


class TestNamedChannel(YouTubeValidator):
    url = "youtube.com/jawed"

    def test_return_value(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        result = results[0]
        assert result.show.key == "UC4QobU6STFB0P71PMvOGN5A"
        assert len(result.seasons) == 1
        assert result.seasons[0].key == "UU4QobU6STFB0P71PMvOGN5A"


class TestNamedAtChannelVideos(YouTubeValidator):
    url = "youtube.com/@jawed/videos"

    def test_return_value(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        result = results[0]
        assert result.show.key == "UC4QobU6STFB0P71PMvOGN5A"
        assert len(result.seasons) == 1
        assert result.seasons[0].key == "UU4QobU6STFB0P71PMvOGN5A"


class TestEpisodeInMultipleSeasons(YouTubeValidator):
    url = "youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"


class TestPlaylistWithDeletedEpisodes(YouTubeValidator):
    url = "youtube.com/playlist?list=PL1cA0ECqV9x-mC2Pxon9_YNDuM5PdyhyH"


class TestChannelWithoutUploads(YouTubeValidator):
    # A channel with no uploads may be imported because the channel has playlists that
    # the user is interested in.
    url = "youtube.com/@highballrider/playlists"


class TestChannelWithoutPlaylists(YouTubeValidator):
    url = "youtube.com/@chad"


class TestInvalidChannelName(PluginValidatorBase):
    plugin_class = YouTube
    url = "youtube.com/@jawed0123456789"

    def test_return_value(self, db: Session) -> None:
        with pytest.raises(InvalidURLError, match="Invalid YouTube URL:"):
            self._import_files_and_url(db)

        self._export_all_files(db)


class TestInvalidPlaylist(PluginValidatorBase):
    plugin_class = YouTube
    # Modified version of jawed's playlist
    url = "youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSi"

    def test_return_value(self, db: Session) -> None:
        with pytest.raises(InvalidURLError, match="Invalid YouTube URL:"):
            self._import_files_and_url(db)

        self._export_all_files(db)


class TestLargeChannel(YouTubeValidator):
    url = "youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA"


class TestInvalidChannelId(PluginValidatorBase):
    plugin_class = YouTube
    # Modified version of jawed's channel
    url = "youtube.com/channel/UC4QobU6STFB0P71PMvOGN5B"

    def test_return_value(self, db: Session) -> None:
        with pytest.raises(InvalidURLError, match="Invalid YouTube URL:"):
            self._import_files_and_url(db)

        self._export_all_files(db)
