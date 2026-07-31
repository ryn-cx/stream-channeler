# TODO: Validate
from __future__ import annotations

from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.NHKWorld.files import FileMixin


class UpsertMixin(FileMixin, register=False):
    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            program = self.video_program_file(show_key).parsed()
            show = Show(
                key=program.id,
                name=program.title,
                description=program.description,
                url=self.build_url(program.url),
                image_url=self._get_image_url(program.images.portrait),
                media_type="TV Show",
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            ).upsert_and_set_update_at(
                source,
                show,
                self._show_files(show_key),
            )

        self._upsert_season(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, show_key)
        if self._season_is_outdated(season, force=force):
            season_files = self._season_files(show_key, show_key)
            season = Season(
                key=show_key,
                sort_order=0,
                url=show.url,
                data_timestamp=self.season_data_timestamp(show_key, show_key),
                show_id=show.id,
            ).upsert_and_set_update_at(show, season, season_files)

        self._upsert_episodes(season, show_key, force=force)

    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(show_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            episode = Episode.get_from_memory(self.session, season, item.id)
            if not self._episode_is_outdated(episode, force=force):
                continue

            video = item.video
            episode_files = self._episode_files(item.id, season.key, show_key)
            Episode(
                key=item.id,
                name=item.title,
                url=self.build_url(item.url),
                description=item.description,
                image_url=self._get_image_url(item.images),
                release_date=video.published_at,
                air_date=item.first_broadcasted_at,
                duration=video.duration,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                episode_identifier=f"NHKWorld {item.id}",
                data_timestamp=self.episode_data_timestamp(
                    item.id,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode, episode_files)
