# TODO: Validate
from sqlmodel import Session

from plugins.YouTube import YouTube
from tests.old_mess.plugins.plugin_validator import StandardTests
from tests.old_mess.plugins.youtube.validators import (
    ChannelWithNoUploadsMixin,
    InvalidYouTubeURLValidator,
    YouTubeValidator,
)


# TODO: Validate
def channel_url_patterns(*prefixes: str) -> tuple[str, ...]:
    return tuple(
        "youtube.com" + prefix + suffix
        for prefix in prefixes
        for suffix in ("", "/videos", "/featured")
    )


# TODO: Validate
class ChannelNameValidator(YouTubeValidator):
    """Validate importing a channel by handle or channel id."""

    # A handle and a channel id are answered by a handler each, so the family is
    # what the URLs have in common.
    urls = channel_url_patterns(
        "/@{channel_name}",
        "/channel/{channel_key}",
    )


# TODO: Validate
class UsernameValidator(YouTubeValidator):
    """Validate importing a channel by username."""

    username: str
    # Only `/user/` reaches the username handler; the other two are handles.
    urls = channel_url_patterns(
        "/{username}",
        "/c/{username}",
        "/user/{username}",
    )


# TODO: Validate
class TestChannelWithVideoInMultiplePlaylists(
    StandardTests[YouTube],
    ChannelNameValidator,
):
    """Test a channel where the same video belongs to multiple playlists.

    "Me at the zoo" is in the channel uploads playlist and the "YouTube" playlist.
    """

    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"
    parse_url_response = ("channel_handle", channel_name)

    # TODO: Validate
    def test_episode_in_multiple_seasons(self, session_with_files: Session) -> None:
        """Test that episodes that belong to multiple seasons works correctly."""
        results = self._import_url(session_with_files)
        show = self.imported_shows(session_with_files, results)[0]
        episode_count = 0
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == "jNQXAC9IVRw":
                    episode_count += 1
        assert episode_count == 2  # noqa: PLR2004


# # It is important that TestChannelByHandle
# # TODO: Validate
# class TestChannelByHandle(StandardTests[YouTube], ChannelNameValidator):
#     """Test importing a channel by handle.

#     The channel handle and username must be different to ensure that the values are
#     handled correctly.
#     """

#     channel_key = "UCX6OQ3DkcsbYNE6H8uQQuVA"
#     channel_name = "MrBeast"
#     parse_url_response = ("channel_handle", channel_name)


# # Caused a crash.
# # TODO: Validate
# class TestVideoWith0x00CharacterInDescription(
#     StandardTests[YouTube],
#     ChannelNameValidator,
# ):
#     channel_key = "UCX6OQ3DkcsbYNE6H8uQQuVA"
#     channel_name = "PhotoLukeHawaii"
#     parse_url_response = ("channel_handle", channel_name)


# # TODO: Validate
# class TestChannelByUsername(StandardTests[YouTube], UsernameValidator):
#     """Test importing a channel by username.

#     The channel handle and username must be different to ensure that the values are
#     handled correctly.
#     """

#     channel_key = "UC4QobU6STFB0P71PMvOGN5A"
#     username = "MrBeast"
#     parse_url_response = ("channel_username", username)


# # A channel with no uploads can be imported because the channel may have playlists with
# # videos.
# # TODO: Validate
# class TestChannelWithoutUploads(
#     StandardTests[YouTube],
#     ChannelWithNoUploadsMixin,
#     ChannelNameValidator,
# ):
#     channel_key = "UCJ0cZ4i3wJU5OMVyRH_PxyQ"
#     channel_name = "highballrider"
#     parse_url_response = ("channel_handle", channel_name)


# # A channel with no playlists can be imported because the channel may have uploads.
# # TODO: Validate
# class TestChannelWithoutPlaylists(StandardTests[YouTube], ChannelNameValidator):
#     channel_key = "UCVlx-IvZ_TBWRKU0UQCaueQ"
#     channel_name = "chad"
#     parse_url_response = ("channel_handle", channel_name)


# # The official YouTube Movies & TV channel truncates every listing it exposes, so
# # importing the channel would import almost none of the videos it owns. Its videos are
# # imported one at a time instead, as shows of their own.
# # TODO: Validate
# class TestStandaloneVideoChannel(InvalidYouTubeURLValidator):
#     channel_key = "UCuVPpxrm2VAgpH3Ktln4HXg"
#     urls = (
#         f"youtube.com/channel/{channel_key}",
#         f"youtube.com/channel/{channel_key}/videos",
#     )


# # TODO: Validate
# class TestInvalidChannelName(InvalidYouTubeURLValidator):
#     urls = ("youtube.com/@jawed0123456789",)


# # TODO: Validate
# class TestInvalidChannelId(InvalidYouTubeURLValidator):
#     urls = ("youtube.com/channel/UC0123456789ABCDEFGHIJHI",)
