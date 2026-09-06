# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from loguru import logger

from app.utils import tz_datetime
from plugins.AdultSwim.media import AdultSwimMedia
from plugins.AdultSwim.shared import (
    EPISODE_URL_REGEX,
    SHOW_URL_REGEX,
    AdultSwimShared,
)
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer
from plugins.utils.base_plugin.search import BaseCatalogueSearchMixin

if TYPE_CHECKING:
    from app.plugins.models import Plugin
    from app.shows.models import Show


# TODO: Validate
class AdultSwimInitializer(BasePluginInitializer, AdultSwimShared):
    # TODO: Validate
    @override
    def _create_source_records(self) -> None:
        super()._create_source_records()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()

    # TODO: Validate
    @override
    def _create_channel_records(self) -> None:
        self._channels()
        self._process_new_shows()


# TODO: Validate
class AdultSwim(
    AdultSwimShared,
    BaseCatalogueSearchMixin,
    BaseReadURL,
    AbstractPlugin,
    register=False,
):
    initializer = AdultSwimInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> AdultSwimMedia:
        return AdultSwimMedia(self)

    # TODO: Validate
    @override
    def update_plugin(self, plugin: Plugin) -> None:
        logger.info("Checking Adult Swim for new shows")
        self.shows_file().download_if_outdated(tz_datetime.now())
        self._process_new_shows()
        self._exclude_subscription_from_free_channel()
        plugin.update_at = tz_datetime.now() + self._next_update_interval()
