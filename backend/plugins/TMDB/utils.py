# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, NamedTuple

from sqlmodel import col, select

from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile

if TYPE_CHECKING:
    from plugins.TMDB.lookup import LookupMixin


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def poster_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w500", path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def poster_original_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def backdrop_thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w300", path)


# TODO: Validate
def still_thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w300", path)


# TODO: Validate
def logo_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: str | date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, and every date the API answers with arrives as the text
    # TMDB wrote rather than as a date.
    if not air_date:
        return None
    if isinstance(air_date, str):
        air_date = date.fromisoformat(air_date)
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
def change_datetime(changed_at: str) -> datetime:
    return tz_datetime.fromisoformat(changed_at.replace(" UTC", "+00:00"))


# TODO: Validate
def first_search_result(
    plugin: LookupMixin,
    name: str,
    media_type: TMDBMediaType | None,
    year: int | None,
) -> tuple[TMDBMediaType, int] | None:
    """Return which half the first title TMDB returns is from, and its id."""
    if media_type is not None:
        results = plugin.search_media(media_type, name, year).parsed().results
        return (media_type, results[0].id) if results else None

    # A search of both halves also returns people, who are no title and are
    # passed over rather than taken as the first result.
    for result in plugin.search_media(None, name, year).parsed().results:
        # Which half of the catalogue a search of both says a result came
        # from. A multi search also returns people, who are no title and
        # cannot be imported.
        half = {"movie": TMDBMediaType.movie, "tv": TMDBMediaType.tv}.get(
            result.media_type,
        )
        if half is not None:
            return half, result.id
    return None


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    id: int
    number: int
    name: str
    overview: str
    still_path: str | None
    runtime: int | None
    air_date: date | None
    native_season_number: int
    native_episode_number: int


# TODO: Validate
class SeasonSource(NamedTuple):
    """One season of a title, however the title is being read.

    The two ways of reading a series - TMDB's own seasons and a chosen episode
    order - answer with different files holding different shapes, and everything
    that writes a season wants the same handful of things out of either. So both
    are read into this and nothing downstream asks which it was.
    """

    key: str
    name: str | None
    season_number: int
    poster_path: str | None
    episodes: list[EpisodeSource]


# TODO: Validate
class UtilsMixin(BasePlugin):
    # TODO: Validate
    @property
    def source(self) -> Source:
        return self._sources[self.plugin_name()]

    # TODO: Validate
    @staticmethod
    def _watch_providers_due(record: Show | Season | None) -> bool:
        if record is None or record.update_at is None:
            return False
        return record.update_at <= tz_datetime.now()

    # TODO: Validate
    def files_with_prefix(
        self,
        file_class: type[BaseFile[Any]],
        key_prefix: str,
    ) -> Sequence[File]:
        statement = select(File).where(
            File.plugin == self.plugin,
            col(File.key).startswith(f"{file_class.class_key()}/{key_prefix}"),
        )
        return self.session.exec(statement).all()

    # TODO: Validate
    @staticmethod
    def _get_file_date_from_name(file_class: type[BaseFile[Any]], stored: File) -> date:
        identifier = file_class.file_to_unique_identifier(stored)
        return date.fromisoformat(identifier.split("/")[-1])

    # TODO: Validate
    def latest_dated_file_date(
        self,
        file_class: type[BaseFile[Any]],
        key_prefix: str,
    ) -> date:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{file_class.class_key()}/{key_prefix}"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        stored = self.session.exec(statement).first()
        if stored is None:
            return tz_datetime.now().date()
        return self._get_file_date_from_name(file_class, stored)
