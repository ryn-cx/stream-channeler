# TODO: Validate
from plugins.YouTube import YouTube
from plugins.YouTube.handlers import PlaylistURLHandler, PlaylistVideoURLHandler
from tests.plugins.plugin_validator import StandardTests
from tests.plugins.youtube.validators import (
    ChannelWithNoUploadsMixin,
    InvalidYouTubeURLValidator,
    YouTubeValidator,
)


class PlaylistValidator(YouTubeValidator):
    """Validate importing a playlist."""

    url_handler = PlaylistURLHandler
    urls = ("youtube.com/playlist?list={playlist_key}",)


class PlaylistVideoValidator(YouTubeValidator):
    """Validate importing a specific video from a playlist."""

    video_key: str
    url_handler = PlaylistVideoURLHandler
    urls = ("/watch?v={video_key}&list={playlist_key}",)


# This also ends up having a playlist with no videos PL2666A74DC50B1A76
class Test16CharacterPlaylist(StandardTests[YouTube], PlaylistValidator):
    """Test importing a playlist with a 16-character key."""

    channel_key = "UCeAS7YuMOKpz39PD07O2p_w"
    playlist_key = "PL374F6CD60916C2C7"
    parse_url_response = ("playlist_key", playlist_key)


class Test32CharacterPlaylist(StandardTests[YouTube], PlaylistValidator):
    """Test importing a playlist with a 32-character key."""

    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    playlist_key = "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"
    parse_url_response = ("playlist_key", playlist_key)


# This also ends up having a playlist with no videos PL2666A74DC50B1A76
class TestEmptyPlaylist(StandardTests[YouTube], PlaylistValidator):
    """Test importing an empty playlist.

    This playlist actually includes 3 videos but all of them are unavailable and the
    information is unable to be imported because the videos were probably deleted.
    """

    channel_key = "UCeAS7YuMOKpz39PD07O2p_w"
    playlist_key = "PL01C74EA6ED98D824"
    parse_url_response = ("playlist_key", playlist_key)


class TestPlaylistWithUnavailableVideos(
    StandardTests[YouTube],
    ChannelWithNoUploadsMixin,
    PlaylistValidator,
):
    """Test importing a playlist with unavailable videos.

    This playlist includes a link to https://www.youtube.com/watch?v=-3retI0ugF4 which
    is geo restricted in the USA, but its information is still available and imported.
    """

    channel_key = "UCJ0cZ4i3wJU5OMVyRH_PxyQ"
    playlist_key = "PL1cA0ECqV9x-mC2Pxon9_YNDuM5PdyhyH"
    parse_url_response = ("playlist_key", playlist_key)


# class TestAlbumWithChannel(StandardTests[YouTube], PlaylistValidator):
#     """Test importing an album that is associated with a channel."""

#     playlist_key = "OLAK5uy_lfFeKLvDqhTQwmfolUjDBfbyrjjgdmYcE"
#     channel_key = "UCo1DYcm1IZ9v3UPkpiAcgtg"
#     parse_url_response = ("playlist_key", playlist_key)


class TestAlbumBelongingToTopic(StandardTests[YouTube], PlaylistValidator):
    """Test importing the CHROMAKOPIA album playlist."""

    playlist_key = "OLAK5uy_nt1Nw4wT6I7VlzNknxTiIz3hfED0ttO8Q"
    channel_key = "UCo1DYcm1IZ9v3UPkpiAcgtg"
    parse_url_response = ("playlist_key", playlist_key)


# # TODO: Find an album without a channel (only a topic page)
# class TestAlbumWithoutChannel(StandardTests[YouTube], PlaylistValidator):
#     channel_key = "UC3lBXcrKFnFAFkfVk5WuKcQ"
#     playlist_key = "PLjB_8hSS2lEPSOivtbvDDugFuCeqC4_xm"
#     parse_url_response = ("playlist_key", playlist_key)


class TestPlaylistVideo(StandardTests[YouTube], PlaylistVideoValidator):
    """Test importing a specific video from a playlist."""

    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    playlist_key = "PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh"
    video_key = "XAJEXUNmP5M"
    parse_url_response = ("playlist_video_key", playlist_key)


class TestInvalidPlaylist(InvalidYouTubeURLValidator):
    urls = ("youtube.com/playlist?list=PL0123456789ABCDEF",)
