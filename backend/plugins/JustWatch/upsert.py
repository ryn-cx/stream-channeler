# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.JustWatch.helpers import HelperMixin
from plugins.TMDB.mixin import highest_episode_number

if TYPE_CHECKING:
    from just_scrape.url_title_details import models as url_title_details_models


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    # TODO: Validate
    def _upsert_sources(self) -> None:
        """Create or update a `Source` for every provider JustWatch tracks."""
        _cache = self._preload_sources().all()
        for source_key in self._providers_by_key():
            self._upsert_source(source_key)

    # TODO: Validate
    @override
    def _upsert_source(self, source_key: str) -> Source:
        """Create or update the `Source` for a single provider."""
        provider = self.provider(source_key)
        # Every provider gets a source but most are never read again, so they
        # fall out of the session's weak identity map and have to be looked up
        # in the database rather than in memory.
        existing_source = Source.get(self.session, self.plugin, source_key)

        source = Source(
            key=source_key,
            name=provider["clear_name"],
            favicon_url=self._favicon_url(provider),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)

        # Only use the data timestamp from the providers file for the initial
        # import. If the source already has a data_timestamp keep it because it will
        # be based on data from the new titles files which are more up to date.
        if not source.data_timestamp:
            source.data_timestamp = self.providers_locale_file().data_timestamp

        return source

    # TODO: Validate
    def _upsert_shows(
        self,
        show_key: str,
        source_keys: list[str] | None = None,
        *,
        force: bool = False,
    ) -> list[Show]:
        shows: list[Show] = []
        for source_key, _ in self._sources_with_offers(show_key):
            if source_keys is not None and source_key not in source_keys:
                continue
            source = self._upsert_source(source_key)
            shows.append(self.upsert_show(source, show_key, force=force))
        return shows

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)

        offer = next(
            (
                offer
                for offer_source_key, offer in self._sources_with_offers(show_key)
                if offer_source_key == source.key
            ),
            None,
        )

        # A source that stopped offering the title has nothing left to import, so the
        # show it was imported into is soft deleted.
        if offer is None:
            if existing_show is None:
                msg = f"Source {source.key} has no offer for show {show_key}."
                raise ValueError(msg)
            existing_show.soft_delete()
            return existing_show

        parsed_json = self.url_title_details_file(show_key).parsed()
        media_type = self._media_type(show_key)
        new_show = Show(
            key=show_key,
            name=parsed_json.data.url_v2.node.content.title,
            media_type=media_type,
            description=parsed_json.data.url_v2.node.content.short_description,
            url=self._clean_external_url(offer.standard_web_url),
            image_url=self._images_base_url
            + parsed_json.data.url_v2.node.content.full_backdrops[0].backdrop_url,
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        )
        show = self._merge_and_upsert_show(
            new_show,
            source,
            existing_show,
            show_key,
            self.tmdb_media_type(show_key),
        )

        self._upsert_seasons(show, show_key, force=force)

        self.soft_delete_missing_seasons(show_key)

        self._set_weekly_updates_from_episodes(show)

        return show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        if self._media_type(show_key) == "TV Show":
            self._upsert_show_seasons(show, show_key, force=force)
        else:
            self._upsert_movie_season(show, show_key, force=force)

    # TODO: Validate
    def _upsert_show_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        # TODO: Upstream in JustScrape, add the ability to parse specific types so there
        # is less need for checking for None.
        parsed_json = self.url_title_details_file(show_key).parsed()
        seasons_data = parsed_json.data.url_v2.node.seasons
        # TODO: Eventually this should be able to be removed once JustScrape is updated.
        if seasons_data is None:
            msg = f"No seasons found for show: {show_key}"
            raise ValueError(msg)
        for season_data in seasons_data:
            existing_season = Season.get_from_memory(self.session, show, season_data.id)
            image_url = self._format_image_url(season_data.content.poster_url, 166)
            new_season = Season(
                image_url=image_url,
                # TODO: Should I use the other ID that matches the URL instead?
                key=season_data.id,
                sort_order=season_data.content.season_number,
                season_number=season_data.content.season_number,
                data_timestamp=self.season_data_timestamp(season_data.id, show_key),
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                new_season,
                show,
                existing_season,
                show_key,
                MediaType.tv,
            )
            self._upsert_season_episodes(
                show,
                season,
                season_data,
                show_key,
                force=force,
            )
            self.soft_delete_missing_episodes(season.key, show_key)

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        parsed_json = self.url_title_details_file(show_key).parsed()
        node_id = parsed_json.data.url_v2.node.id
        existing_season = Season.get_from_memory(self.session, show, node_id)
        new_season = Season(
            key=node_id,
            name="Movie",
            sort_order=0,
            season_number=0,
            data_timestamp=self.season_data_timestamp(node_id, show_key),
            show_id=show.id,
        )
        season = self._merge_and_upsert_season(
            new_season,
            show,
            existing_season,
            show_key,
            MediaType.movie,
        )
        upserted_key = self._upsert_movie_episode(show, season, show_key, force=force)
        expected_keys = [upserted_key] if upserted_key else []
        season.soft_delete_missing_children(expected_keys)

    # TODO: Validate
    def _upsert_season_episodes(
        self,
        show: Show,
        season: Season,
        season_data: url_title_details_models.Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        source_key = show.source.key
        season_episodes_file = self.season_episodes_file(season_data.id)
        backdrops = (
            self.url_title_details_file(show_key)
            .parsed()
            .data.url_v2.node.content.full_backdrops
        )
        parsed_episodes = season_episodes_file.parsed_episodes()
        last_number = highest_episode_number(
            season_episode.content.episode_number for season_episode in parsed_episodes
        )
        for index, season_episode in enumerate(parsed_episodes):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                season_episode.id,
            )
            if not self._episode_is_outdated(
                existing_episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            # An episode with no offer at all is on no service, so there is no
            # buy box offers file for it to be read out of.
            if not season_episode.unique_offer_count:
                continue

            buy_box_offers = self.buy_box_offers_file(season_episode.id)
            episode_info = self._find_matching_episode(
                source_key,
                buy_box_offers.parsed().data.node,
            )
            if not episode_info:
                continue

            # For a little bit of variety in the images, rotate through the backdrop
            # images so every episode doesn't have the same image.
            backdrop_image = backdrops[index % len(backdrops)].backdrop_url

            new_episode = Episode(
                url=self._clean_external_url(episode_info.standard_web_url),
                key=season_episode.id,
                name=season_episode.content.title,
                description=season_episode.content.short_description,
                duration=season_episode.content.runtime * 60,
                sort_order=season_episode.content.episode_number,
                episode_number=season_episode.content.episode_number,
                data_timestamp=self.episode_data_timestamp(
                    season_episode.id,
                    season.key,
                    show_key,
                ),
                image_url=self._images_base_url + backdrop_image,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                new_episode,
                season,
                existing_episode,
                show_key,
                MediaType.tv,
                last_number,
            )

    # TODO: Validate
    def _upsert_movie_episode(
        self,
        show: Show,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> str | None:
        source_key = show.source.key
        parsed_data = self.url_title_details_file(show_key).parsed()
        episode_info = self._find_matching_episode(
            source_key,
            parsed_data.data.url_v2.node,
        )
        if not episode_info:
            return None

        existing_episode = Episode.get_from_memory(
            self.session,
            season,
            episode_info.id,
        )
        if not self._episode_is_outdated(
            existing_episode,
            season.key,
            show_key,
            force=force,
        ):
            return episode_info.id

        node = parsed_data.data.url_v2.node
        new_episode = Episode(
            url=self._clean_external_url(episode_info.standard_web_url),
            key=episode_info.id,
            name=node.content.title,
            description=node.content.short_description,
            duration=node.content.runtime * 60,
            sort_order=0,
            episode_number=0,
            data_timestamp=self.episode_data_timestamp(
                episode_info.id,
                season.key,
                show_key,
            ),
            release_date=self._date_to_datetime(node.content.original_release_date),
            air_date=self._date_to_datetime(node.content.original_release_date),
            season_id=season.id,
        )
        self._merge_and_upsert_episode(
            new_episode,
            season,
            existing_episode,
            show_key,
            MediaType.movie,
        )
        return episode_info.id
