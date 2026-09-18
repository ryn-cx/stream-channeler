# TODO: Validate
from typing import override

from sqlmodel import Session

from app.utils import tz_datetime
from plugins.YouTube import YouTube
from plugins.YouTube.files import (
    is_an_album,
    is_title_season_key,
    is_video_key,
)
from tests.plugins.plugin_validator import PluginValidator, StandardTests


# TODO: Validate
def _reads_a_feed(season_key: str) -> bool:
    """Report whether the season's update reads a feed for new videos.

    A season that is a single video, and a season of a title, are re-read from
    the page describing them instead, which is a file the season already has.
    """
    return not (
        is_video_key(season_key)
        or is_title_season_key(season_key)
        or is_an_album(season_key)
    )


# TODO: Validate
class YouTubeValidator(PluginValidator[YouTube]):
    """Validate all YouTube content."""

    channel_key: str
    playlist_key: str
    channel_name: str

    plugin_class = YouTube

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        plugin = self.plugin_class(session)
        for source in self.select_plugin_with_children(session).sources:
            for title in source.titles:
                for season in title.seasons:
                    if _reads_a_feed(season.key):
                        plugin.playlist_feed_file(season.key).download_if_outdated(
                            tz_datetime.now(),
                        )


# TODO: Validate
class ChannelValidator(YouTubeValidator):
    urls = (
        "youtube.com/@{channel_name}",
        "youtube.com/channel/{channel_key}",
        # A channel opens on whichever tab it was left on, so a pasted link
        # usually carries one, and every tab is the same channel.
        "youtube.com/@{channel_name}/videos",
        "youtube.com/@{channel_name}/featured",
        "youtube.com/channel/{channel_key}/videos",
        "youtube.com/channel/{channel_key}/featured",
    )


# The channel uploads playlist and the "YouTube" playlist both list "Me at the
# zoo", so the one video is an episode of two seasons.
# TODO: Validate
class TestChannelWithVideoInMultiplePlaylists(
    StandardTests[YouTube],
    ChannelValidator,
):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"


# TODO: Validate
class SystemHubChannelValidator(YouTubeValidator):
    urls = (
        "youtube.com/channel/{channel_key}",
        "youtube.com/channel/{channel_key}/videos",
    )


# TODO: Validate
class TestSystemHubChannel(StandardTests[YouTube], SystemHubChannelValidator):
    channel_key = "UClgRkhTL3_hImCAmdLfDE4g"


# TODO: Validate
class TestMusicSystemHubChannel(
    StandardTests[YouTube],
    SystemHubChannelValidator,
):
    channel_key = "UC-9-kyTW8ZkZNDHQJ6FgpwQ"


# TODO: Validate
class PlaylistValidator(YouTubeValidator):
    urls = ("youtube.com/playlist?list={playlist_key}",)


# TODO: Validate
class TestChannelPlaylist(StandardTests[YouTube], PlaylistValidator):
    playlist_key = "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"


# An album YouTube generated a playlist of, whose tracks went up on the
# musician's own channel rather than on a Topic channel generated for them. A
# channel that is not a Topic lists far more than music, so the release is a
# title of its own instead of a season of the channel that published it.
# TODO: Validate
class TestMusicAlbumPlaylist(StandardTests[YouTube], PlaylistValidator):
    playlist_key = "OLAK5uy_mKcftf5tOvVhq-CsutohYLKrB1l8PqCG8"


# TODO: Validate
class TestTitlePlaylistURL(StandardTests[YouTube], PlaylistValidator):
    playlist_key = "TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw"


# TODO: Validate
class TestChannelUploadsPlaylistURL(
    StandardTests[YouTube],
    PlaylistValidator,
):
    playlist_key = "UU4QobU6STFB0P71PMvOGN5A"


# TODO: Validate
class VideoValidator(YouTubeValidator):
    urls = ("youtube.com/watch?v={video_key}",)


# A title of YouTube's catalogue that has to be bought or rented. Every one of
# them is published on a channel generated for that title alone and named after
# it was published in and nothing else.
# TODO: Validate
class TestPaidMovie(StandardTests[YouTube], VideoValidator):
    video_key = "koInAsdH8WA"


# A title of YouTube's catalogue that is served free with ads. Every one of them
# is owned by the one channel the whole free catalogue is published on, which
# lists almost none of what it owns, so the title is a title of its own.
# TODO: Validate
class TestFreeMovie(StandardTests[YouTube], VideoValidator):
    video_key = "zKQGAv8gtBA"


# TODO: Validate
class TestAnotherPaidMovie(StandardTests[YouTube], VideoValidator):
    video_key = "NdYRsrRptco"


# TODO: Validate
class TitleVideoValidator(YouTubeValidator):
    urls = (
        "youtube.com/watch?v={video_key}",
        "youtube.com/watch?v={video_key}&list={title_playlist_key}&index=2",
    )


# TODO: Validate
class TestPaidTitleVideo(StandardTests[YouTube], TitleVideoValidator):
    video_key = "8zWeHypLPRk"
    title_playlist_key = "TVSHfA9WsdDU4jgSZuc4pG3gHBd3nWnvtjK8A"


# TODO: Validate
class TitleValidator(YouTubeValidator):
    urls = ("youtube.com/show/{title_key}",)


# TODO: Validate
class TestSubscriptionTitle(StandardTests[YouTube], TitleValidator):
    title_key = "SC9aXZwJfzfg0g7pZ6ird15g"


# TODO: Validate
class TestTopicAlbumPlaylist(StandardTests[YouTube], PlaylistValidator):
    playlist_key = "OLAK5uy_kiAyq0iiYYIPvqybBkpxFvNai3lAw3fyU"


# TODO: Validate
class TestVariousArtistsAlbum(StandardTests[YouTube], PlaylistValidator):
    playlist_key = "OLAK5uy_keBDQuR704nX77z1CcmcLhIhYlDJkt35s"


# TODO: Validate
class TopicChannelValidator(YouTubeValidator):
    urls = ("youtube.com/channel/{channel_key}",)


# TODO: Validate
class TestTopicChannel(StandardTests[YouTube], TopicChannelValidator):
    channel_key = "UCvYD4mt2SEikFlX0iJmTKvw"
