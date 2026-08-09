"""Crunchyroll URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Crunchyroll.music_keys import (
    MusicCategory,
    artist_show_key,
    music_episode_key,
)
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.shows.models import Show
    from plugins.Crunchyroll import Crunchyroll


def _build_crunchyroll_url_regex(*path: str, group: str) -> str:
    """Return the regex for a Crunchyroll url."""
    return (
        "(?x:"
        # The sometimes present local prefix like de, pt-br, etc.
        r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"
        # The media type identifier, series, watch, artist, etc.
        + "".join(rf"\/{segment}" for segment in path)
        # The Crunchyroll key.
        + rf"\/(?P<{group}>[A-Z0-9]{{9,}})"
        # The URL suffix, usually a slug but other options are also valid.
        r"(?:[\/?#]|$)"
        ")"
    )


class _CrunchyrollURLHandler(URLHandler["Crunchyroll"]):
    @override
    def __init__(self, plugin: Crunchyroll, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class CrunchyrollSeriesURLHandler(_CrunchyrollURLHandler):
    """Crunchyroll series URL handler.

    Example URL https://www.crunchyroll.com/series/GEXH3W29Z
    """

    _URL_REGEX = _build_crunchyroll_url_regex("series", group="show_key")

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def raise_if_invalid(self) -> None:
        plugin_file = self.plugin.series_file(self._key)
        self.plugin.raise_if_invalid_file(plugin_file, self.url)


class CrunchyrollEpisodeURLHandler(_CrunchyrollURLHandler):
    """Crunchyroll episode URL handler.

    Example URL https://www.crunchyroll.com/watch/GVWU8XW1Z
    """

    _URL_REGEX = _build_crunchyroll_url_regex("watch", group="episode_key")

    @property
    @override
    def show_key(self) -> str:
        objects_file = self.plugin.objects_file(self._key)
        return objects_file.parsed().data[0].episode_metadata.series_id

    @override
    def raise_if_invalid(self) -> None:
        objects_file = self.plugin.objects_file(self._key)
        self.plugin.raise_if_invalid_file(objects_file, self.url)

        # TODO: Is it true the api always returns the original region in the current
        # setup?
        # Episodes for different regions have different keys. The show is always
        # imported for the original region so the episode key also needs to match.
        for version in objects_file.parsed().data[0].episode_metadata.versions:
            if version.original:
                self._key = version.guid
                break

        original_file = self.plugin.objects_file(self._key)
        self.plugin.raise_if_invalid_file(original_file, self.url)

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return [
            URLImportResult.for_episodes(show, [self._get_matching_episode(show)]),
        ]

    def _get_matching_episode(self, show: Show) -> Episode:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._key:
                    return episode

        msg = f"Episode {self._key} not found in show {show.key}"
        raise InvalidURLError(msg)


class CrunchyrollArtistURLHandler(_CrunchyrollURLHandler):
    """Crunchyroll artist URL handler.

    Example URL https://www.crunchyroll.com/artist/MA899F54A4
    """

    _URL_REGEX = _build_crunchyroll_url_regex("artist", group="artist_key")

    @property
    @override
    def show_key(self) -> str:
        return artist_show_key(self._key)

    @override
    def raise_if_invalid(self) -> None:
        artist_file = self.plugin.artist_file(self._key)
        self.plugin.raise_if_invalid_file(artist_file, self.url)


class _CrunchyrollMusicURLHandler(_CrunchyrollURLHandler):
    _CATEGORY: MusicCategory

    @property
    @override
    def show_key(self) -> str:
        file = self.plugin.concert_or_music_video_file(self._episode_key)
        details = file.parsed().data[0]
        return artist_show_key(details.artist.id)

    @property
    def _episode_key(self) -> str:
        return music_episode_key(self._CATEGORY, self._key)

    @override
    def raise_if_invalid(self) -> None:
        music_file = self.plugin.concert_or_music_video_file(self._episode_key)
        self.plugin.raise_if_invalid_file(music_file, self.url)

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [
                        URLImportResult.for_episodes(show, [episode]),
                    ]

        msg = f"Episode {self._episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)


class CrunchyrollMusicVideoURLHandler(_CrunchyrollMusicURLHandler):
    """Crunchyroll music video URL handler.

    Example URL https://www.crunchyroll.com/watch/musicvideo/MV5CD8B009
    """

    _URL_REGEX = _build_crunchyroll_url_regex(
        "watch",
        "musicvideo",
        group="music_video_key",
    )
    _CATEGORY = MusicCategory.MUSIC_VIDEO


class CrunchyrollConcertURLHandler(_CrunchyrollMusicURLHandler):
    """Crunchyroll concert URL handler.

    Example URL https://www.crunchyroll.com/watch/concert/MC413F1C5C
    """

    _URL_REGEX = _build_crunchyroll_url_regex("watch", "concert", group="concert_key")
    _CATEGORY = MusicCategory.CONCERT
