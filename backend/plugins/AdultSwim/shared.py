# TODO: Validate
"""What the plugin, its importers and its initializer all read Adult Swim by."""

from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from plugins.AdultSwim.constants import (
    EPISODE_URL_REGEX,
    FREE,
    SUBSCRIPTION,
    TITLE_URL_REGEX,
)
from plugins.AdultSwim.files import TitlePage, TitlesPage
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pools_closed.show.models import Episode as EpisodeData
    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.channels.models import Channel
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://adultswim.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"videos/{title_key}")


# TODO: Validate
def episode_url(title_key: str, episode_slug: str) -> str:
    return build_url(f"videos/{title_key}/{episode_slug}")


# TODO: Validate
def source_requires_auth(source_key: str) -> bool:
    return source_key == SUBSCRIPTION


# TODO: Validate
def is_clip_season(season: SeasonData) -> bool:
    return season.type == "CLIP"


# TODO: Validate
def season_key(season: SeasonData) -> str:
    if is_clip_season(season):
        return f"clip-{season.number}"
    return str(season.number)


# TODO: Validate
def season_name(season: SeasonData) -> str:
    if is_clip_season(season):
        return f"Clips from Season {season.number}"
    return season.name


# TODO: Validate
def season_keys(title: ShowModel) -> list[str]:
    return [season_key(season) for season in title.seasons]


# TODO: Validate
def episode_keys(title: ShowModel, wanted_season_keys: list[str]) -> list[str]:
    return [
        episode.id
        for season in title.seasons
        if season_key(season) in wanted_season_keys
        for episode in season.episodes
    ]


# TODO: Validate
def source_episodes(season: SeasonData, source_key: str) -> list[EpisodeData]:
    return [
        episode_data
        for episode_data in season.episodes
        if episode_data.auth == source_requires_auth(source_key)
    ]


# TODO: Validate
def episode_air_date(episode: EpisodeData) -> datetime | None:
    air_date = episode.first_airing or episode.launch_date
    if isinstance(air_date, str):
        return datetime.fromisoformat(air_date)
    return air_date


# TODO: Validate
def episode_key_from_slug(title: ShowModel, episode_slug: str) -> str | None:
    for season in title.seasons:
        for episode in season.episodes:
            if episode.slug == episode_slug:
                return episode.id
    return None


# TODO: Validate
class AdultSwimShared(BasePlugin):
    # TODO: Validate
    def title_file(self, title_key: str) -> TitlePage:
        return self._cached_file(TitlePage, title_key)

    # TODO: Validate
    def titles_file(self) -> TitlesPage:
        return self._cached_file(TitlesPage)

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[TitlesPage]:
        return [self.titles_file()]

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[TitlesPage]:
        return [self.titles_file()]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return season_keys(self.title_file(title_key).parsed())

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return episode_keys(self.title_file(title_key).parsed(), season_keys)

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Adult Swim"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.adultswim.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "adultswim.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (FREE, SUBSCRIPTION)

    # TODO: Validate
    def create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel(
            "All Titles",
            self._title_urls_from_plugin_files(),
        )

    # TODO: Validate
    def _title_urls_from_plugin_files(self) -> list[str]:
        return [
            title_url(title_key) for title_key in self._title_keys_from_plugin_files()
        ]

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        return [
            show.slug
            for show in self.titles_file().parsed().shows
            if show.slug is not None
        ]

    # TODO: Validate
    def _channel(self) -> Channel:
        return self.get_or_create_channel(
            self._channel_name("All Titles"),
            self._channel_description("All Titles"),
        )


# TODO: Validate
class AdultSwimImporter(AdultSwimShared, BaseImporter, ABC):
    pass
