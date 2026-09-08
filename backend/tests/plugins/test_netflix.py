# TODO: Validate
from datetime import UTC, datetime

from plugins.Netflix import Netflix
from tests.plugins.plugin_validator import PluginValidator, StandardTests


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
