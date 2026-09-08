# TODO: Validate
import os
from datetime import UTC, datetime
from typing import override

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from app.channels.models import Channel, ChannelQueue
from plugins.Hulu import Hulu
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
    TMDBLookupTests,
)
from tests.plugins.plugin_validator.log_stats import log_stats


# TODO: Validate
class HuluValidator(PluginValidator[Hulu]):
    plugin_class = Hulu


# TODO: Validate
class TestInitializeChannel(HuluValidator):
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
            session_with_files.flush()
        self.assert_state(session_with_files, "initialize_channel")

        channel_count = session_with_files.exec(
            select(func.count()).select_from(Channel),
        ).one()
        queue_count = session_with_files.exec(
            select(func.count()).select_from(ChannelQueue),
        ).one()
        assert channel_count > 0
        assert queue_count > 0


# TODO: Validate
class TestMovie(StandardTests[Hulu], TMDBLookupTests[Hulu], HuluValidator):
    import_time = datetime(2026, 9, 2, tzinfo=UTC)
    update_time = datetime(2026, 9, 3, tzinfo=UTC)
    movie_id = "34bc6b99-813f-4d5d-bbe7-f3099b45879b"
    title_slug = "the-devil-wears-prada-2"
    urls = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movie/{title_slug}-{movie_id}",
        "/watch/{movie_id}",
    )

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        for variant in self._url_variants():
            self._import_url(session, variant)
        super()._initialize_extra_files(session)


# TODO: Validate
class TestSeries(StandardTests[Hulu], TMDBLookupTests[Hulu], HuluValidator):
    series_id = "7117a15d-128c-4c2b-a5b9-98adfa0f4505"
    title_slug = "chad-powers"
    urls = (
        "/series/{series_id}",
        "/series/{series_id}/",
        "/series/{title_slug}-{series_id}",
    )


# TODO: Validate
class TestSeriesEpisode(StandardTests[Hulu], TMDBLookupTests[Hulu], HuluValidator):
    import_time = datetime(2026, 9, 2, tzinfo=UTC)
    update_time = datetime(2026, 9, 3, tzinfo=UTC)
    episode_id = "c282fbd1-d649-4a69-8733-ad9e52222858"
    urls = (
        "/watch/{episode_id}",
        "/watch/{episode_id}/",
    )
