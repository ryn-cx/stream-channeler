# # TODO: Validate
# import re
# import uuid
# from collections.abc import Callable
# from functools import cache
# from typing import override
# from urllib.parse import urlparse

# from sqlalchemy.orm import joinedload
# from sqlmodel import Session, select

# from app.config import settings
# from app.episodes.models import Episode
# from app.plugins.models import Plugin as PluginModel
# from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
# from app.plugins.plugins.utils.base_plugin import BasePlugin
# from app.seasons.models import Season
# from app.shows.models import Show
# from app.sources.models import Source


# class StreamChanneler(BasePlugin, register=True):
#     _VERSION = "0.0.1"

#     @classmethod
#     @cache
#     @override
#     def domains(cls) -> list[str]:
#         # localhost is added for developement purposes.
#         return ["streamchanneler.com", "localhost"]

#     @classmethod
#     @cache
#     @override
#     def _url_regex(cls) -> str:
#         domain_regex = cls._domain_regex()
#         uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
#         return (
#             domain_regex
#             + r"\/(?P<media_type>plugin|source|show|season|episode)"
#             + rf"\/(?P<media_id>{uuid_pattern})(?:\/|$)"
#         )

#     @override
#     def import_url(self, url: str) -> list[URLImportResult]:
#         match = re.match(self._url_regex(), url)
#         if not match:
#             msg = f"Invalid {self._plugin_name()} URL: {url}"
#             raise InvalidURLError(msg)

#         media_type = match.group("media_type")
#         media_id = uuid.UUID(match.group("media_id"))

#         handlers: dict[str, Callable[[uuid.UUID, str], list[URLImportResult]]] = {
#             "show": self._import_show,
#             "season": self._import_season,
#             "episode": self._import_episode,
#             "source": self._import_source,
#             "plugin": self._import_plugin,
#         }
#         return handlers[media_type](media_id, url)

#     def _import_plugin(
#         self,
#         plugin_id: uuid.UUID,
#         url: str,
#     ) -> list[URLImportResult]:
#         plugin_entity = self.db.exec(
#             select(PluginModel)
#             .where(PluginModel.id == plugin_id)
#             .options(joinedload(PluginModel.sources).joinedload(Source.shows)),
#         ).first()
#         if not plugin_entity:
#             msg = f"Plugin not found: {url}"
#             raise InvalidURLError(msg)
#         return [
#             URLImportResult(show=show, whitelist_mode=False)
#             for source in plugin_entity.sources
#             for show in source.shows
#         ]

#     def _import_source(
#         self,
#         source_id: uuid.UUID,
#         url: str,
#     ) -> list[URLImportResult]:
#         source = self.db.exec(
#             select(Source)
#             .where(Source.id == source_id)
#             .options(
#                 joinedload(Source.shows),  # type: ignore[arg-type]
#             ),
#         ).first()
#         if not source:
#             msg = f"Source not found: {url}"
#             raise InvalidURLError(msg)
#         return [
#             URLImportResult(show=show, whitelist_mode=False) for show in source.shows
#         ]

#     def _import_show(
#         self,
#         show_id: uuid.UUID,
#         url: str,
#     ) -> list[URLImportResult]:
#         show = self.db.exec(select(Show).where(Show.id == show_id)).unique().first()

#         if not show:
#             msg = f"Show not found: {url}"
#             raise InvalidURLError(msg)
#         return [URLImportResult(show=show, whitelist_mode=False)]

#     def _import_season(
#         self,
#         season_id: uuid.UUID,
#         url: str,
#     ) -> list[URLImportResult]:
#         season = self.db.exec(
#             select(Season)
#             .where(Season.id == season_id)
#             .options(joinedload(Season.show)),  # type: ignore[arg-type]
#         ).first()
#         if not season:
#             msg = f"Season not found: {url}"
#             raise InvalidURLError(msg)
#         return [
#             URLImportResult(show=season.show, seasons=[season], whitelist_mode=True),
#         ]

#     def _import_episode(
#         self,
#         episode_id: uuid.UUID,
#         url: str,
#     ) -> list[URLImportResult]:
#         episode = self.db.exec(
#             select(Episode)
#             .where(Episode.id == episode_id)
#             .options(joinedload(Episode.season).joinedload(Season.show)),  # type: ignore[arg-type]
#         ).first()
#         if not episode:
#             msg = f"Episode not found: {url}"
#             raise InvalidURLError(msg)
#         return [
#             URLImportResult(
#                 show=episode.season.show,
#                 episodes=[episode],
#                 whitelist_mode=True,
#             ),
#         ]

#     @override
#     def update_show(self, show: Show) -> None:
#         pass

#     @override
#     def update_season(self, season: Season) -> None:
#         pass

#     @override
#     def update_episode(self, episode: Episode) -> None:
#         pass
