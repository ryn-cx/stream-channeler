# TODO: Validate
from __future__ import annotations

from typing import override

from pools_closed.show.models import Season as SeasonData
from pools_closed.show.models import ShowModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from plugins.AdultSwim.files import ShowsPage
from plugins.AdultSwim.utils import HelperMixin, source_requires_auth


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    # TODO: Validate
    @override
    def _upsert_source(self, source_key: str) -> Source:
        latest_shows_file = self.find_newest_shows_file()
        if not latest_shows_file:
            latest_shows_file = self._initial_file(ShowsPage)
            latest_shows_file.download_if_outdated()

        existing_source = Source.get(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            data_timestamp=latest_shows_file.data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(
            self.plugin,
            existing_source,
            [latest_shows_file],
        )

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
        show_data = self.show_file(show_key).parsed()
        metadata = show_data.metadata
        hero = show_data.hero
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            new_show = Show(
                key=show_key,
                name=show_data.title,
                description=metadata.description if metadata else None,
                media_type="TV Show",
                url=self.show_url(show_key),
                image_url=hero.image_url if hero else None,
                thumbnail_url=metadata.thumbnail if metadata else None,
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_seasons(
            show,
            show_data,
            requires_auth=source_requires_auth(source.key),
            force=force,
        )
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)

        add_canonical_show_and_link_episodes(self.session, show, canonical_show)
        return show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        show_data: ShowModel,
        *,
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        for sort_order, season_data in enumerate(show_data.seasons):
            season_key = str(season_data.number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_data.name,
                    season_number=season_data.number,
                    sort_order=sort_order,
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show.key,
                )

            self._upsert_episodes(
                season,
                show.key,
                season_data,
                requires_auth=requires_auth,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_data: SeasonData,
        *,
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        episodes_data = [
            episode_data
            for episode_data in season_data.episodes
            if episode_data.auth == requires_auth
        ]
        for sort_order, episode_data in enumerate(episodes_data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            new_episode = Episode(
                key=episode_data.id,
                name=episode_data.title,
                description=episode_data.description,
                url=self.episode_url(
                    episode_data.collection_slug,
                    episode_data.slug,
                ),
                image_url=episode_data.poster,
                thumbnail_url=episode_data.poster,
                air_date=episode_data.first_airing or episode_data.launch_date,
                duration=int(episode_data.duration),
                episode_number=episode_data.episode_number,
                sort_order=sort_order,
                data_timestamp=self.episode_data_timestamp(
                    episode_data.id,
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

        season.soft_delete_missing_children(
            episode_data.id for episode_data in episodes_data
        )
