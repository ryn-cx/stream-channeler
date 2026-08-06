# TODO: Validate
from typing import override

from app.models import Visibility
from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.models import User
from plugins.TMDB.files import FileMixin
from plugins.TMDB.helpers import HelperMixin
from plugins.TMDB.import_url import ImportURLMixin
from plugins.TMDB.link import LinkMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.upsert import UpsertMixin


class TMDB(
    UpsertMixin,
    LinkMixin,
    SearchMixin,
    ImportURLMixin,
    HelperMixin,
    FileMixin,
    register=True,
):
    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.themoviedb.org/favicon.ico"

    @override
    def _upsert_plugin(
        self,
        plugin_user: User,
        existing_plugin: Plugin | None,
    ) -> Plugin:
        """Create the `Plugin` record as private.

        Nothing here is streamable, so its media only ever exists to stand in for
        what another plugin's website leaves out and is never browsed directly.
        """
        return Plugin(
            key=self.plugin_key(),
            name=self.plugin_name(),
            version=self._VERSION,
            visibility=Visibility.private,
            anonymous=False,
            user_id=plugin_user.id,
        ).upsert_and_set_update_at(plugin_user, existing_plugin)

    @override
    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
