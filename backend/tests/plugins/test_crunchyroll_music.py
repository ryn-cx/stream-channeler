# TODO: Validate
from datetime import datetime
from typing import override

from chirashi.browse_music.models import BrowseMusicModel

from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from plugins.Crunchyroll.files import chirashi
from plugins.Crunchyroll.music_keys import parse_artist_show_key
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.validator import Validator


class BaseCrunchyrollMusicValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/artist/{parse_url_response}/{artist_slug}",
        "/artist/{parse_url_response}/",
        "/artist/{parse_url_response}",
    )


class CrunchyrollMusicStandardTests(
    StandardTests[Crunchyroll],
    BaseCrunchyrollMusicValidator,
):
    pass


class CrunchyrollMusicUpdateSourceTest(
    UpdateSourceTests[Crunchyroll],
    BaseCrunchyrollMusicValidator,
):
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # Source.update will mock download a new BrowseMusic file, this file will
        # then be used to set Source.data_timestamp, then Source.update_at will
        # be set to a month after Source.data_timestamp.
        validator = validator.incremented(Source, "update_at")

        # Source.update will mock download a new BrowseMusic that includes a mock
        # new entry for the artist. An artist carries no per-category timestamp,
        # so the show and both of its category seasons are marked.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # The existing seasons may or may not already have an update_at value.
        return validator.populated_or_decremented(Season, "update_at")

    def export_browse_file(
        self,
        plugin_instance: Crunchyroll,
        parsed: list[BrowseMusicModel],
        timestamp: datetime,
    ) -> None:
        new_browse = plugin_instance.browse_music_file(timestamp)
        dumped = chirashi().browse_music.model_dump(parsed)
        new_browse.write(dumped)
        new_browse.database_record.data_timestamp = timestamp

    @override
    def _create_source_update_entry(
        self,
        plugin_instance: Crunchyroll,
        source: Source,
        timestamp: datetime,
    ) -> None:
        existing_browse = plugin_instance.find_newest_music_browse_file()
        assert existing_browse, "The music source is created with a browse file"
        parsed = existing_browse.parsed()
        first_entry = parsed[0].data[0]
        first_entry.id = parse_artist_show_key(source.shows[0].key)
        first_entry.updated_at = timestamp
        self.export_browse_file(plugin_instance, parsed, timestamp)


class TestArtistWithMusicVideosAndConcerts(
    CrunchyrollMusicStandardTests,
    CrunchyrollMusicUpdateSourceTest,
):
    parse_url_response = "MA899F54A4"
    artist_slug = "lisa"


class TestArtistWithOnlyMusicVideos(
    CrunchyrollMusicStandardTests,
    CrunchyrollMusicUpdateSourceTest,
):
    parse_url_response = "MA3B4C0F0F"
    artist_slug = "yoasobi"


class TestMusicVideo(CrunchyrollMusicStandardTests, CrunchyrollMusicUpdateSourceTest):
    parse_url_response = "MA899F54A4"
    artist_slug = "lisa"
    music_video_key = "MV5CD8B009"
    music_video_slug = "gurenge"
    urls = (
        "/watch/musicvideo/{music_video_key}",
        "/watch/musicvideo/{music_video_key}/",
        "/watch/musicvideo/{music_video_key}/{music_video_slug}",
    )


class TestConcert(CrunchyrollMusicStandardTests, CrunchyrollMusicUpdateSourceTest):
    parse_url_response = "MA899F54A4"
    artist_slug = "lisa"
    concert_key = "MC413F1C5C"
    concert_slug = "lisa-ladybug"
    urls = (
        "/watch/concert/{concert_key}",
        "/watch/concert/{concert_key}/",
        "/watch/concert/{concert_key}/{concert_slug}",
    )


class InvalidCrunchyrollMusicURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll


class TestInvalidArtistKey(InvalidCrunchyrollMusicURLValidator):
    urls = ("crunchyroll.com/artist/MGGGGGGGG",)


class TestInvalidMusicVideoKey(InvalidCrunchyrollMusicURLValidator):
    urls = ("crunchyroll.com/watch/musicvideo/MVGGGGGGG",)


class TestInvalidConcertKey(InvalidCrunchyrollMusicURLValidator):
    urls = ("crunchyroll.com/watch/concert/MCGGGGGGG",)
