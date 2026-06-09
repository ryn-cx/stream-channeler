# TODO: Validate
from datetime import date, datetime, timedelta
from typing import override
from unittest.mock import patch

import pytest
from just_scrape.new_title_buckets import NewTitleBuckets
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.JustWatch import JustWatch
from plugins.JustWatch.files import NewTitleBucket
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    block_downloads,
)
from tests.plugins.plugin_validator.validator import Validator


class BaseJustWatch(PluginValidator[JustWatch]):
    plugin_class = JustWatch
    class_key: str

    # @override
    # def _import_files(self, session: Session) -> None:
    #     # initialize_source refreshes the latest new-titles bucket whenever the newest
    #     # one is more than a day old, which recorded test data always is, so it would
    #     # trigger a real download during fixture setup. The recorded bucket is enough
    #     # for these tests, so skip the refresh.
    #     with patch.object(JustWatch, "_download_latest_new_titles_bucket"):
    #         super()._import_files(session)

    def _incomplete_bucket_source_dates(
        self,
        session: Session,
        plugin: Plugin,
    ) -> list[tuple[str, date]]:
        """Return (source_key, edge_date) for incomplete-bucket edges with a source."""
        plugin_instance = JustWatch(session)
        statement = select(File).where(
            File.plugin_id == plugin.id,
            col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
            File.extra == "Incomplete",
        )
        entries: list[tuple[str, date]] = []
        for bucket_file in session.exec(statement).all():
            bucket = plugin_instance.new_titles_bucket_file(bucket_file)
            for edge in bucket.parsed_edges():
                source = Source.get_from_memory(
                    session,
                    plugin,
                    edge.key.package.short_name,
                )
                if source:
                    entries.append((source.key, edge.key.date))
        return entries

    @override
    def update_plugin_validator(self, session: Session, plugin: Plugin) -> Validator:
        validator = super().update_plugin_validator(session, plugin)
        validator.incremented(plugin.id, "update_at")
        # All sources get re-upserted during update_plugin.
        validator.incremented(Source, "data_timestamp")
        validator.incremented(Source, "modified_at")
        # Sources referenced by an unprocessed bucket are marked outdated.
        for source_key, _ in self._incomplete_bucket_source_dates(session, plugin):
            validator.populated(source_key, "update_at")
        return validator

    def test_update_plugin(self, session_with_url: Session) -> None:
        """Update a random plugin and validate the data."""
        if self.invalid_url or not self.url:
            pytest.skip()

        plugin_instance = self.plugin_class(session_with_url)
        assert isinstance(plugin_instance, JustWatch)
        # The URL's files are already imported by the session_with_url fixture, so the
        # re-import finds the shows preloaded and never downloads.
        with block_downloads():
            results = plugin_instance.import_url(self.url)
        plugin = results[0].show.source.plugin

        # Pre-create the NewTitles files that bucket processing will mark incomplete
        # so the mocked update doesn't try to download an unrecorded file.
        for source_key, edge_date in self._incomplete_bucket_source_dates(
            session_with_url,
            plugin,
        ):
            plugin_instance.new_titles_file(source_key, edge_date)._write([])  # pyright: ignore[reportPrivateUsage] # noqa: SLF001

        original_plugin = self.get_detached_plugin(session_with_url)

        # Set the bucket file's data_timestamp to now so
        # _download_latest_new_titles_bucket considers it recent (within 1 day)
        # and skips downloading a new bucket.
        bucket_file = plugin_instance._get_latest_new_titles_bucket().one()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        bucket_file.data_timestamp = tz_datetime.now()

        self._update_and_validate(
            session_with_url,
            original_plugin,
            plugin,
        )

    @override
    def update_season_validator(self, season: Season) -> Validator:
        return super().update_season_validator(season).seasons_share_show_file(season)

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        return (
            super()
            .update_episode_validator(episode)
            .episodes_share_season_file(episode)
        )

    @staticmethod
    def _create_fake_bucket_file(
        plugin_instance: JustWatch,
        timestamp: datetime,
        source_key: str,
        edge_date: date,
    ) -> None:
        """Create a fake NewTitleBucket file pointing the first edge at the source."""
        existing_bucket_file = plugin_instance._get_latest_new_titles_bucket().one()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        existing_bucket = plugin_instance.new_titles_bucket_file(existing_bucket_file)
        parsed = existing_bucket.parsed()
        first_edge = parsed[0].data.new_title_buckets.edges[0]
        assert first_edge is not None, "Bucket file has no edges"
        first_edge.key.package.short_name = source_key
        first_edge.key.date = edge_date
        new_bucket = plugin_instance.new_titles_bucket_file(timestamp)
        new_bucket._write(NewTitleBuckets.dump_response(parsed))  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_bucket._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

    @staticmethod
    def _create_fake_new_titles_file(
        plugin_instance: JustWatch,
        source_key: str,
        new_titles_date: date,
    ) -> None:
        """Create an empty, pending NewTitles file so update_source processes it."""
        new_titles_file = plugin_instance.new_titles_file(
            source_key,
            new_titles_date,
        )
        new_titles_file._write([])  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_titles_file.database_record.extra = "Incomplete"

    def test_update_source(self, session_with_url: Session) -> None:
        if self.invalid_url or not self.url:
            pytest.skip()

        plugin_instance = self.plugin_class(session_with_url)
        # The URL's files are already imported by the session_with_url fixture, so the
        # re-import finds the shows preloaded and never downloads.
        with block_downloads():
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
        return (
            super()
            .update_show_validator(show)
            .seasons_share_show_file(show)
            .episodes_share_show_file(show)
        )

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
            .episodes_share_file(episode)
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
