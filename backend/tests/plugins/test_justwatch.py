# TODO: Validate
from datetime import datetime, timedelta
from typing import override

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.JustWatch import JustWatch
from plugins.JustWatch.files import just_scrape
from plugins.utils.abstract_plugin import URLImportResult
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.context_managers import mock_update
from tests.plugins.plugin_validator.validator import Validator


class JustWatchValidator(PluginValidator[JustWatch]):
    plugin_class = JustWatch

    @staticmethod
    def _own_results(results: list[URLImportResult]) -> list[URLImportResult]:
        """Return the results for the shows JustWatch itself owns.

        A title is imported through the plugin of every service that has one, so
        the results also cover shows stored under those plugins. JustWatch has no
        files for them and cannot update them, which leaves the shows it imported
        from its own data as the only ones its tests can use.
        """
        return [
            result
            for result in results
            if result.show.source.plugin.key == JustWatch.plugin_key()
        ]

    @staticmethod
    @override
    def get_random_source(results: list[URLImportResult]) -> Source:
        return PluginValidator.get_random_source(
            JustWatchValidator._own_results(results),
        )

    @staticmethod
    @override
    def get_random_show(results: list[URLImportResult]) -> Show:
        return PluginValidator.get_random_show(JustWatchValidator._own_results(results))

    @staticmethod
    @override
    def get_random_season(results: list[URLImportResult]) -> Season:
        return PluginValidator.get_random_season(
            JustWatchValidator._own_results(results),
        )

    @staticmethod
    @override
    def get_random_episode(results: list[URLImportResult]) -> Episode:
        return PluginValidator.get_random_episode(
            JustWatchValidator._own_results(results),
        )


class JustWatchStandardTests(StandardTests[JustWatch], JustWatchValidator):
    pass


class JustWatchUpdateSourceTest(UpdateSourceTests[JustWatch], JustWatchValidator):
    """Update source tests for JustWatch's own sources and the delegated ones."""

    slug: str

    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # update_source reads the fake new titles file, whose data_timestamp is
        # later than the source's, then schedules the source to be reprocessed
        # once the file's entries are guaranteed to be complete.
        validator = validator.incremented(Source, "update_at")

        # The fake entry announces a season that is not stored, so the show is
        # marked for update at the file's timestamp, which is sooner than the
        # update_at the test seeded.
        validator = validator.incremented(Show, "modified_at")
        return validator.decremented(Show, "update_at")

    @override
    def _create_source_update_entry(
        self,
        plugin_instance: JustWatch,
        source: Source,
        timestamp: datetime,
    ) -> None:
        self._fake_new_titles_file(
            plugin_instance,
            source,
            source.shows[0].key,
            len(source.shows[0].seasons) + 1,
            timestamp,
        )

    @staticmethod
    def _fake_new_titles_file(
        plugin_instance: JustWatch,
        source: Source,
        show_key: str,
        season_number: int,
        timestamp: datetime,
    ) -> None:
        """Point a copy of the source's newest new titles file at the title.

        The file's first entry is repointed at a season the database does not
        have, so processing it marks the title for update, and the result is
        written as a new timestamped file so update_source sees it as pending.
        """
        existing_files = plugin_instance._pending_new_titles_files(source)  # noqa: SLF001
        assert existing_files, (
            f"No new titles file recorded for {source.key}. Re-record the test data."
        )

        parsed = existing_files[-1].parsed()
        page = parsed[0]
        edge = page.data.new_titles.edges[0]
        edge.node.field__typename = "Season"
        # An id no stored season uses, so the show is the record that is marked.
        edge.node.id = "fake-season-id"
        edge.node.content.full_path = f"{show_key}/season-{season_number}"
        page.data.new_titles.edges = [edge]

        new_titles = plugin_instance.new_titles_file(source.key, timestamp)
        new_titles.write(just_scrape().new_titles.model_dump([page]))
        new_titles.database_record.data_timestamp = timestamp

    def test_update_source_marks_external_show(
        self,
        session_with_files: Session,
    ) -> None:
        """Updating a delegated service's source marks that service's own copy.

        Hulu has its own plugin, so JustWatch stores no show for it and only
        keeps a source to watch its new titles feed with. A hit in that feed
        belongs to Hulu's copy of the title, which JustWatch has to mark because
        the copy lives under a plugin that has no feed of its own.
        """
        results = self._import_url(session_with_files)
        plugin_instance = self.imported_plugin

        external_shows = [
            result.show
            for result in results
            if result.show.source.plugin.key != JustWatch.plugin_key()
        ]
        assert external_shows, "No show owned by another plugin was imported."

        # Every service a title is on can have its own plugin, which leaves
        # JustWatch without a show of its own to read the key off of.
        show_key = f"/us/tv-show/{self.slug}"

        # JustWatch has a source for every provider it tracks, but only the ones
        # offering this title on a service with its own plugin say anything about
        # the copies that plugin stores.
        delegated_sources = [
            Source.get_one(session_with_files, plugin_instance.plugin, source_key)
            for source_key, _ in plugin_instance._sources_with_offers(show_key)  # noqa: SLF001
            if plugin_instance._plugin_for_source(show_key, source_key) is not None  # noqa: SLF001
        ]
        assert len(delegated_sources) == len(external_shows)

        timestamp = tz_datetime.now() + timedelta(minutes=1)

        for source in delegated_sources:
            self._fake_new_titles_file(
                plugin_instance,
                source,
                show_key,
                # Only the show the entry belongs to matters here, the season it
                # announces is never looked up.
                1,
                timestamp,
            )
            with mock_update():
                JustWatch(session_with_files).update_source(source=source)

        for external_show in external_shows:
            plugin_key = external_show.source.plugin.key
            assert external_show.update_at == timestamp, (
                f"{plugin_key} show was not marked for update."
            )
            # Updating a show does not always update its seasons, so they are
            # marked separately and may already be due sooner than the entry.
            for season in external_show.active_children:
                assert season.update_at is not None, (
                    f"{plugin_key} season {season.key} was not marked for update."
                )
                assert season.update_at <= timestamp, (
                    f"{plugin_key} season {season.key} is due later than the entry."
                )


class MovieURLs:
    urls: tuple[str, ...] = (
        "/us/movie/{slug}",
        "/us/movie/{slug}/",
    )


class ShowURLs:
    urls: tuple[str, ...] = (
        "/us/tv-show/{slug}",
        "/us/tv-show/{slug}/",
    )


# class TestMovie(MovieURLs, JustWatchStandardTests):
#     # Megamind (2010), streaming on Tubi.
#     slug = "megamind"


# class TestSingleSeasonShow(ShowURLs, JustWatchStandardTests):
#     # Strip Law — a single season, streaming on Netflix.
#     slug = "strip-law"


class TestHuluShow(ShowURLs, JustWatchStandardTests, JustWatchUpdateSourceTest):
    "Tests Hulu source."

    slug = "the-bear"


class TestNetflixShow(ShowURLs, JustWatchStandardTests, JustWatchUpdateSourceTest):
    "Tests Netflix source."

    slug = "basic-versus-baller-travel-at-any-cost"


class InvalidJustWatchValidator(InvalidURLValidator[JustWatch]):
    plugin_class = JustWatch


class TestInvalidMovie(MovieURLs, InvalidJustWatchValidator):
    slug = "invalid-movie-that-does-not-exist"


class TestInvalidShow(ShowURLs, InvalidJustWatchValidator):
    slug = "invalid-show-that-does-not-exist"
