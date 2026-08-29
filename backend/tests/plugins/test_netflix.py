# TODO: Validate
from plugins.Netflix import Netflix
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt


# TODO: Validate
class NetflixValidatorAlt(PluginValidatorAlt[Netflix]):
    plugin_class = Netflix


# TODO: Validate
class TestDrStone(StandardTestsAlt[Netflix], NetflixValidatorAlt):
    """Test a show with more than 10 episodes in a season."""

    show_id = "81046193"
    urls = (
        "/title/{show_id}",
        "/title/{show_id}/",
    )
