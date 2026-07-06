# TODO: Validate
from sqlmodel import Session

from plugins.YouTube import YouTube
from tests.plugins.plugin_validator import StandardTests
from tests.plugins.youtube.validators import (
    ChannelWithNoUploadsMixin,
    InvalidYouTubeURLValidator,
    YouTubeValidator,
)

# A channel is reachable from any of its identifying prefixes with any tab suffix.
CHANNEL_TAB_SUFFIXES = ("", "/videos", "/featured")


def channel_url_patterns(*prefixes: str) -> tuple[str, ...]:
    return tuple(
        prefix + suffix for prefix in prefixes for suffix in CHANNEL_TAB_SUFFIXES
    )


class ChannelNameValidator(YouTubeValidator):
    """Validate importing a channel by handle or channel id."""

    urls = channel_url_patterns(
        "/@{channel_name}",
        "/channel/{channel_key}",
    )


class UsernameValidator(YouTubeValidator):
    """Validate importing a channel by legacy username."""

    username: str
    urls = channel_url_patterns(
        "/{username}",
        "/c/{username}",
        "/user/{username}",
    )


# It is important that TestChannelByHandle
class TestChannelByHandle(StandardTests[YouTube], ChannelNameValidator):
    """Test importing a channel by handle.

    The channel handle and username must be different to ensure that the values are
    handled correctly.
    """

    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "MrBeast"
    parse_url_response = ("channel_handle", channel_name)

    def test_episode_in_multiple_seasons(self, session_with_url: Session) -> None:
        """Test that episodes that belong to multiple seasons works correctly."""
        results = self._import_url(session_with_url)
        result = results[0]
        show = result.show
        episode_count = 0
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == "jNQXAC9IVRw":
                    episode_count += 1
        assert episode_count == 2  # noqa: PLR2004


class TestChannelByUsername(StandardTests[YouTube], UsernameValidator):
    """Test importing a channel by username.

    The channel handle and username must be different to ensure that the values are
    handled correctly.
    """

    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    username = "MrBeast"
    parse_url_response = ("channel_username", username)


# A channel with no uploads can be imported because the channel may have playlists with
# videos.
class TestChannelWithoutUploads(
    StandardTests[YouTube],
    ChannelWithNoUploadsMixin,
    ChannelNameValidator,
):
    channel_key = "UCJ0cZ4i3wJU5OMVyRH_PxyQ"
    channel_name = "highballrider"
    parse_url_response = ("channel_handle", channel_name)


# A channel with no playlists can be imported because the channel may have uploads.
class TestChannelWithoutPlaylists(StandardTests[YouTube], ChannelNameValidator):
    channel_key = "UCVlx-IvZ_TBWRKU0UQCaueQ"
    channel_name = "chad"
    parse_url_response = ("channel_handle", channel_name)


class TestInvalidChannelName(InvalidYouTubeURLValidator):
    urls = ("youtube.com/@jawed0123456789",)


class TestInvalidChannelId(InvalidYouTubeURLValidator):
    urls = ("youtube.com/channel/UC0123456789ABCDEFGHIJHI",)
