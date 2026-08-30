# TODO: Validate
from __future__ import annotations

from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from plugins.NHKWorld.files import FileMixin


# TODO: Validate
class UpsertMixin(FileMixin, register=False):
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
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            program = self.video_program_file(show_key).parsed()
            new_show = Show(
                key=program.id,
                name=program.title,
                description=program.description,
                url=self.build_url(program.url),
                image_url=self._get_image_url(program.images.portrait),
                thumbnail_url=self._get_thumbnail_url(program.images.portrait),
                media_type="TV Show",
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_season(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        add_canonical_show_and_link_episodes(self.session, show, canonical_show)
        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, show_key)
        if self._season_is_outdated(season, show_key, force=force):
            new_season = Season(
                key=show_key,
                season_number=1,
                sort_order=0,
                data_timestamp=self.season_data_timestamp(show_key, show_key),
                show_id=show.id,
            )
            season = self._upsert_season_object(
                new_season,
                show,
                season,
                show_key,
            )

        self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
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
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            new_episode = Episode(
                key=item.id,
                name=item.title,
                url=self.build_url(item.url),
                description=item.description,
                image_url=self._get_image_url(item.images),
                thumbnail_url=self._get_thumbnail_url(item.images),
                air_date=item.first_broadcasted_at,
                duration=item.video.duration,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                data_timestamp=self.episode_data_timestamp(
                    item.id,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(
                new_episode,
                season,
                episode,
                show_key,
            )
