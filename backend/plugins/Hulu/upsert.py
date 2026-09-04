# TODO: Validate
"""Writing what Hulu says about a title into the database."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service.canonical import add_canonical_show_and_link_episodes
from app.sources.models import Source
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Hulu.files import FileMixin, MovieFileMixin, SeriesFileMixin
from plugins.Hulu.utils import HuluMediaType, season_name, season_numbers

if TYPE_CHECKING:
    from wholoo.movies.models import MoviesModel


# TODO: Validate
class SeriesUpsertMixin(SeriesFileMixin):
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(existing_show, force=force):
            parsed_series = self.series_file(show_key).parsed()
            entity = parsed_series.details.entity
            new_show = Show(
                key=show_key,
                name=parsed_series.name,
                description=entity.description,
                media_type="TV Show",
                url=self._show_url(show_key, HuluMediaType.SERIES),
                image_url=self._image_url(parsed_series.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(
                    parsed_series.artwork.program_tile.path
                ),
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            existing_show = self._upsert_show_object(
                new_show,
                source,
                existing_show,
                show_key,
            )

        self._upsert_seasons(existing_show, force=force)
        self._soft_delete_missing(show_key)
        add_canonical_show_and_link_episodes(
            self.session,
            existing_show,
            canonical_show,
        )

        return existing_show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self.series_file(show.key).parsed()),
        ):
            season_key = self._season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_name(
                        self.season_file(show.key, season_number).parsed(),
                    ),
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(new_season, show, season, show.key)

            self._upsert_episodes(season, show.key, season_number, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        season_items = self.season_file(show_key, season_number).parsed().items
        for sort_order, item in enumerate(season_items):
            start_date = item.bundle.availability.start_date
            if start_date > tz_datetime.now():
                continue

            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            hero_artwork = item.artwork.video_horizontal_hero
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.name,
                episode_number=int(item.number),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=self._image_url(hero_artwork.path) if hero_artwork else None,
                thumbnail_url=self._thumbnail_url(hero_artwork.path)
                if hero_artwork
                else None,
                duration=item.duration,
                air_date=item.premiere_date,
                sort_order=sort_order,
                data_timestamp=self.episode_data_timestamp(
                    episode_key,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)


# TODO: Validate
class MovieUpsertMixin(MovieFileMixin):
    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        model = self.movie_file(show_key).parsed()
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            new_show = Show(
                key=show_key,
                name=model.name,
                description=model.details.entity.description,
                url=self._show_url(show_key, HuluMediaType.MOVIE),
                image_url=self._image_url(model.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(model.artwork.program_tile.path),
                media_type="Movie",
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_season(show, force=force)
        self._soft_delete_missing(show_key)
        add_canonical_show_and_link_episodes(self.session, show, canonical_show)

        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        model = self.movie_file(show.key).parsed()
        season_key = self._season_key(show.key, 0)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=self.season_data_timestamp(season_key, show.key),
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show.key)

        self._upsert_episode(season, show.key, model, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        model: MoviesModel,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            new_episode = Episode(
                key=show_key,
                watch_identifier=watch_identifier(self.plugin_name(), show_key),
                name=model.name,
                description=model.details.entity.description,
                url=self._episode_url(show_key),
                image_url=self._image_url(model.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(model.artwork.program_tile.path),
                duration=model.details.entity.duration,
                episode_number=0,
                sort_order=0,
                data_timestamp=self.episode_data_timestamp(
                    show_key,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)


# TODO: Validate
class UpsertMixin(FileMixin):
    """Mixin containing all upsert functions."""

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        source_files = self._source_files()
        source = Source.get_from_memory(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=self._file_timestamp(source_files),
            update_at=staggered_monthly_update_at(source_key, tz_datetime.now()),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
