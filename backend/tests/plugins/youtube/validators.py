# TODO: Validate
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.YouTube import YouTube
from plugins.YouTube.files import is_show_season_key
from tests.plugins.plugin_validator import InvalidURLValidator, PluginValidator
from tests.plugins.plugin_validator.validator import Validator


# TODO: Validate
class YouTubeValidator(PluginValidator[YouTube]):
    """Validate all YouTube content."""

    channel_key: str
    playlist_key: str
    channel_name: str

    plugin_class = YouTube

    # TODO: Validate
    @override
    def import_url_validator(self) -> Validator:
        output = super().import_url_validator()
        # Source.data_timestamp is based on when the Source is created.
        output.incremented(Source, "data_timestamp")
        return output

    # TODO: Validate
    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        # update_at is recalculated from channel_file.data_timestamp + 30 days.
        output.incremented(show.id, "update_at")
        return output

    # TODO: Validate
    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        # Season update_at is recalculated from the RSS feed in update_season.
        output.incremented(season.id, "update_at")
        # # The show is also re-upserted during update_season.
        # output.incremented(season.show.id, "data_timestamp", "modified_at")
        return output

    # TODO: Validate
    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        output = super().update_episode_validator(episode)
        # Episodes with the same key will all get updated together.
        output.incremented(episode.key, "modified_at", "data_timestamp")
        return output

    # TODO: Validate
    @override
    def deleted_episode_validator(self, episode: Episode) -> Validator:
        output = super().deleted_episode_validator(episode)
        # A season of a show is read from the show's page, which has no feed to
        # re-derive an update_at from, so the season is left as it is. Every other
        # season has its update_at re-derived from its feed, which also bumps its
        # modified_at.
        if not is_show_season_key(episode.season.key):
            output.incremented(episode.season.id, "update_at", "modified_at")
        return output


# TODO: Validate
class ChannelWithNoUploadsMixin(YouTubeValidator):
    # TODO: Validate
    @property
    def uploads_key(self) -> str:
        return "UU" + self.channel_key[2:]


# TODO: Validate
class InvalidYouTubeURLValidator(InvalidURLValidator[YouTube]):
    plugin_class = YouTube
