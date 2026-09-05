# TODO: Validate
from plugins.AdultSwim import AdultSwim
from tests.plugins.plugin_validator import PluginValidator, StandardTests


# TODO: Validate
class AdultSwimValidator(PluginValidator[AdultSwim]):
    plugin_class = AdultSwim


# TODO: Validate
class TestRickAndMorty(StandardTests[AdultSwim], AdultSwimValidator):
    show_id = "rick-and-morty"
    urls = (
        "https://www.adultswim.com/{show_id}",
        "/{show_id}",
        "/videos/{show_id}",
        "/videos/{show_id}/",
    )
