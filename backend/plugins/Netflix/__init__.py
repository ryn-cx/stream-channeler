# TODO: Validate
import re
from datetime import datetime, timedelta
from typing import Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from meshfilm.title import models as netflix_models
from plugins.Netflix.files import FileMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult


class Netflix(FileMixin, register=True):
    _VERSION = "0.0.1"

    @classmethod
    def import_url_instructions(cls) -> str:
        return "> [!TIP/Title]\n> `https://www.netflix.com/title/80240027`\n\n"

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key = self._parse_url(url)
        self._validate_url(show_key, url)
        show = self._import_show(show_key)
        return [URLImportResult(show=show, is_whitelist=False)]

    @override
    def _parse_url(self, url: str) -> str:
        if match := re.match(self._url_regex(), url):
            return match.group("title_key")
        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, show_key: str, url: str) -> None:
        self._raise_if_no_content(self.title_file(show_key), url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key).one_or_none():
            return show

        _cache = self._download_show_files_and_children(show_key)
        return self._upsert_show(self.source, show_key)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        # Example URL: https://www.netflix.com/title/80240027
        return cls._domain_regex() + r"\/title\/(?P<title_key>\d+)(?:\/|$)"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"title/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="Netflix",
            favicon_url="https://www.netflix.com/favicon.ico",
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        if self._is_movie(show_key):
            return self._upsert_movie(source, show_key)
        return self._upsert_tv_show(source, show_key)

    def _upsert_tv_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        show_data = self._main_show(show_key)
        assert show_data

        show = Show(
            key=show_key,
            name=show_data.title,
            description=show_data.short_synopsis,
            url=self._show_url(show_key),
            image_url=self._artwork_url(show_data.artwork_boxshot_300_jpg),
            media_type="TV Show",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_tv_seasons(show, show_key)
        self._apply_update_schedule(show, self._latest_release(show_key))
        return show

    def _upsert_tv_seasons(self, show: Show, show_key: str) -> None:
        for sort_order, season_data in enumerate(self._ordered_seasons(show_key)):
            season_key = self._season_key(show_key, season_data.video_id)
            new_timestamp = self.season_data_timestamp(season_key, show_key)
            season = Season.get_from_memory(self.session, show, season_key)
            if (
                not season
                or season.data_timestamp != new_timestamp
                or season.deleted_at is not None
            ):
                season = Season(
                    key=season_key,
                    name=season_data.title,
                    season_number=sort_order + 1,
                    sort_order=sort_order,
                    url=self._show_url(show_key),
                    data_timestamp=new_timestamp,
                    show_id=show.id,
                ).upsert(show, season)

            self._upsert_tv_episodes(season, show_key, season_data.video_id)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: int,
    ) -> None:
        for sort_order, episode_data in enumerate(
            self._season_episodes(show_key, season_id),
        ):
            episode_key = str(episode_data.video_id)
            new_timestamp = self.episode_data_timestamp(
                episode_key,
                season.key,
                show_key,
            )
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if (
                episode
                and episode.data_timestamp == new_timestamp
                and episode.deleted_at is None
            ):
                continue

            release_date = self._episode_release_date(episode_data)
            Episode(
                key=episode_key,
                name=episode_data.title,
                description=episode_data.short_synopsis,
                url=self._episode_url(episode_key),
                image_url=self._artwork_url(episode_data.artwork_merch_still_300_png),
                episode_number=episode_data.number,
                sort_order=sort_order,
                duration=episode_data.runtime_sec,
                release_date=release_date,
                air_date=release_date,
                data_timestamp=new_timestamp,
                season_id=season.id,
            ).upsert(season, episode)

        self.soft_delete_missing_episodes(season.key)

    def _upsert_movie(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        movie_data = self._main_movie(show_key)
        assert movie_data

        show = Show(
            key=show_key,
            name=movie_data.title,
            url=self._show_url(show_key),
            image_url=self._artwork_url(movie_data.artwork_boxshot_300_jpg),
            media_type="Movie",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_movie_season(show, show_key, movie_data)
        self._apply_update_schedule(show, self._latest_release(show_key))
        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        movie_data: netflix_models.Movie,
    ) -> None:
        season_key = self._season_key(show_key, show_key)
        new_timestamp = self.season_data_timestamp(season_key, show_key)
        season = Season.get_from_memory(self.session, show, season_key)
        if (
            not season
            or season.data_timestamp != new_timestamp
            or season.deleted_at is not None
        ):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show_key),
                data_timestamp=new_timestamp,
                show_id=show.id,
            ).upsert(show, season)

        episode_key = show_key
        episode_timestamp = self.episode_data_timestamp(
            episode_key,
            season.key,
            show_key,
        )
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if (
            not episode
            or episode.data_timestamp != episode_timestamp
            or episode.deleted_at is not None
        ):
            Episode(
                key=episode_key,
                name=movie_data.title,
                url=self._episode_url(episode_key),
                image_url=self._artwork_url(movie_data.artwork_boxshot_300_jpg),
                episode_number=0,
                sort_order=0,
                data_timestamp=episode_timestamp,
                season_id=season.id,
            ).upsert(season, episode)

        self.soft_delete_missing_episodes(season.key)
        self.soft_delete_missing_seasons(show_key)

    def _latest_release(self, show_key: str) -> datetime | None:
        """Latest episode availability if the data exposes it, else show premiere.

        Netflix's public data usually omits per-episode dates, so the show's
        premiere (availabilityStartTime) is the fallback signal.
        """
        title = self._title(show_key)
        episode_dates = [
            date
            for episode in title.episodes or []
            if (date := self._episode_release_date(episode))
        ]
        if episode_dates:
            return max(episode_dates)
        if main_show := self._main_show(show_key):
            return main_show.availability_start_time
        return None

    def _apply_update_schedule(self, show: Show, release: datetime | None) -> None:
        """Schedule the file to refresh a week after the latest release, and a
        month after this download, whichever comes first.
        """
        entities: list[Show | Season | Episode] = [show]
        for season in show.seasons:
            entities.append(season)
            entities.extend(season.episodes)

        for entity in entities:
            if release:
                entity.set_update_at(release + timedelta(days=7))
            entity.set_update_at(entity.data_timestamp + timedelta(days=30))

    @staticmethod
    def _episode_release_date(
        episode: netflix_models.Episode,
    ) -> datetime | None:
        # Episodes of currently-airing shows may expose availabilityStartTime,
        # which meshfilm adds to the model on demand; released shows omit it.
        return getattr(episode, "availability_start_time", None)

    @staticmethod
    def _artwork_url(artwork: Any) -> str | None:  # noqa: ANN401 - Varies by artwork type.
        return artwork.url if artwork else None
