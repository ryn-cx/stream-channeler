# TODO: Validate
from datetime import UTC, datetime

from plugins.NHKWorld import NHKWorld
from tests.plugins.plugin_validator import PluginValidator, StandardTests


# TODO: Validate
class NHKWorldValidator(PluginValidator[NHKWorld]):
    plugin_class = NHKWorld


# TODO: Validate
class TestSeries(StandardTests[NHKWorld], NHKWorldValidator):
    import_time = datetime(2026, 9, 15, tzinfo=UTC)
    title_key = "dwc"
    urls = ("/nhkworld/en/shows/{title_key}", "/nhkworld/en/shows/{title_key}/")
