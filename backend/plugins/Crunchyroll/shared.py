# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, override

from chirashi.season_episodes.models import Images as EpisodeImages
from chirashi.series.models import Images as SeriesImages
from chirashi.series.models import SeriesModel

from plugins.Crunchyroll.constants import (
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    CrunchyrollMusicCategory,
)
from plugins.Crunchyroll.files import (
    Artist,
    ArtistConcerts,
    ArtistMusicVideos,
    Catalogue,
    Categories,
    Concert,
    MusicVideo,
    Objects,
    SeasonEpisodes,
    Seasons,
    Series,
    SimilarTo,
)
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import TMDBLookupInfo

# The prefix Crunchyroll issues ids under, which is what a key is recognised by.
CATEGORY_ID_PREFIXES = {
    "MV": CrunchyrollMusicCategory.MUSIC_VIDEO,
    "MC": CrunchyrollMusicCategory.CONCERT,
}


# TODO: Validate
def title_is_a_series(title_key: str) -> bool:
    """Report whether a `Title` key belongs to a series rather than an artist."""
    return title_key.startswith("G")


# TODO: Validate
def season_is_music(season_key: str) -> bool:
    """Report whether a `Season` key is for music."""
    return season_key in set(CrunchyrollMusicCategory)


# TODO: Validate
def music_episode_category(episode_key: str) -> CrunchyrollMusicCategory:
    """Return the listing an episode is a video or a concert of."""
    return CATEGORY_ID_PREFIXES[episode_key[:2]]


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://crunchyroll.com/{path.lstrip('/')}"


# TODO: Validate
class CrunchyrollSizedImage(Protocol):
    width: int
    source: str


# TODO: Validate
def largest_image(images: Sequence[CrunchyrollSizedImage]) -> str | None:
    """Return the source of the widest size Crunchyroll offers an image in."""
    if not images:
        return None
    return max(images, key=lambda image: image.width).source


# TODO: Validate
def nearest_thumbnail(images: Sequence[CrunchyrollSizedImage]) -> str | None:
    if not images:
        return None
    wide_enough = [image for image in images if image.width >= 480]  # noqa: PLR2004
    if wide_enough:
        return min(wide_enough, key=lambda image: image.width).source
    return max(images, key=lambda image: image.width).source


# TODO: Validate
def title_image(images: SeriesImages) -> str | None:
    """Return the widest poster a listing carries, where it carries one.

    The wide one first because that is the shape the artwork is shown in, the
    tall one being what is left for a listing Crunchyroll has only a portrait
    poster of.
    """
    wide = images.poster_wide
    if wide and wide[0]:
        return max(wide[0], key=lambda image: image.width).source
    tall = images.poster_tall
    if tall and tall[0]:
        return max(tall[0], key=lambda image: image.width).source
    return None


# TODO: Validate
def title_thumbnail(images: SeriesImages) -> str | None:
    wide = images.poster_wide
    if wide and wide[0]:
        return nearest_thumbnail(wide[0])
    tall = images.poster_tall
    if tall and tall[0]:
        return nearest_thumbnail(tall[0])
    return None


# TODO: Validate
def title_poster(images: SeriesImages) -> str | None:
    tall = images.poster_tall
    if tall and tall[0]:
        return max(tall[0], key=lambda image: image.width).source
    return None


# TODO: Validate
def title_poster_thumbnail(images: SeriesImages) -> str | None:
    tall = images.poster_tall
    if tall and tall[0]:
        return nearest_thumbnail(tall[0])
    return None


# TODO: Validate
def episode_image(images: EpisodeImages) -> str | None:
    """Return the largest thumbnail an episode has, where it has one at all.

    An episode Crunchyroll has no thumbnail for carries no sizes to pick from,
    and older ones carry none of the field at all.
    """
    thumbnails = images.thumbnail
    if not thumbnails or not thumbnails[0]:
        return None
    return thumbnails[0][-1].source


# TODO: Validate
def episode_thumbnail(images: EpisodeImages) -> str | None:
    thumbnails = images.thumbnail
    if not thumbnails or not thumbnails[0]:
        return None
    return nearest_thumbnail(thumbnails[0])


# TODO: Validate
def is_movie(series: SeriesModel) -> bool:
    return "type:movie" in series.keywords


# TODO: Validate
class CrunchyrollShared(BasePlugin):
    # TODO: Validate
    def series_file(self, title_key: str) -> Series:
        return self._cached_file(Series, title_key)

    # TODO: Validate
    def categories_file(self, title_key: str) -> Categories:
        return self._cached_file(Categories, title_key)

    # TODO: Validate
    def similar_to_file(self, title_key: str) -> SimilarTo:
        return self._cached_file(SimilarTo, title_key)

    # TODO: Validate
    def objects_file(self, episode_key: str) -> Objects:
        return self._cached_file(Objects, episode_key)

    # TODO: Validate
    def seasons_file(self, title_key: str) -> Seasons:
        return self._cached_file(Seasons, title_key)

    # TODO: Validate
    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._cached_file(SeasonEpisodes, season_key)

    # TODO: Validate
    def artist_file(self, artist_id: str) -> Artist:
        return self._cached_file(Artist, artist_id)

    # TODO: Validate
    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        return self._cached_file(ArtistMusicVideos, artist_id)

    # TODO: Validate
    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        return self._cached_file(ArtistConcerts, artist_id)

    # TODO: Validate
    def music_video_file(self, music_video_id: str) -> MusicVideo:
        return self._cached_file(MusicVideo, music_video_id)

    # TODO: Validate
    def concert_file(self, concert_id: str) -> Concert:
        return self._cached_file(Concert, concert_id)

    # TODO: Validate
    def catalogue_file(self) -> Catalogue:
        return self._cached_file(Catalogue, "alphabetical")

    # TODO: Validate
    def season_file(
        self,
        artist_id: str,
        category: CrunchyrollMusicCategory,
    ) -> ArtistMusicVideos | ArtistConcerts:
        """Return the ArtistMusicVideos or ArtistConcerts file based on the category.

        Each artist (Title) has two `Season`s, one for concerts and one for music
        videos. This function main purpose is to make sure the correct files are
        returned when getting all of the files for a specific season.
        """
        if category is CrunchyrollMusicCategory.CONCERT:
            return self.artist_concerts_file(artist_id)
        return self.artist_music_videos_file(artist_id)

    # TODO: Validate
    def concert_or_music_video_file(
        self,
        episode_key: str,
    ) -> MusicVideo | Concert:
        """Return the Concert or MusicVideo file based on the category.

        There are different files for concerts and music videos. This function main
        purpose is to make sure the correct files are returned when getting all of the
        files for a specific episode.
        """
        if music_episode_category(episode_key) is CrunchyrollMusicCategory.CONCERT:
            return self.concert_file(episode_key)
        return self.music_video_file(episode_key)

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        # Do not use the year for Crunchyroll because it's so often incorrect. It's fine
        # to leave it in the database as a reference but using it for lookups keeps
        # returning the wrong results.
        return [
            lookup_info._replace(year=None)
            for lookup_info in super().tmdb_lookup_info(title)
        ]
