# TODO: Validate
from typing import override

from sqlmodel import Session

from app.utils import tz_datetime
from plugins.YouTube import YouTube
from plugins.YouTube.files import (
    is_an_album,
    is_show_season_key,
    is_video_key,
)
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt


# TODO: Validate
def _reads_a_feed(season_key: str) -> bool:
    """Report whether the season's update reads a feed for new videos.

    A season that is a single video, and a season of a show, are re-read from
    the page describing them instead, which is a file the season already has.
    """
    return not (
        is_video_key(season_key)
        or is_show_season_key(season_key)
        or is_an_album(season_key)
    )


# TODO: Validate
class YouTubeValidatorAlt(PluginValidatorAlt[YouTube]):
    """Validate all YouTube content."""

    channel_key: str
    playlist_key: str
    channel_name: str

    plugin_class = YouTube

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        """Store the feed each season's update reads for new videos.

        Nothing asks for it while a URL is being imported, so it is the one file
        an update needs that recording the import does not leave behind.
        """
        plugin = self.plugin_class(session)
        for source in self.select_plugin_with_children(session).sources:
            for show in source.shows:
                for season in show.seasons:
                    if _reads_a_feed(season.key):
                        plugin.playlist_feed_file(season.key).download_if_outdated(
                            tz_datetime.now(),
                        )


# TODO: Validate
class ChannelValidatorAlt(YouTubeValidatorAlt):
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
    StandardTestsAlt[YouTube],
    ChannelValidatorAlt,
):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"


# TODO: Validate
class SystemHubChannelValidatorAlt(YouTubeValidatorAlt):
    urls = (
        "youtube.com/channel/{channel_key}",
        "youtube.com/channel/{channel_key}/videos",
    )


# TODO: Validate
class TestSystemHubChannel(StandardTestsAlt[YouTube], SystemHubChannelValidatorAlt):
    channel_key = "UClgRkhTL3_hImCAmdLfDE4g"


# TODO: Validate
class TestMusicSystemHubChannel(
    StandardTestsAlt[YouTube],
    SystemHubChannelValidatorAlt,
):
    channel_key = "UC-9-kyTW8ZkZNDHQJ6FgpwQ"


# TODO: Validate
class PlaylistValidatorAlt(YouTubeValidatorAlt):
    urls = ("youtube.com/playlist?list={playlist_key}",)


# A playlist a channel made, which is a season of that channel rather than a
# listing of its own. This is the same playlist the channel test reaches through
# the channel, asked for the other way around.
# TODO: Validate
class TestChannelPlaylist(StandardTestsAlt[YouTube], PlaylistValidatorAlt):
    playlist_key = "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"


# An album YouTube generated a playlist of, whose tracks went up on the
# musician's own channel rather than on a Topic channel generated for them. A
# channel that is not a Topic lists far more than music, so the release is a
# show of its own instead of a season of the channel that published it.
# TODO: Validate
class TestMusicAlbumPlaylist(StandardTestsAlt[YouTube], PlaylistValidatorAlt):
    playlist_key = "OLAK5uy_mKcftf5tOvVhq-CsutohYLKrB1l8PqCG8"


# The playlist a show is published as, which is what browse lists a show under
# and is not the key the show's page is served at, so the URL names the show only
# by way of the listing it asks for.
# TODO: Validate
class TestShowPlaylistURL(StandardTestsAlt[YouTube], PlaylistValidatorAlt):
    playlist_key = "TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw"


# A channel's uploads playlist, which is a season of that channel rather than a
# listing of its own, so the URL is the channel's asked for the long way around.
# TODO: Validate
class TestChannelUploadsPlaylistURL(
    StandardTestsAlt[YouTube],
    PlaylistValidatorAlt,
):
    playlist_key = "UU4QobU6STFB0P71PMvOGN5A"


# TODO: Validate
class VideoValidatorAlt(YouTubeValidatorAlt):
    urls = ("youtube.com/watch?v={video_key}",)


# A title of YouTube's catalogue that has to be bought or rented. Every one of
# them is published on a channel generated for that title alone and named after
# the catalogue rather than after the title, holding the title once per language
# it was published in and nothing else.
# TODO: Validate
class TestPaidMovie(StandardTestsAlt[YouTube], VideoValidatorAlt):
    video_key = "koInAsdH8WA"


# A title of YouTube's catalogue that is served free with ads. Every one of them
# is owned by the one channel the whole free catalogue is published on, which
# lists almost none of what it owns, so the title is a show of its own.
# TODO: Validate
class TestFreeMovie(StandardTestsAlt[YouTube], VideoValidatorAlt):
    video_key = "zKQGAv8gtBA"


# TODO: Validate
class TestAnotherPaidMovie(StandardTestsAlt[YouTube], VideoValidatorAlt):
    video_key = "NdYRsrRptco"


# TODO: Validate
class ShowVideoValidatorAlt(YouTubeValidatorAlt):
    urls = (
        "youtube.com/watch?v={video_key}",
        "youtube.com/watch?v={video_key}&list={show_playlist_key}&index=2",
    )


# TODO: Validate
class TestPaidShowVideo(StandardTestsAlt[YouTube], ShowVideoValidatorAlt):
    video_key = "8zWeHypLPRk"
    show_playlist_key = "TVSHfA9WsdDU4jgSZuc4pG3gHBd3nWnvtjK8A"


# TODO: Validate
class ShowValidatorAlt(YouTubeValidatorAlt):
    urls = ("youtube.com/show/{show_key}",)


# TODO: Validate
class TestSubscriptionShow(StandardTestsAlt[YouTube], ShowValidatorAlt):
    show_key = "SC9aXZwJfzfg0g7pZ6ird15g"


# TODO: Validate
class TestTopicAlbumPlaylist(StandardTestsAlt[YouTube], PlaylistValidatorAlt):
    playlist_key = "OLAK5uy_kiAyq0iiYYIPvqybBkpxFvNai3lAw3fyU"


# TODO: Validate
class TestVariousArtistsAlbum(StandardTestsAlt[YouTube], PlaylistValidatorAlt):
    playlist_key = "OLAK5uy_keBDQuR704nX77z1CcmcLhIhYlDJkt35s"


# TODO: Validate
class TopicChannelValidatorAlt(YouTubeValidatorAlt):
    urls = ("youtube.com/channel/{channel_key}",)


# TODO: Validate
class TestTopicChannel(StandardTestsAlt[YouTube], TopicChannelValidatorAlt):
    channel_key = "UCvYD4mt2SEikFlX0iJmTKvw"
