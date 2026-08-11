# TODO: Validate
from datetime import timedelta
from typing import override

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Netflix import Netflix
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


# TODO: Validate
class NetflixValidator(PluginValidator[Netflix]):
    plugin_class = Netflix

    # TODO: Validate
    @override
    def import_url_validator(self) -> Validator:
        output = super().import_url_validator()
        output.incremented(Source, "data_timestamp")
        return output

    # TODO: Validate
    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output

    # TODO: Validate
    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        output.incremented(Season, "data_timestamp", "modified_at")
        output.incremented(Episode, "data_timestamp", "modified_at")
        # Only the updated season's update_at is recomputed (others stay sooner).
        output.incremented(season.id, "update_at")
        return output

    # TODO: Validate
    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        output = super().update_episode_validator(episode)
        output.incremented(Season, "data_timestamp", "modified_at")
        output.incremented(Episode, "data_timestamp", "modified_at")
        # Only the updated episode's update_at is recomputed (others stay sooner).
        output.incremented(episode.id, "update_at")
        return output


# TODO: Validate
class NetflixStandardTests(StandardTests[Netflix], NetflixValidator):
    pass


# class TestShow(NetflixStandardTests):
#     # Virgin River — a stable public title.
#     parse_url_response = "80240027"
#     urls = (
#         "/title/{parse_url_response}",
#         "/title/{parse_url_response}/",
#     )


# TODO: Validate
class TestAiringShow(NetflixStandardTests):
    # Chainsmoker Cat — currently airing; it advertises an upcoming episode via a
    # tagline message, so the show refreshes weekly instead of monthly.
    parse_url_response = "82760630"
    urls = (
        "/title/{parse_url_response}",
        "/title/{parse_url_response}/",
    )

    # TODO: Validate
    def test_upcoming_update_schedule(self, session_with_files: Session) -> None:
        """An airing title refreshes on the upcoming episode's scheduled day."""
        results = self._import_url(session_with_files)
        show = results[0].show
        assert show.data_timestamp is not None
        thursday = 3  # "New Episode Coming Thursday"
        days_ahead = (thursday - show.data_timestamp.weekday()) % 7 or 1
        assert show.update_at == show.data_timestamp + timedelta(days=days_ahead)


# class InvalidNetflixURLValidator(InvalidURLValidator[Netflix]):
#     plugin_class = Netflix


# class TestInvalidURL(InvalidNetflixURLValidator):
#     # Not a title URL, so the regex rejects it.
#     urls = ("https://www.netflix.com/browse",)
