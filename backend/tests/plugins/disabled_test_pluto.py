# TODO: Validate
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.Pluto import Pluto
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class PlutoValidator(PluginValidator[Pluto]):
    plugin_class = Pluto

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output

    @override
    def update_season_validator(self, season: Season) -> Validator:
        output = super().update_season_validator(season)
        # Every entity's data comes from the single seasons file, so updating one
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


class PlutoStandardTests(StandardTests[Pluto], PlutoValidator):
    pass


class MovieURLs:
    urls: tuple[str, ...] = (
        "/en/on-demand/movies/{item_id}/details",
        "/en/on-demand/movies/{item_id}",
        "/us/on-demand/movies/{item_id}/",
        "/on-demand/movies/{item_id}",
    )


class SeriesURLs:
    urls: tuple[str, ...] = (
        "/en/on-demand/series/{item_id}/details",
        "/en/on-demand/series/{item_id}",
        "/us/on-demand/series/{item_id}/",
        "/on-demand/series/{item_id}",
        "/en/on-demand/series/{item_id}/season/1",
    )


class TestMovie(MovieURLs, PlutoStandardTests):
    # Hansan: Rising Dragon (2022).
    item_id = "68a54f49df1220b53566f16e"


class TestSingleSeasonShow(SeriesURLs, PlutoStandardTests):
    # Gordon Ramsay Behind Bars — a single season with four episodes.
    item_id = "66abc7823653a6001363e279"


class TestMultipleSeasonsShow(SeriesURLs, PlutoStandardTests):
    # On Death Row — two seasons with four episodes each.
    item_id = "5ef05c6acdce3c001a779a79"


class InvalidPlutoValidator(InvalidURLValidator[Pluto]):
    plugin_class = Pluto


class TestInvalidMovie(MovieURLs, InvalidPlutoValidator):
    item_id = "aaaaaaaaaaaaaaaaaaaaaaaa"


class TestInvalidSeries(SeriesURLs, InvalidPlutoValidator):
    item_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
