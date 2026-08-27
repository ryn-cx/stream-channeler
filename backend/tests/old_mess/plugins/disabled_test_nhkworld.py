# TODO: Validate
from datetime import datetime
from typing import override

from app.shows.models import Show
from app.sources.models import Source
from plugins.NHKWorld import NHKWorld
from plugins.NHKWorld.files import naphki
from tests.old_mess.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.old_mess.plugins.plugin_validator.validator import Validator


# TODO: Validate
class NHKWorldValidator(PluginValidator[NHKWorld]):
    plugin_class = NHKWorld


# TODO: Validate
class NHKWorldStandardTests(StandardTests[NHKWorld], NHKWorldValidator):
    pass


# TODO: Validate
class NHKWorldUpdateSourceTest(UpdateSourceTests[NHKWorld], NHKWorldValidator):
    # TODO: Validate
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # _upsert_source rewrites update_at = data_timestamp + 1 day off the fake
        # feed file, whose data_timestamp is set to a later value than the original.
        validator.incremented(Source, "update_at")

        # Only the matched show is marked for update; seasons have no update
        # procedure of their own, so they are left untouched. The show's
        # modified_at is bumped and its update_at is decremented because the feed's
        # published_at is mocked to a sooner timestamp than the seeded update_at.
        validator.incremented(Show, "modified_at")
        validator.decremented(Show, "update_at")

        return validator

    # TODO: Validate
    @staticmethod
    def _create_fake_feed_file(
        plugin_instance: NHKWorld,
        timestamp: datetime,
        show_key: str,
    ) -> None:
        """Create a fake new-episodes file pointing its first item at the show.

        The latest new-episodes file is reused as a template, its first item is
        pointed at the show with a recent published_at, and the result is written
        as a new timestamped file so update_source treats it as unprocessed.
        """
        latest_feed = plugin_instance.latest_new_video_episodes_file()
        latest_feed.database_record.extra = "Completed"
        parsed = latest_feed.parsed()
        first_page = parsed[0]
        first_item = first_page.items[0]
        first_item.video_program.id = show_key
        first_item.video.published_at = timestamp
        first_page.items = [first_item]
        parsed = [first_page]
        new_feed = plugin_instance.new_video_episodes_file(timestamp)
        new_feed.write(naphki().video_episodes.model_dump(parsed))  # pyright: ignore[reportPrivateUsage]
        new_feed._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

    # TODO: Validate
    @override
    def _create_source_update_entry(
        self,
        plugin_instance: NHKWorld,
        source: Source,
        timestamp: datetime,
    ) -> None:
        self._create_fake_feed_file(plugin_instance, timestamp, source.shows[0].key)


# TODO: Validate
class TestShow(NHKWorldStandardTests, NHKWorldUpdateSourceTest):
    parse_url_response = "dwc"
    urls = (
        "/nhkworld/en/shows/{parse_url_response}/",
        "/nhkworld/en/shows/{parse_url_response}",
    )


# TODO: Validate
class InvalidNHKWorldURLValidator(InvalidURLValidator[NHKWorld]):
    plugin_class = NHKWorld


# TODO: Validate
class TestInvalidShowKey(InvalidNHKWorldURLValidator):
    # Correctly formatted show URL whose program does not exist.
    urls = ("https://www3.nhk.or.jp/nhkworld/en/shows/zzzzzzzzzz/",)


# TODO: Validate
class TestInvalidURL(InvalidNHKWorldURLValidator):
    # Numeric key is an episode URL, not a show, so the regex rejects it.
    urls = ("https://www3.nhk.or.jp/nhkworld/en/shows/3025240/",)
