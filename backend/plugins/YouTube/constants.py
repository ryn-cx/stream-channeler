# TODO: Validate
from datetime import timedelta

from plugins.utils.base_plugin.url import URLMixin

LONG_DOMAIN = "youtube.com"
SHORT_DOMAIN = "youtu.be"
LONG_DOMAIN_REGEX = URLMixin.regex_escape_domain(LONG_DOMAIN)
SHORT_DOMAIN_REGEX = URLMixin.regex_escape_domain(SHORT_DOMAIN)

FREE_SOURCE_KEY = "YouTube Free Movies & Shows"
PAID_SOURCE_KEY = "YouTube Paid Movies & Shows"
LINKS_SOURCE_KEY = "YouTube Links"

FEED_UPDATE_DELAY = timedelta(hours=1)
