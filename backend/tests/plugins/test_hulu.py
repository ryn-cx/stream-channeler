# TODO: Validate
from plugins.Hulu import Hulu
from tests.plugins.plugin_validator_v2 import PluginValidatorV2, StandardTestsV2


# TODO: Validate
class HuluValidatorV2(PluginValidatorV2[Hulu]):
    plugin_class = Hulu


# TODO: Validate
class TestPrincessMononoke(StandardTestsV2[Hulu], HuluValidatorV2):
    """Test a movie."""

    movie_id = "f15f9043-8d98-4f6f-b993-7bee1d8320ce"
    show_slug = "princess-mononoke"
    urls = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movie/{show_slug}-{movie_id}",
    )
