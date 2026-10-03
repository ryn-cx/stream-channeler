# TODO: Validate
import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from app.channels.models import Channel, ChannelQueue
from plugins.AdultSwim import AdultSwim
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator import PluginValidator, StandardTests
from tests.plugins.plugin_validator.log_stats import log_stats


# TODO: Validate
class AdultSwimValidator(PluginValidator[AdultSwim]):
    plugin_class = AdultSwim


# TODO: Validate
class TestInitializeChannel(AdultSwimValidator):
    initializes_channels = True

    # TODO: Validate
    @pytest.mark.enable_socket
    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Records/refreshes test data locally; never runs on CI.",
    )
    def test__initialize_test_data(self, session_with_files: Session) -> None:
        try:
            AdultSwim.initialize_plugin(session_with_files)
        finally:
            self._export_files_manifest(session_with_files)
            self._export_files(session_with_files)

    # TODO: Validate
    def test_initialize_channel(self, session_with_files: Session) -> None:
        with log_stats(self), frozen_clock(self.import_time):
            AdultSwim.initialize_plugin(session_with_files)
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
class TestSeries(StandardTests[AdultSwim], AdultSwimValidator):
    import_time = datetime(2026, 9, 9, tzinfo=UTC)
    title_key = "rick-and-morty"
    urls = (
        "/videos/{title_key}",
        "/videos/{title_key}/",
    )


# TODO: Validate
class TestAiringShow(StandardTests[AdultSwim], AdultSwimValidator):
    import_time = datetime(2026, 9, 9, tzinfo=UTC)
    title_key = "president-curtis"
    urls = (
        "/videos/{title_key}",
        "/videos/{title_key}/",
    )


# TODO: Validate
class TestCollectionShow(StandardTests[AdultSwim], AdultSwimValidator):
    import_time = datetime(2026, 9, 9, tzinfo=UTC)
    title_key = "toonami"
    urls = (
        "/videos/{title_key}",
        "/videos/{title_key}/",
    )
