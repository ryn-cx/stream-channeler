# TODO: Validate
from plugins.NHKWorld import NHKWorld
from tests.plugins.plugin_validator_alt import InvalidURLValidatorAlt


# TODO: Validate
class TestJapanRailwayJournalEpisode(InvalidURLValidatorAlt[NHKWorld]):
    """Test a single episode URL, which the plugin does not support yet."""

    plugin_class = NHKWorld
    episode_id = "2049178"
    urls = (
        "/nhkworld/en/shows/{episode_id}/",
        "/nhkworld/en/shows/{episode_id}",
    )
