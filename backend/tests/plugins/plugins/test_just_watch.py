# TODO: Validate
import json
from datetime import date, datetime, timedelta
from typing import override

import pytest
from just_scrape.new_title_buckets import NewTitleBuckets
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.JustWatch import JustWatch
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class BaseJustWatch(PluginValidator[JustWatch]):
    plugin_class = JustWatch
    class_key: str

    @override
    def import_url_validator(self) -> Validator:
        output = super().import_url_validator()
        # Plugin.data_timestamp and update_at are set during initialize_plugin based on
        # the latest bucket and providers file timestamps which may differ from the
        # verification file.
        output.ignore(Plugin, "data_timestamp", "update_at")
        return output

    @override
    def update_plugin_validator(self, session: Session, plugin: Plugin) -> Validator:
        validator = super().update_plugin_validator(session, plugin)
        # Plugin.update_at is recalculated from file timestamps.
        validator.changed(plugin.id, "update_at")
        # All sources get re-upserted during update_plugin.
        validator.changed(Source, "data_timestamp")
        validator.ignore(Source, "modified_at")
        # Sources in the bucket will be marked as outdated.
        just_watch = JustWatch(session)
        source_keys = just_watch._source_keys_from_buckets(session, plugin)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        for source_key in source_keys:
            validator.incremented(source_key, "modified_at")
            validator.populated(source_key, "update_at")
            validator.populated(source_key, "extra")
        return validator

    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        extra_dates = [date.fromisoformat(d) for d in json.loads(source.extra or "[]")]
        all_complete = all(
            tz_datetime.combine(d, datetime.min.time()) + timedelta(days=2)
            <= tz_datetime.now()
            for d in extra_dates
        )
        show = source.shows[0]
        if all_complete:
            validator.changed(source.id, "extra")
            validator.ignore(show.id, "modified_at", "update_at")
        else:
            validator.ignore(show.id, "modified_at", "update_at")
            validator.populated(source.id, "update_at")
        return validator

    def test_update_plugin(self, session_with_url: Session) -> None:
        """Update a random plugin and validate the data."""
        if self.invalid_url:
            pytest.skip()

        plugin_instance = self.plugin_class(session_with_url)
        results = plugin_instance.import_url(self.url)
        plugin = results[0].show.source.plugin
        original_plugin = self.get_detached_plugin(session_with_url)

        # Set the bucket file's data_timestamp to now so
        # _download_latest_new_titles_bucket considers it recent (within 1 day)
        # and skips downloading a new bucket.
        assert isinstance(plugin_instance, JustWatch)
        bucket_file = plugin_instance._get_latest_new_titles_bucket().one()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        bucket_file.data_timestamp = tz_datetime.now()

        self._update_and_validate(
            session_with_url,
            original_plugin,
            plugin,
        )

    @override
    def update_show_validator(self, show: Show) -> Validator:
        validator = super().update_show_validator(show).seasons_share_show_file(show)
        for season in show.seasons:
            validator.ignore(season.id, "modified_at", "data_timestamp")
        return validator

    @override
    def update_season_validator(self, season: Season) -> Validator:
        validator = (
            super().update_season_validator(season).seasons_share_show_file(season)
        )
        for sibling in season.show.seasons:
            if sibling.id != season.id:
                validator.ignore(sibling.id, "modified_at", "data_timestamp")
        return validator

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        validator = super().update_episode_validator(episode)
        validator.incremented(episode.season.id, "modified_at", "data_timestamp")
        for sibling in episode.season.episodes:
            if sibling.id != episode.id:
                validator.ignore(sibling.id, "modified_at", "data_timestamp")
        return validator

    @staticmethod
    def _create_fake_bucket_file(
        plugin_instance: JustWatch,
        timestamp: datetime,
        source_key: str,
        edge_date: date,
    ) -> None:
        """Create a fake NewTitleBucket file pointing the first edge at the source."""
        existing_bucket_file = plugin_instance._get_latest_new_titles_bucket().one()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        existing_bucket = plugin_instance._new_titles_bucket_file(existing_bucket_file)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        parsed = existing_bucket.parsed()
        first_edge = parsed[0].data.new_title_buckets.edges[0]
        assert first_edge is not None, "Bucket file has no edges"
        first_edge.key.package.short_name = source_key
        first_edge.key.date = edge_date
        new_bucket = plugin_instance._new_titles_bucket_file(timestamp)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_bucket._write(NewTitleBuckets.dump_response(parsed))  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_bucket._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

    @staticmethod
    def _create_fake_new_titles_file(
        plugin_instance: JustWatch,
        source_key: str,
        new_titles_date: date,
    ) -> None:
        """Create an empty NewTitles file so update_source doesn't try to download."""
        new_titles_file = plugin_instance._new_titles_file(  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
            source_key,
            new_titles_date,
        )
        new_titles_file._write([])  # pyright: ignore[reportPrivateUsage] # noqa: SLF001

    def test_update_source(self, session_with_url: Session) -> None:
        """Update a random source and validate the data."""
        plugin_instance = self.plugin_class(session_with_url)
        results = plugin_instance.import_url(self.url)

        # Find the specific source that will have updates available for it.
        source = next(
            result.show.source
            for result in results
            if result.show.source.key == self.class_key
        )
        assert source.data_timestamp

        new_bucket_timestamp = tz_datetime.now() + timedelta(minutes=1)
        edge_date = source.data_timestamp.date()
        self._create_fake_bucket_file(
            plugin_instance,
            new_bucket_timestamp,
            source.key,
            edge_date,
        )
        self._create_fake_new_titles_file(plugin_instance, source.key, edge_date)
        # Set source.extra to the single known-good date. Running bucket processing
        # here would pick up dates from stale buckets that don't have fake
        # NewTitles files, so we bypass it and write extra directly.
        source.extra = json.dumps([edge_date.isoformat()])

        original_plugin = self.get_detached_plugin(session_with_url)

        self._update_and_validate(
            session_with_url,
            original_plugin,
            source,
        )


