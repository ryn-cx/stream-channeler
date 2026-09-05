# TODO: Validate
from plugins.utils.base_plugin_v3.url import BaseURLMixin

LONG_DOMAIN = "youtube.com"
SHORT_DOMAIN = "youtu.be"
LONG_DOMAIN_REGEX = BaseURLMixin.regex_escape_domain(LONG_DOMAIN)
SHORT_DOMAIN_REGEX = BaseURLMixin.regex_escape_domain(SHORT_DOMAIN)

FREE_SOURCE_KEY = "YouTube Free Movies & Shows"
PAID_SOURCE_KEY = "YouTube Paid Movies & Shows"
LINKS_SOURCE_KEY = "YouTube Links"
