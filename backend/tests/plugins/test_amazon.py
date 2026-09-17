# TODO: Validate
from datetime import UTC, datetime

from plugins.Amazon import Amazon
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
)


# TODO: Validate
class AmazonValidator(PluginValidator[Amazon]):
    plugin_class = Amazon


# TODO: Validate
class TestChannelSubscriptionTitle(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 11, tzinfo=UTC)
    title_key = "B0H8N888NW"
    urls = (
        "/gp/video/detail/{title_key}",
        "/dp/{title_key}",
        "https://www.amazon.com/gp/video/detail/{title_key}"
        "?jic=64%7CCgxsdW5hc3RhbmRhcmQKDHNob3V0ZmFjdG9yeRIMc3Vic2NyaXB0aW9uEgRzdm9k"
        "&ref_=atv_tv_hom_c_8zC58H_awns_5_1",
    )


# TODO: Validate
class TestMovie(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 17, tzinfo=UTC)
    title_key = "0T4FBS1H845HDEYTKZGP4Y4GTQ"
    urls = (
        "/detail/{title_key}",
        "https://www.primevideo.com/detail/{title_key}?_ssoLoop=1",
    )
