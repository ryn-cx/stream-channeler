# TODO: Validate
from plugins.YouTube import YouTube
from tests.old_mess.plugins.plugin_validator import StandardTests
from tests.old_mess.plugins.youtube.validators import YouTubeValidator
from tests.plugins.plugin_validator_v2 import StandardTestsV2, PluginValidatorV2


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
class TestChannelWithVideoInMultiplePlaylists(StandardTests[YouTube], ChannelValidator):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"
