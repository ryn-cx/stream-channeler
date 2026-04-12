from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.plugins.plugins.Crunchyroll.files import Browse, FileMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


class UpsertMixin(FileMixin, register=False):
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        """Return the episode URL for the episode_key."""
        return f"{cls._base_url()}watch/{episode_key}"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return f"{cls._base_url()}series/{show_key}"

    def _upsert_source(self, latest_browse_file: Browse) -> Source:
        source = Source.get_from_memory(self.db, self.plugin, self.plugin_key())
        timestamp = latest_browse_file.database_record.data_timestamp
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=f"{self._base_url()}build/assets/img/favicons/favicon-v2-96x96.png",
            update_at=timestamp + timedelta(days=1),
            data_timestamp=timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.db, source, show_key)
        series_data = self._series_file(show_key).parsed().data[0]
        show = Show(
            key=series_data.id,
            name=series_data.title,
            description=series_data.description,
            url=self._show_url(series_data.id),
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
            media_type=self._guess_media_type(show_key),
        ).upsert(source, existing_show)

        self._upsert_seasons(show, show_key)

        self._set_update_at_from_episodes(show)

        return show

    def _guess_media_type(self, show_key: str) -> str:
        """Guess media type based on the number of episodes and their release dates."""
        release_dates = [
            episode_data.premium_available_date
            for season_key in self._season_keys_from_file(show_key)
            for episode_data in self._episodes_file(season_key).parsed().data
        ]
        if len(release_dates) != 1:
            return "TV Show"
        latest_release = release_dates[0]
        if self.show_data_timestamp(show_key) > latest_release + timedelta(days=7):
            return "Movie"
        return "TV Show"

    @staticmethod
    def _set_update_at_from_episodes(show: Show) -> None:
        """Set update_at on the show and each season based on episode release dates."""
        for season in show.active_children:
            for episode in season.active_children:
                if episode.release_date:
                    update_at = episode.release_date + timedelta(days=7)
                    season.set_update_at(update_at)
                    show.set_update_at(update_at)

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        seasons_file = self._seasons_file(show_key)
        for i, season_data in enumerate(seasons_file.parsed().data):
            season_timestamp = self.season_data_timestamp(season_data.id, show.key)
            season = Season.get_from_memory(self.db, show, season_data.id)
            if not season or season.data_timestamp != season_timestamp:
                season = Season(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=season_timestamp,
                    show_id=show.id,
                ).upsert(show, season)

            self._upsert_episodes(season)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season) -> None:
        episode_timestamp = self.episode_data_timestamp("", season.key, season.show.key)
        episodes_data = self._episodes_file(season.key).parsed()
        for i, episode_data in enumerate(episodes_data.data):
            existing_episode = Episode.get_from_memory(self.db, season, episode_data.id)
            if (
                existing_episode
                and existing_episode.data_timestamp == episode_timestamp
            ):
                continue
            Episode(
                key=episode_data.id,
                url=self._episode_url(episode_data.id),
                sort_order=i,
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                episode_number=episode_data.episode_number,
                name=episode_data.title,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                duration=episode_data.duration_ms // 1000,
                data_timestamp=episode_timestamp,
                season_id=season.id,
            ).upsert(season, existing_episode)

        self.soft_delete_missing_episodes(season.key)
