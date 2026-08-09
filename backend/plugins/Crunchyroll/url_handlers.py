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

# Crunchyroll serves the same page under a locale prefix (`/de/series/...`,
# `/pt-br/series/...`), which a link from elsewhere may well carry.
_LOCALE = r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"

# Every id Crunchyroll puts in a URL has this shape.
_KEY = r"[A-Z0-9]{9,}"

# What may follow a key: a slug, a query, a fragment, or the end of the URL. A
# link from elsewhere keeps its tracking parameters, so a query has to end a key
# just as a slash does.
_KEY_END = r"(?:[\/?#]|$)"


def _key_url_regex(*path: str, group: str) -> str:
    """Return the regex for a Crunchyroll path that ends in an id.

    Wraps `path` in the locale prefix and the key terminator so each handler
    only states the part that is its own.
    """
    segments = "".join(rf"\/{segment}" for segment in path)
    return rf"{_LOCALE}{segments}\/(?P<{group}>{_KEY}){_KEY_END}"


class CrunchyrollURLHandler(URLHandler["Crunchyroll"]):
    """Base URL handler for the Crunchyroll plugin."""

    @override
    def __init__(self, plugin: Crunchyroll, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class CrunchyrollSeriesURLHandler(CrunchyrollURLHandler):
    """Crunchyroll series URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/series/GEXH3W29Z
        - https://www.crunchyroll.com/series/GEXH3W29Z/compass20-animation-project
    """

    _URL_REGEX = _key_url_regex("series", group="show_key")

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def raise_if_invalid(self) -> None:
        plugin_file = self.plugin.series_file(self._key)
        self.plugin.raise_if_invalid_file(plugin_file, self.url)


class CrunchyrollEpisodeURLHandler(CrunchyrollURLHandler):
    """Crunchyroll episode URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/watch/GVWU8XW1Z
        - https://www.crunchyroll.com/watch/GVWU8XW1Z/this-is-compass20
    """

    _URL_REGEX = _key_url_regex("watch", group="episode_key")

    @property
    @override
    def show_key(self) -> str:
        objects_file = self.plugin.objects_file(self._key)
        return objects_file.parsed().data[0].episode_metadata.series_id

    @override
    def raise_if_invalid(self) -> None:
        objects_file = self.plugin.objects_file(self._key)
        self.plugin.raise_if_invalid_file(objects_file, self.url)

        # Crunchyroll gives an episode an id per audio version and a link can
        # name any of them, but a show only carries the original one, so the key
        # becomes that and the dub is not referred to again.
        for version in objects_file.parsed().data[0].episode_metadata.versions:
            if version.original:
                self._key = version.guid
                break

        original_file = self.plugin.objects_file(self._key)
        self.plugin.raise_if_invalid_file(original_file, self.url)

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return [
            URLImportResult.for_episodes(show, [self._stored_episode(show)]),
        ]

    def _stored_episode(self, show: Show) -> Episode:
        """Return the episode the URL names.

        Raises:
            `InvalidURLError` if the show does not carry the episode.

        """
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._key:
                    return episode

        msg = f"Episode {self._key} not found in show {show.key}"
        raise InvalidURLError(msg)


class CrunchyrollArtistURLHandler(CrunchyrollURLHandler):
    """Crunchyroll artist URL handler.

    Importing an artist takes every music video and concert they have released,
    and every one they release later.

    Supported URL Formats:
        - https://www.crunchyroll.com/artist/MA899F54A4
        - https://www.crunchyroll.com/artist/MA899F54A4/lisa
    """

    _URL_REGEX = _key_url_regex("artist", group="artist_key")

    @property
    @override
    def show_key(self) -> str:
        return artist_show_key(self._key)

    @override
    def raise_if_invalid(self) -> None:
        artist_file = self.plugin.artist_file(self._key)
        self.plugin.raise_if_invalid_file(artist_file, self.url)


class CrunchyrollMusicURLHandler(CrunchyrollURLHandler):
    """Base handler for a single music video or concert.

    Both are reached through the artist that released them, so the URL only
    identifies which of the artist's episodes the import should whitelist.
    """

    _CATEGORY: MusicCategory

    @property
    @override
    def show_key(self) -> str:
        details = self.plugin.music_file(self._episode_key).parsed().data[0]
        return artist_show_key(details.artist.id)

    @property
    def _episode_key(self) -> str:
        return music_episode_key(self._CATEGORY, self._key)

    @override
    def raise_if_invalid(self) -> None:
        music_file = self.plugin.music_file(self._episode_key)
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


class CrunchyrollMusicVideoURLHandler(CrunchyrollMusicURLHandler):
    """Crunchyroll music video URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/watch/musicvideo/MV5CD8B009
        - https://www.crunchyroll.com/watch/musicvideo/MV5CD8B009/gurenge
    """

    _URL_REGEX = _key_url_regex("watch", "musicvideo", group="music_video_key")
    _CATEGORY = MusicCategory.MUSIC_VIDEO


class CrunchyrollConcertURLHandler(CrunchyrollMusicURLHandler):
    """Crunchyroll concert URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/watch/concert/MC413F1C5C
        - https://www.crunchyroll.com/watch/concert/MC413F1C5C/lisa-ladybug
    """

    _URL_REGEX = _key_url_regex("watch", "concert", group="concert_key")
    _CATEGORY = MusicCategory.CONCERT
