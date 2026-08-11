# TODO: Validate
from datetime import datetime
from typing import override

from chirashi.browse_music.models import BrowseMusicModel

from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from plugins.Crunchyroll.files import chirashi
from tests.plugins.crunchyroll.validators import (
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTests,
    CrunchyrollValidator,
    crunchyroll_urls,
)


# TODO: Validate
class CrunchyrollArtistValidator(CrunchyrollValidator):
    urls = crunchyroll_urls("artist/{parse_url_response}", "{artist_slug}")


# TODO: Validate
class CrunchyrollMusicUpdateSourceTest(
    CrunchyrollUpdateSourceTests,
    CrunchyrollArtistValidator,
):
    # TODO: Validate
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

    # TODO: Validate
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
        first_entry.id = source.shows[0].key
        first_entry.updated_at = timestamp
        self.export_browse_file(plugin_instance, parsed, timestamp)


# TODO: Validate
class TestArtistWithMusicVideosAndConcerts(
    CrunchyrollStandardTests,
    CrunchyrollMusicUpdateSourceTest,
):
    parse_url_response = "MA179CB50D"
    artist_slug = "LiSA"


# class TestArtistWithOnlyMusicVideos(
#     CrunchyrollMusicStandardTests,
#     CrunchyrollMusicUpdateSourceTest,
# ):
#     parse_url_response = "MA3B4C0F0F"
#     artist_slug = "yoasobi"


# class TestMusicVideo(CrunchyrollMusicStandardTests, CrunchyrollMusicUpdateSourceTest):
#     parse_url_response = "MA899F54A4"
#     artist_slug = "lisa"
#     music_video_key = "MV5CD8B009"
#     music_video_slug = "gurenge"
#     urls = crunchyroll_urls("watch/musicvideo/{music_video_key}", "{music_video_slug}")


# class TestConcert(CrunchyrollMusicStandardTests, CrunchyrollMusicUpdateSourceTest):
#     parse_url_response = "MA899F54A4"
#     artist_slug = "lisa"
#     concert_key = "MC413F1C5C"
#     concert_slug = "lisa-ladybug"
#     urls = crunchyroll_urls("watch/concert/{concert_key}", "{concert_slug}")


# class TestInvalidArtistKey(InvalidCrunchyrollURLValidator):
#     urls = ("crunchyroll.com/artist/MGGGGGGGG",)


# class TestInvalidMusicVideoKey(InvalidCrunchyrollURLValidator):
#     urls = ("crunchyroll.com/watch/musicvideo/MVGGGGGGG",)


# class TestInvalidConcertKey(InvalidCrunchyrollURLValidator):
#     urls = ("crunchyroll.com/watch/concert/MCGGGGGGG",)
