# TODO: Validate
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.Tubi import Tubi
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class TubiValidator(PluginValidator[Tubi]):
    plugin_class = Tubi

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output

    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        # Every entity's data comes from the single content file, so updating one
        # season refreshes the whole show.
        output.incremented(Season, "data_timestamp", "modified_at")
        output.incremented(Episode, "data_timestamp", "modified_at")
        output.incremented(season.id, "update_at")
        return output

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        output = super().update_episode_validator(episode)
        output.incremented(Season, "data_timestamp", "modified_at")
        output.incremented(Episode, "data_timestamp", "modified_at")
        output.incremented(episode.id, "update_at")
        return output


class TubiStandardTests(StandardTests[Tubi], TubiValidator):
    pass


class MovieURLs:
    urls: tuple[str, ...] = (
        "/movies/{content_id}/{slug}",
        "/movies/{content_id}",
        "/movies/{content_id}/",
    )


class SeriesURLs:
    urls: tuple[str, ...] = (
        "/series/{content_id}/{slug}",
        "/series/{content_id}",
        "/series/{content_id}/",
    )


class EpisodeURLs:
    urls: tuple[str, ...] = (
        "/tv-shows/{content_id}/{slug}",
        "/tv-shows/{content_id}",
        "/tv-shows/{content_id}/",
    )


class TestMovie(MovieURLs, TubiStandardTests):
    # Megamind (2010).
    content_id = "100029837"
    slug = "megamind"


class TestSingleSeasonShow(SeriesURLs, TubiStandardTests):
    # Kingpin (2025) — a single season with six episodes.
    content_id = "300016176"
    slug = "kingpin"


class TestMultipleSeasonsShow(SeriesURLs, TubiStandardTests):
    # Scooby-Doo Where Are You? — two seasons.
    content_id = "300006854"
    slug = "scooby-doo-where-are-you"


class TestEpisode(EpisodeURLs, TubiStandardTests):
    # Kingpin S01:E01, which resolves to the Kingpin series.
    content_id = "200218827"
    slug = "s01-e01-episode-1"


class InvalidTubiValidator(InvalidURLValidator[Tubi]):
    plugin_class = Tubi


class TestInvalidMovie(MovieURLs, InvalidTubiValidator):
    content_id = "999999999999"
    slug = "invalid"


class TestInvalidSeries(SeriesURLs, InvalidTubiValidator):
    content_id = "999999999999"
    slug = "invalid"


class TestInvalidEpisode(EpisodeURLs, InvalidTubiValidator):
    content_id = "999999999999"
    slug = "invalid"
