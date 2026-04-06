# TODO: Validate
import json
from datetime import date, datetime, timedelta
from typing import override

import pytest
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.JustWatch import JustWatch
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from tests.plugins.plugin_validator import InvalidURLValidator, PluginValidator
from tests.plugins.plugin_validator.validator import Validator


class BaseJustWatch(PluginValidator):
    plugin_class = JustWatch
    class_key: str

    @override
    def _import_url_validator(self) -> Validator:
        output = super()._import_url_validator()
        # Plugin.data_timestamp and update_at are set during initialize_plugin based on
        # the latest bucket and providers file timestamps which may differ from the
        # verification file.
        output.ignore(Plugin, "data_timestamp", "update_at")
        return output

    @override
    def _update_plugin_validator(self, db: Session, plugin: Plugin) -> Validator:
        validator = super()._update_plugin_validator(db, plugin)
        # Plugin.update_at is recalculated based on the providers file and bucket
        # timestamps, which may result in a different (not necessarily higher) value.
        validator.changed(plugin.id, "update_at")

        # All sources get re-upserted during update_plugin which resets their
        # data_timestamp.
        validator.changed(Source, "data_timestamp")
        validator.ignore(Source, "modified_at")

        # Every source contained in the new titles bucket will be marked as outdated.
        just_watch = JustWatch(db)
        source_keys = just_watch._source_keys_from_buckets(db, plugin)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        for source_key in source_keys:
            validator.incremented(source_key, "modified_at")
            validator.populated(source_key, "update_at")
            validator.populated(source_key, "extra")
        return validator

    def test_update_plugin(self, db_with_url: Session) -> None:
        """Update a random plugin and validate the data."""
        if self.invalid_url or self.skip_update_tests:
            pytest.skip()

        plugin_instance = self.plugin_class(db_with_url, url=self.url)
        results = plugin_instance.import_url(self.url)
        plugin = results[0].show.source.plugin
        original_plugin = self._get_detached_plugin(db_with_url)

        # Set the bucket file's data_timestamp to now so no new files are downloaded.
        assert isinstance(plugin_instance, JustWatch)
        bucket_file = plugin_instance._get_latest_new_titles_bucket().one()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        bucket_file.data_timestamp = tz_datetime.now()

        self._update_and_validate(
            db_with_url,
            original_plugin,
            plugin,
            static_keys=list(Plugin.model_fields),
        )

    def _update_source_validator(self, source: Source) -> Validator:
        validator = super()._update_source_validator(source)

        # Dates older than the minimum_new_titles_data_timestamp threshold (date + 2
        # days) are considered complete and will be removed from extra.
        extra_dates = [date.fromisoformat(d) for d in json.loads(source.extra or "[]")]
        all_complete = all(
            tz_datetime.combine(d, datetime.min.time()) + timedelta(days=2)
            <= tz_datetime.now()
            for d in extra_dates
        )
        show = source.shows[0]
        if all_complete:
            validator.changed(source.id, "extra")
            # When dates are complete, the show may or may not appear in the new
            # titles edges depending on external data.
            validator.ignore(show.id, "modified_at", "update_at")
        else:
            # The show being tested should be set to be updated.
            validator.ignore(show.id, "modified_at", "update_at")
            validator.populated(source.id, "update_at")
        return validator

    def _update_show_validator(self, show: Show) -> Validator:
        validator = super()._update_show_validator(show).seasons_share_show_file(show)
        # Seasons share the UrlTitleDetails file with the show, but
        # _oldest_file_timestamp also includes CustomSeasonEpisodes which won't
        # be re-downloaded during update_show, so the season's data_timestamp
        # won't change.
        for season in show.seasons:
            validator.ignore(season.id, "modified_at", "data_timestamp")
        return validator

    def _update_season_validator(self, season: Season) -> Validator:
        validator = (
            super()._update_season_validator(season).seasons_share_show_file(season)
        )
        # Sibling seasons share UrlTitleDetails but their own
        # CustomSeasonEpisodes won't be re-downloaded, so they won't update.
        for sibling in season.show.seasons:
            if sibling.id != season.id:
                validator.ignore(sibling.id, "modified_at", "data_timestamp")
        return validator

    def _update_episode_validator(self, episode: Episode) -> Validator:
        validator = super()._update_episode_validator(episode)
        # The season shares CustomSeasonEpisodes with episodes, so updating an
        # episode also re-downloads the season file, causing the season to update.
        validator.incremented(episode.season.id, "modified_at", "data_timestamp")
        # Episodes share CustomSeasonEpisodes but each has its own
        # CustomBuyBoxOffers. Since _oldest_file_timestamp takes the min of
        # both, sibling episodes won't actually update because their
        # CustomBuyBoxOffers wasn't re-downloaded.
        for sibling in episode.season.episodes:
            if sibling.id != episode.id:
                validator.ignore(sibling.id, "modified_at", "data_timestamp")
        return validator

    def test_update_source(self, db_with_url: Session) -> None:
        """Update a random source and validate the data."""
        plugin_instance = self.plugin_class(db_with_url, url=self.url)
        results = plugin_instance.import_url(self.url)

        # Find the specific source that will have updates available for it.
        source = next(
            result.show.source
            for result in results
            if result.show.source.key == self.class_key
        )
        assert source.data_timestamp
        # Normally update_plugin would set this value.
        source.extra = json.dumps([source.data_timestamp.date().isoformat()])
        original_plugin = self._get_detached_plugin(db_with_url)

        mocka = False
        try:
            self._update_and_validate(
                db_with_url,
                original_plugin,
                source,
                use_mock_update=mocka,
                static_keys=list(Source.model_fields),
            )
        finally:
            if not mocka:
                self._export_all_files(db_with_url)


