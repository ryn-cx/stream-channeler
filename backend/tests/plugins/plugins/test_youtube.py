# TODO: Validate
from typing import override

import pytest
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.plugins.YouTube import YouTube
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class YouTubeValidator(PluginValidator[YouTube]):
    url: str
    channel_key: str
    playlist_key: str
    channel_name: str

    plugin_class = YouTube

    @pytest.fixture(params=YouTube.domains())
    def domain(self, request: pytest.FixtureRequest) -> str:
        return request.param

    @override
    def import_url_validator(self) -> Validator:
        output = super().import_url_validator()
        # Source.data_timestamp is based on when the Source is created.
        output.incremented(Source, "data_timestamp")
        return output

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        # update_at is recalculated from channel_file.data_timestamp + 30 days.
        output.incremented(show.id, "update_at")
        return output

    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        # Season update_at is recalculated by _set_season_update_at.
        output.incremented(season.id, "update_at")
        # The show is also re-upserted during update_season.
        output.incremented(season.show.id, "data_timestamp", "modified_at")
        return output

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        output = super().update_episode_validator(episode)
        # Episodes with the same key will all get updated together.
        output.incremented(episode.key, "modified_at", "data_timestamp")
        return output

    @override
    def deleted_episode_validator(self, episode: Episode) -> Validator:
        output = super().deleted_episode_validator(episode)
        # _set_season_update_at recalculates update_at from episode release dates.
        # Whether it changes depends on whether the fake episode had the latest
        # release date, so we ignore it.
        output.ignore(episode.season.id, "update_at")
        return output


class PlaylistValidator(YouTubeValidator):
    @pytest.fixture(
        params=[
            "/playlist?list={key}",
            # Dummy values for the video ID.
            "/watch?v=0123456789A&list={key}",
            "/0123456789A?list={key}",
        ],
    )
    def playlist_path(self, request: pytest.FixtureRequest) -> str:
        return request.param.format(key=self.playlist_key)

    def test_import_response(
        self,
        db_with_url: Session,
        domain: str,
        playlist_path: str,
    ) -> None:
        results = self._import_url(db_with_url, url=domain + playlist_path)
        result = results[0]

        assert len(results) == 1
        assert result.show.key == self.channel_key
        assert len(result.seasons) == 1
        assert result.seasons[0].key == self.playlist_key
        assert result.whitelist_mode is False


class ChannelValidator(YouTubeValidator):
    @pytest.fixture(
        params=["/{name}", "/@{name}", "/c/{name}", "/channel/{key}"],
    )
    def base_channel_path(self, request: pytest.FixtureRequest) -> str:
        return request.param.format(name=self.channel_name, key=self.channel_key)

    @pytest.fixture(params=["", "/videos", "/featured"])
    def channel_path(
        self,
        request: pytest.FixtureRequest,
        base_channel_path: str,
    ) -> str:
        return base_channel_path + request.param

    def test_channel_import_response(
        self,
        db_with_url: Session,
        domain: str,
        channel_path: str,
    ) -> None:
        url = domain + channel_path
        results = self._import_url(db_with_url, url=url)
        result = results[0]

        assert len(results) == 1
        assert result.show.key == self.channel_key
        assert len(result.seasons) == 1
        assert result.seasons[0].key == "UU" + self.channel_key[2:]
        assert result.whitelist_mode

    def test_channel_playlists_import_response(
        self,
        db_with_url: Session,
        domain: str,
        base_channel_path: str,
    ) -> None:
        url = domain + base_channel_path + "/playlists"
        results = self._import_url(db_with_url, url=url)
        result = results[0]

        assert len(results) == 1
        assert result.show.key == self.channel_key
        assert sorted(season.key for season in result.seasons) == sorted(
            season.key for season in result.show.seasons
        )
        assert result.whitelist_mode is False


class ChannelWithNoUploadsMixin(YouTubeValidator):
    @property
    def uploads_key(self) -> str:
        return "UU" + self.channel_key[2:]

    @override
    def import_url_validator(self) -> Validator:
        output = super().import_url_validator()
        output.ignore(self.uploads_key, "update_at")
        return output

    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        if season.key == self.uploads_key:
            output.changed(season.id, "update_at")
        return output


# This also ends up having a playlist with no videos PL2666A74DC50B1A76
class Test16CharacterPlaylist(StandardTests, PlaylistValidator):
    channel_key = "UCeAS7YuMOKpz39PD07O2p_w"
    playlist_key = "PL374F6CD60916C2C7"
    url = f"youtube.com/playlist?list={playlist_key}"


class Test32CharacterPlaylist(StandardTests, PlaylistValidator):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    playlist_key = "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"
    url = f"youtube.com/playlist?list={playlist_key}"


class TestPlaylistWithDeletedVideos(
    StandardTests, ChannelWithNoUploadsMixin, PlaylistValidator
):
    channel_key = "UCJ0cZ4i3wJU5OMVyRH_PxyQ"
    playlist_key = "PL1cA0ECqV9x-mC2Pxon9_YNDuM5PdyhyH"
    url = f"youtube.com/playlist?list={playlist_key}"


class TestNamedChannel(StandardTests, ChannelValidator):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"
    url = f"youtube.com/{channel_name}"

    def test_episode_in_multiple_seasons(self, db_with_url: Session) -> None:
        """Test that episodes that belong to multiple seasons works correctly."""
        results = self._import_url(db_with_url)
        result = results[0]
        show = result.show
        episode_count = 0
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == "jNQXAC9IVRw":
                    episode_count += 1
        assert episode_count == 2  # noqa: PLR2004


# A channel with no uploads can be imported because the channel may have playlists with
# videos.
class TestChannelWithoutUploads(
    StandardTests, ChannelWithNoUploadsMixin, ChannelValidator
):
    channel_key = "UCJ0cZ4i3wJU5OMVyRH_PxyQ"
    channel_name = "highballrider"
    url = f"youtube.com/@{channel_name}"

    # When there are no uploads for a channel the fallback is to import all of the
    # playlists instead.
    def test_channel_import_response(
        self,
        db_with_url: Session,
        domain: str,
        channel_path: str,
    ) -> None:
        self.test_channel_playlists_import_response(db_with_url, domain, channel_path)


# A channel with no playlists can be imported because the channel may have uploads.
class TestChannelWithoutPlaylists(StandardTests, ChannelValidator):
    channel_key = "UCVlx-IvZ_TBWRKU0UQCaueQ"
    channel_name = "chad"
    url = f"youtube.com/{channel_name}"


# class TestLargeChannel(ChannelValidator):
#     channel_key = "UCX6OQ3DkcsbYNE6H8uQQuVA"
#     channel_name = "MrBeast"
#     url = f"youtube.com/{channel_name}"


class InvalidYouTubeURLValidator(InvalidURLValidator[YouTube]):
    plugin_class = YouTube


class TestInvalidChannelName(InvalidYouTubeURLValidator):
    url = "youtube.com/@jawed0123456789"


class TestInvalidPlaylist(InvalidYouTubeURLValidator):
    url = "youtube.com/playlist?list=PL0123456789ABCDEF"


class TestInvalidChannelId(InvalidYouTubeURLValidator):
    url = "youtube.com/channel/UC0123456789ABCDEFGHIJHI"
