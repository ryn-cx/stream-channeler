# TODO: Validate
from datetime import UTC, datetime

from plugins.DisneyPlus import DisneyPlus
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
)


# TODO: Validate
class DisneyPlusValidator(PluginValidator[DisneyPlus]):
    plugin_class = DisneyPlus
