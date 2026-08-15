# TODO: Validate
from typing import override

from sqlmodel import Session

from app.utils import tz_datetime
from plugins.YouTube import YouTube
from plugins.YouTube.files import is_show_season_key, is_video_key
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt


# TODO: Validate
def _reads_a_feed(season_key: str) -> bool:
    """Report whether the season's update reads a feed for new videos.

    A season that is a single video, and a season of a show, are re-read from
    the page describing them instead, which is a file the season already has.
    """
    return not (is_video_key(season_key) or is_show_season_key(season_key))


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
