import json
from datetime import date, datetime, timedelta
from typing import override

import pytest
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.JustWatch import JustWatch
from app.plugins.plugins.JustWatch.files import NewTitlesBucket
from app.plugins.schemas import PluginInput
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
    def _update_plugin_validator(self, db: Session, plugin: Plugin) -> Validator:
        validator = super()._update_plugin_validator(db, plugin)
        # Plugin.update_at will automatically increment based on the timestamp of the
        # existing files.
        validator.incremented(plugin.id, "update_at")

        # Every source contained in the new titles bucket will be marked as outdated.
        source_keys = self._source_keys_from_buckets(db, plugin)
        for source_key in source_keys:
            validator.incremented(source_key, "modified_at")
            validator.populated(source_key, "update_at")
            validator.populated(source_key, "extra")
        return validator

    @staticmethod
    def _source_keys_from_buckets(db: Session, plugin: Plugin) -> set[str]:
        """Get all source keys with new titles from unimported bucket files."""
        statement = select(File).where(
            File.plugin_id == plugin.id,
            col(File.key).startswith(f"{NewTitlesBucket.__name__}/"),
            col(File.data_timestamp) > plugin.data_timestamp
            if plugin.data_timestamp
            else True,
        )
        source_keys: set[str] = set()
        for file in db.exec(statement).all():
            bucket = NewTitlesBucket(
                db,
                plugin,
                tz_datetime.fromisotimestamp(
                    NewTitlesBucket.file_key_to_unique_identifier(file.key),
                ),
            )
            for edge in bucket.parsed_edges():
                if edge.node.total_count > 0:
                    source_keys.add(edge.key.package.short_name)
        return source_keys

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
            static_keys=list(PluginInput.model_fields),
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
        return super()._update_show_validator(show).seasons_share_show_file(show)

    def _update_season_validator(self, season: Season) -> Validator:
        return (
            super()
            ._update_season_validator(season)
            .seasons_share_show_file(season)
            .seasons_share_file(season)
        )

    def _update_episode_validator(self, episode: Episode) -> Validator:
        return super()._update_episode_validator(episode).episodes_share_file(episode)

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


class TestJustWatchSingleSeasonTVShow(BaseJustWatch):
    url = "https://www.justwatch.com/us/tv-show/girl-from-nowhere-the-reset/"
    class_key = "nfx"


class TestJustWatchMovie(BaseJustWatch):
    url = "https://www.justwatch.com/us/movie/the-plastic-detox"
    class_key = "nfx"

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
        url = f"Netflix{self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Netflix"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db_with_files: Session) -> None:
        url = f"Netflix {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Netflix"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_fuzzy_match(self, db_with_files: Session) -> None:
        url = f"netflix {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Netflix"
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
    url = "https://www.justwatch.com/us/tv-show/gintama/"
    class_key = "nfx"

    def test_import_single_source(self, db_with_files: Session) -> None:
        url = f"Netflix{self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Netflix"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db_with_files: Session) -> None:
        url = f"Netflix {self.url}"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Netflix"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_and_season(self, db_with_files: Session) -> None:
        url = f"Netflix {self.url}/season-2"
        results = self._import_url(db_with_files, url)
        assert len(results) == 1
        assert len(results[0].seasons) == 1
        assert isinstance(results[0].seasons[0], Season)
        assert not results[0].episodes

    def test_import_single_season(self, db_with_files: Session) -> None:
        url = f"{self.url}/season-2"
        results = self._import_url(db_with_files, url)
        for result in results:
            assert len(result.seasons) == 1
            assert result.seasons[0].season_number == 2  # noqa: PLR2004
            assert not result.episodes

    def test_import_everything(self, db_with_files: Session) -> None:
        results = self._import_url(db_with_files)
        for result in results:
            assert not result.seasons
            assert not result.episodes
