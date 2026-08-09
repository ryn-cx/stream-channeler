# TODO: Validate
from plugins.YouTube import YouTube
from tests.plugins.plugin_validator import StandardTests
from tests.plugins.youtube.validators import YouTubeValidator


class TestVideo(StandardTests[YouTube], YouTubeValidator):
    channel_key = "UC4QobU6STFB0P71PMvOGN5A"
    channel_name = "jawed"
    video_key = "jNQXAC9IVRw"
    urls = (
        f"youtube.com/watch?v={video_key}",
        f"youtube.com/watch?v={video_key}&t=120s",
        f"youtube.com/shorts/{video_key}",
        f"youtu.be/{video_key}",
        f"youtu.be/{video_key}?t=120",
    )
    parse_url_response = ("video_key", video_key)


class TestYouTubeMovie(StandardTests[YouTube], YouTubeValidator):
    """Test importing a movie hosted on YouTube.

    The official YouTube Movies & TV channel truncates every listing it exposes, so
    the video is missing from the channel's uploads and can only be imported as a
    show of its own.
    """

    video_key = "dQB4HJfVj2Q"
    urls = (
        f"youtube.com/watch?v={video_key}",
        f"youtu.be/{video_key}",
    )
    parse_url_response = ("video_key", video_key)


class TestYouTubeShowEpisode(StandardTests[YouTube], YouTubeValidator):
    """Test importing an episode of a show hosted on YouTube.

    The show playlist the URL carries is not a playlist the API can read, so the
    episode is imported as a show of its own the same way a movie is.

    The show playlist is not a `PL` playlist, so even the URL carrying it is
    answered by the video handler rather than the playlist video one.
    """

    video_key = "TEJevNI9WoA"
    show_playlist_key = "TVSHZ4sc4JoEC9IdUMI4DcegnVhNMxEieH11w"
    urls = (
        f"youtube.com/watch?v={video_key}",
        f"youtube.com/watch?v={video_key}&list={show_playlist_key}",
    )
    parse_url_response = ("video_key", video_key)