class TestSingleSeasonTVShow(StandardTests, BaseJustWatch):
    url = "https://www.justwatch.com/us/tv-show/mutiny/"
    class_key = "amp"
    search_query = "Mutiny"


class TestMovie(StandardTests, BaseJustWatch):
    url = "https://www.justwatch.com/us/movie/evangelion-1-0-you-are-not-alone"
    class_key = "amp"
    search_query = "Evangelion: 1.0 You Are (Not) Alone"

    @override
    def update_show_validator(self, show: Show) -> Validator:
        return super().update_show_validator(show).episodes_share_show_file(show)

    @override
    def update_season_validator(self, season: Season) -> Validator:
        return (
            super()
            .update_season_validator(season)
            .seasons_share_show_file(season)
            .episodes_share_season_file(season)
        )

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        return (
            super()
            .update_episode_validator(episode)
            .episodes_share_show_file(episode)
            .episodes_share_season_file(episode)
        )

    def test_import_single_source(self, session_with_files: Session) -> None:
        url = f"Amazon Prime Video{self.url}"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, session_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_fuzzy_match(
        self,
        session_with_files: Session,
    ) -> None:
        url = f"amazon prime video {self.url}"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].episodes

    def test_import_everything(self, session_with_files: Session) -> None:
        results = self._import_url(session_with_files)
        for result in results:
            assert not result.seasons
            assert not result.episodes


class TestInvalidMovieUrl(InvalidURLValidator[JustWatch]):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/movie/invalid-url"


class TestInvalidTVShowUrl(InvalidURLValidator[JustWatch]):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/tv-show/invalid-url"


class TestMultipleSeasonTVShow(StandardTests, BaseJustWatch):
    plugin_class = JustWatch
    url = "https://www.justwatch.com/us/tv-show/mutant-x/"
    class_key = "amp"
    search_query = "Mutant X"

    def test_import_single_source(self, session_with_files: Session) -> None:
        url = f"Amazon Prime Video{self.url}"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, session_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Amazon Prime Video"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_and_season(self, session_with_files: Session) -> None:
        url = f"Amazon Prime Video {self.url}/season-2"
        results = self._import_url(session_with_files, url)
        assert len(results) == 1
        assert len(results[0].seasons) == 1
        assert isinstance(results[0].seasons[0], Season)
        assert not results[0].episodes
