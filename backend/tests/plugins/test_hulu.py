# TODO: Validate
import os
from typing import override

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
class TestInitializeChannel(HuluValidatorAlt):
    """Test the channels Hulu's catalogue is read into."""

    initializes_channels = True

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
            Hulu.initialize_plugin(session_with_files)
        finally:
            self._export_files_manifest(session_with_files)

    # TODO: Validate
    def test_initialize_channel(self, session_with_files: Session) -> None:
        """Building the channels leaves the database as it was recorded."""
        with log_stats(self), frozen_clock(self.import_time):
            Hulu.initialize_plugin(session_with_files)
        self.assert_state(session_with_files, "initialize_channel")


# TODO: Validate
class TestMovie(StandardTestsAlt[Hulu], HuluValidatorAlt):
    movie_id = "f15f9043-8d98-4f6f-b993-7bee1d8320ce"
    show_slug = "princess-mononoke"
    urls = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movie/{show_slug}-{movie_id}",
        "/watch/{movie_id}",
    )

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        for variant in self._url_variants():
            self._import_url(session, variant)


# TODO: Validate
class TestSeries(StandardTestsAlt[Hulu], HuluValidatorAlt):
    series_id = "3c3c0f8b-7366-4d15-88ab-18050285978e"
    show_slug = "family-guy"
    urls = (
        "/series/{series_id}",
        "/series/{series_id}/",
        "/series/{show_slug}-{series_id}",
    )


# TODO: Validate
class TestSeriesEpisode(StandardTestsAlt[Hulu], HuluValidatorAlt):
    episode_id = "ac156a83-a17a-445b-a522-1544373fbbf1"
    urls = (
        "/watch/{episode_id}",
        "/watch/{episode_id}/",
    )
