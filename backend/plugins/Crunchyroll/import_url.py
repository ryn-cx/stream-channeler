# TODO: Validate
from __future__ import annotations

import re
from typing import override

from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
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


# TODO: Validate
class ImportURLMixin(HelperMixin, ReadURLPlugin, register=False):
    # https://www.crunchyroll.com/watch/musicvideo/MV5CD8B009
    _MUSIC_VIDEO_URL_REGEX = _build_crunchyroll_url_regex(
        "watch",
        "musicvideo",
        group="music_video_key",
    )
    # https://www.crunchyroll.com/watch/concert/MC413F1C5C
    _CONCERT_URL_REGEX = _build_crunchyroll_url_regex(
        "watch",
        "concert",
        group="concert_key",
    )
    # https://www.crunchyroll.com/artist/MA899F54A4
    _ARTIST_URL_REGEX = _build_crunchyroll_url_regex("artist", group="artist_key")
    # https://www.crunchyroll.com/series/GEXH3W29Z
    _SERIES_URL_REGEX = _build_crunchyroll_url_regex("series", group="show_key")
    # https://www.crunchyroll.com/watch/GVWU8XW1Z
    _EPISODE_URL_REGEX = _build_crunchyroll_url_regex("watch", group="episode_key")

    _episode_key: str | None
    _url_source_value: Source

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._MUSIC_VIDEO_URL_REGEX,  # Must be listed first due to URL overlap.
            cls._CONCERT_URL_REGEX,
            cls._ARTIST_URL_REGEX,
            cls._SERIES_URL_REGEX,
            cls._EPISODE_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _url_source(self) -> Source:
        return self._url_source_value

    # TODO: Validate
    @override
    def _read_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        self._episode_key = None

        for url_regex, group in (
            (self._MUSIC_VIDEO_URL_REGEX, "music_video_key"),
            (self._CONCERT_URL_REGEX, "concert_key"),
        ):
            if match := re.match(domain_regex + url_regex, url):
                self._read_music_url(match.group(group), url)
                return

        if match := re.match(domain_regex + self._ARTIST_URL_REGEX, url):
            self._show_key = match.group("artist_key")
            self._url_source_value = self.music_source
            self.raise_if_invalid_file(self.artist_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            self._show_key = match.group("show_key")
            self._url_source_value = self.video_source
            self.raise_if_invalid_file(self.series_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._EPISODE_URL_REGEX, url):
            self._read_episode_url(match.group("episode_key"), url)
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _read_music_url(self, episode_key: str, url: str) -> None:
        self._url_source_value = self.music_source
        music_file = self.concert_or_music_video_file(episode_key)
        self.raise_if_invalid_file(music_file, url)
        self._episode_key = episode_key
        self._show_key = music_file.parsed().data[0].artist.id

    # TODO: Validate
    def _read_episode_url(self, episode_key: str, url: str) -> None:
        self._url_source_value = self.video_source
        objects_file = self.objects_file(episode_key)
        self.raise_if_invalid_file(objects_file, url)

        # TODO: Is it true the api always returns the original region in the current
        # setup?
        # Episodes for different regions have different keys. The show is always
        # imported for the original region so the episode key also needs to match.
        for version in objects_file.parsed().data[0].episode_metadata.versions:
            if version.original:
                episode_key = version.guid
                break

        original_file = self.objects_file(episode_key)
        self.raise_if_invalid_file(original_file, url)
        self._episode_key = episode_key
        self._show_key = original_file.parsed().data[0].episode_metadata.series_id

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]

        msg = f"Episode {self._episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)
