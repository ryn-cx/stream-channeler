# TODO: Validate
from plugins.Netflix import Netflix
from tests.plugins.plugin_validator import PluginValidator, StandardTests


# TODO: Validate
class NetflixValidator(PluginValidator[Netflix]):
    plugin_class = Netflix


# TODO: Validate
class TestDrStone(StandardTests[Netflix], NetflixValidator):
    """Test a title with more than 10 episodes in a season."""

    title_id = "81046193"
    urls = (
        "/title/{title_id}",
        "/title/{title_id}/",
    )
