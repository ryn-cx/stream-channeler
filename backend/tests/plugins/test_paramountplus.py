# TODO: Validate
from datetime import UTC, datetime

from plugins.ParamountPlus import ParamountPlus
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
)


# TODO: Validate
class ParamountPlusValidator(PluginValidator[ParamountPlus]):
    plugin_class = ParamountPlus


# TODO: Validate
class TestSeriesWithSections(StandardTests[ParamountPlus], ParamountPlusValidator):
    import_time = datetime(2026, 9, 16, tzinfo=UTC)
    title_key = "star-trek-strange-new-worlds"
    urls = ("/shows/{title_key}/",)
