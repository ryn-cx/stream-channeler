# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override
from urllib.parse import quote_plus

from wholoo.movies.models import MoviesModel
from wholoo.search.models import Result

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Hulu.files import FileMixin
from plugins.Hulu.handlers import HuluURLHandler, MovieURLHandler, SeriesURLHandler
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin

_SEARCH_MAX_AGE = timedelta(days=7)
_SEARCHABLE_TYPES = ("series", "movie")


class Hulu(FileMixin, URLHandlerPlugin[HuluURLHandler], register=True):
    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Hulu",)

    _URL_HANDLERS: ClassVar[tuple[type[HuluURLHandler], ...]] = (
        SeriesURLHandler,
        MovieURLHandler,
    )

    @classmethod
    @override
    def search_url(cls, query: str) -> str:
        return f"https://www.hulu.com/search?q={quote_plus(query)}"

    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        results = [
            self._search_result(result)
            for group in search_file.parsed().groups
            for result in group.results
            if result.metrics_info.target_type in _SEARCHABLE_TYPES
        ]
        return PluginSearchResults(results=results)

    def _search_result(self, result: Result) -> PluginSearchResult:
        metrics = result.metrics_info
        content_type = metrics.target_type
        premiere_date = result.entity_metadata.premiere_date
        return PluginSearchResult(
            title=metrics.target_name,
            url=self._show_url(f"{content_type}/{metrics.target_id}"),
            year=premiere_date.year if premiere_date else None,
            image_url=result.visuals.artwork.horizontal.image.path,
            media_type="Movie" if content_type == "movie" else "TV Show",
        )

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.hulu.com/series/fdeb1018-4472-442f-ba94-fb087cdea069`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.hulu.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981`\n\n"
        )

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    def _show_url(self, show_key: str) -> str:
        return self.build_url(show_key)

    def _episode_url(self, episode_key: str) -> str:
        return self.build_url(f"watch/{episode_key}")

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="Hulu",
            favicon_url="https://www.hulu.com/favicon.ico",
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if self._is_movie(show_key):
            return self._upsert_movie(source, show_key, force=force)
        return self._upsert_tv_show(source, show_key, force=force)

    def _upsert_tv_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        series_id = self._content_id(show_key)
        existing_show = Show.get_from_memory(self.session, source, show_key)
        model = self._series_model(series_id)
        entity = model.details.entity
        data_timestamp = self.show_data_timestamp(show_key)

        show = Show(
            key=show_key,
            name=model.name,
            description=entity.description,
            media_type="TV Show",
            url=self._show_url(show_key),
            image_url=model.artwork.program_tile.path,
            data_timestamp=data_timestamp,
            source_id=source.id,
        )

        tmdb_id = self._fetch_tmdb_id(show_key, existing_show)
        show = self.tmdb.tmdb_merge_show(show, tmdb_id)
        show_files = self._show_files(show_key)
        show = show.upsert_and_set_update_at(source, existing_show, show_files)

        self._upsert_tv_seasons(show, show_key, force=force)
        self._set_weekly_updates_from_episodes(show)
        return show

    def _upsert_tv_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        series_id = self._content_id(show_key)
        for sort_order, season_number in enumerate(self._season_numbers(series_id)):
            season_key = self._season_key(show_key, season_number)
            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    name=self._season_name(series_id, season_number),
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show_key),
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self.tmdb.tmdb_merge_season(
                    season,
                    show.tmdb_id,
                    season_number,
                    "tv",
                )
                season_files = self._season_files(season_key, show_key)
                season = season.upsert_and_set_update_at(
                    show,
                    season_check.record,
                    season_files,
                )
            else:
                season = season_check.record

            self._upsert_tv_episodes(season, show_key, season_number, force=force)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        series_id = self._content_id(show_key)
        for sort_order, item in enumerate(self._season_items(series_id, season_number)):
            episode_key = str(item.id)
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            episode = Episode(
                key=episode_key,
                name=item.name,
                episode_number=int(item.number),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=item.artwork.video_horizontal_hero.path,
                duration=item.duration,
                release_date=item.premiere_date,
                sort_order=sort_order,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            episode = self.tmdb.tmdb_merge_episode(
                episode,
                season.show.tmdb_id,
                season.season_number,
                int(item.number),
            )
            episode_files = self._episode_files(episode_key, season.key, show_key)
            episode.upsert_and_set_update_at(
                season,
                episode_check.record,
                episode_files,
            )

        self.soft_delete_missing_episodes(season.key)

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        movie_id = self._content_id(show_key)
        existing_show = Show.get_from_memory(self.session, source, show_key)
        model = self._movie_model(movie_id)
        data_timestamp = self.show_data_timestamp(show_key)

        show = Show(
            key=show_key,
            name=model.name,
            description=model.details.entity.description,
            url=self._show_url(show_key),
            image_url=model.artwork.program_tile.path,
            media_type="Movie",
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert_and_set_update_at(source, existing_show, self._show_files(show_key))

        self._upsert_movie_season(show, show_key, model, force=force)
        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        model: MoviesModel,
        *,
        force: bool = False,
    ) -> None:
        movie_id = self._content_id(show_key)
        season_key = self._season_key(show_key, 0)
        if season_check := self._season_check(show, season_key, show_key, force=force):
            season_files = self._season_files(season_key, show_key)
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show_key),
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            ).upsert_and_set_update_at(show, season_check.record, season_files)
        else:
            season = season_check.record

        if episode_check := self._episode_check(
            movie_id,
            season,
            show_key,
            force=force,
        ):
            episode_files = self._episode_files(movie_id, season.key, show_key)
            Episode(
                key=movie_id,
                name=model.name,
                description=model.details.entity.description,
                url=self._episode_url(movie_id),
                image_url=model.artwork.program_tile.path,
                duration=model.details.entity.duration,
                episode_number=0,
                sort_order=0,
                episode_identifier=f"{self.plugin_key()} {movie_id}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode_check.record, episode_files)

        self.soft_delete_missing_episodes(season.key)
        self.soft_delete_missing_seasons(show_key)
