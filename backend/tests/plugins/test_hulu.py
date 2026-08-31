# TODO: Validate
import os

import pytest
from sqlmodel import Session

from plugins.Hulu import Hulu
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt
from tests.plugins.plugin_validator_alt.log_stats import log_stats


# TODO: Validate
class HuluValidatorAlt(PluginValidatorAlt[Hulu]):
    plugin_class = Hulu


# TODO: Validate
class TestPrincessMononoke(StandardTestsAlt[Hulu], HuluValidatorAlt):
    """Test a movie."""

    movie_id = "f15f9043-8d98-4f6f-b993-7bee1d8320ce"
    show_slug = "princess-mononoke"
    urls = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movie/{show_slug}-{movie_id}",
    )


# TODO: Validate
class TestInitializeChannel(HuluValidatorAlt):
    """Test the channels Hulu's catalogue is read into."""

    # TODO: Validate
    @pytest.mark.enable_socket
    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Records/refreshes test data locally; never runs on CI.",
    )
    def test__initialize_test_data(self, session_with_files: Session) -> None:
        """Download and store the genre pages this test class reads.

        Left on the real clock, like the validator's own, because what it stores
        is shared with every test that reaches for the same file and a file
        dated by a frozen clock would say it was downloaded on a day it was not.
        """
        try:
            Hulu.initialize_db(session_with_files)
        finally:
            self._export_files_manifest(session_with_files)

    # TODO: Validate
    def test_initialize_channel(self, session_with_files: Session) -> None:
        """Building the channels leaves the database as it was recorded."""
        with log_stats(self), frozen_clock(self.import_time):
            Hulu.initialize_db(session_with_files)
        self.assert_state(session_with_files, "initialize_channel")
