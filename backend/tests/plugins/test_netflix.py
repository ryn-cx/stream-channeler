# TODO: Validate
from datetime import UTC, datetime

from plugins.Netflix import Netflix
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)


# TODO: Validate
class NetflixValidator(PluginValidator[Netflix]):
    plugin_class = Netflix


# TODO: Validate
class TestAiringShow(StandardTests[Netflix], NetflixValidator):
    import_time = datetime(2026, 9, 7, tzinfo=UTC)
    title_key = "82760630"
    urls = (
        "/title/{title_key}",
        "/title/{title_key}/",
    )


# TODO: Validate
class TestLargeTVShow(StandardTests[Netflix], NetflixValidator):
    import_time = datetime(2026, 9, 8, tzinfo=UTC)
    title_key = "80107103"
    urls = ("/title/{title_key}",)


# TODO: Validate
class TestInvalidTitleID(InvalidURLValidator[Netflix], NetflixValidator):
    import_time = datetime(2026, 9, 9, tzinfo=UTC)
    title_key = "99999999"
    urls = ("/title/{title_key}",)
