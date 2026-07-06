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