class TestSingleSeasonTVShow(BaseJustWatch):
    url = "https://www.justwatch.com/us/tv-show/mutiny/"
    class_key = "amp"


class TestMovie(BaseJustWatch):
    url = "https://www.justwatch.com/us/movie/evangelion-1-0-you-are-not-alone"
    class_key = "amp"

    @override
    def _update_show_validator(self, show: Show) -> Validator:
        return super()._update_show_validator(show).episodes_share_show_file(show)

    @override
    def _update_season_validator(self, season: Season) -> Validator:
        return (
            super()
            ._update_season_validator(season)
            .seasons_share_show_file(season)
            .episodes_share_season_file(season)
        )

    @override
    def _update_episode_validator(self, episode: Episode) -> Validator:
        return (
            super()
            ._update_episode_validator(episode)
            .episodes_share_show_file(episode)
            .episodes_share_season_file(episode)
        )

    def test_import_single_source(self, db_with_files: Session) -> None:
        url = f"Amazon Prime Video{self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_fuzzy_match(self, db_with_files: Session) -> None:
        url = f"amazon prime video {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].episodes

    def test_import_everything(self, db_with_files: Session) -> None:
        results = self._import_url(db_with_files)
        for result in results:
            assert not result.seasons
            assert not result.episodes


class TestInvalidMovieUrl(InvalidURLValidator):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/movie/invalid-url"


class TestInvalidTVShowUrl(InvalidURLValidator):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/tv-show/invalid-url"


class TestMultipleSeasonTVShow(BaseJustWatch):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/tv-show/mutant-x/"
    class_key = "amp"

    def test_import_single_source(self, db_with_files: Session) -> None:
        url = f"Amazon Prime Video{self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_and_season(self, db_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}/season-2"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert len(results[0].seasons) == 1
        assert isinstance(results[0].seasons[0], Season)
        assert not results[0].episodes


# TODO: TestSearch requires cached test data to work. Generate test data first.
# class TestSearch(PluginValidator):
#     plugin_class = JustWatch
#     search_query = "South Park"
