# TODO: Validate
from plugins.AdultSwim import AdultSwim
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt


# TODO: Validate
class AdultSwimValidatorAlt(PluginValidatorAlt[AdultSwim]):
    plugin_class = AdultSwim


# TODO: Validate
class TestRickAndMorty(StandardTestsAlt[AdultSwim], AdultSwimValidatorAlt):
    show_id = "rick-and-morty"
    urls = (
        "https://www.adultswim.com/{show_id}",
        "/{show_id}",
        "/videos/{show_id}",
        "/videos/{show_id}/",
    )
