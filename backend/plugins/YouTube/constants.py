# TODO: Validate
from plugins.utils.base_plugin.url import BaseURLMixin

LONG_DOMAIN = "youtube.com"
SHORT_DOMAIN = "youtu.be"
LONG_DOMAIN_REGEX = BaseURLMixin.regex_escape_domain(LONG_DOMAIN)
SHORT_DOMAIN_REGEX = BaseURLMixin.regex_escape_domain(SHORT_DOMAIN)

FREE_SOURCE_KEY = "YouTube Free Movies & Shows"
PAID_SOURCE_KEY = "YouTube Paid Movies & Shows"
LINKS_SOURCE_KEY = "YouTube Links"

# https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
# https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
PLAYLIST_VIDEO_URL_REGEX = (
    rf"(?:{LONG_DOMAIN_REGEX}|{SHORT_DOMAIN_REGEX})"
    r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
    r"list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
)
# https://www.youtube.com/playlist?list=TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw
TITLE_PLAYLIST_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/playlist\?list=(?P<title_playlist_key>TVSH[^&]+)"
)
# https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
PLAYLIST_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
)
# https://www.youtube.com/watch?v=jNQXAC9IVRw
# https://www.youtube.com/shorts/jNQXAC9IVRw
# https://youtu.be/jNQXAC9IVRw
VIDEO_URL_REGEX = (
    rf"(?:{LONG_DOMAIN_REGEX}\/(?:watch\?v=|shorts\/)|{SHORT_DOMAIN_REGEX}\/)"
    r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"
)
# https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
CHANNEL_KEY_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"
)
# https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw
# https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw?season=23&sbp=...
TITLE_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/show\/(?P<title_key>SC[A-Za-z0-9_-]+?)(?:$|[/?])"
)
# https://www.youtube.com/user/jawed
CHANNEL_USERNAME_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/user\/(?P<channel_username>.+?)(?:$|\/)"
)
# https://www.youtube.com/@jawed
# https://www.youtube.com/c/jawed
# https://www.youtube.com/jawed
CHANNEL_HANDLE_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"
)

URL_REGEXES = (
    PLAYLIST_VIDEO_URL_REGEX,  # Must be first due to regex overlap
    TITLE_PLAYLIST_URL_REGEX,
    PLAYLIST_URL_REGEX,
    VIDEO_URL_REGEX,
    CHANNEL_KEY_URL_REGEX,
    TITLE_URL_REGEX,
    CHANNEL_USERNAME_URL_REGEX,
    CHANNEL_HANDLE_URL_REGEX,
)
