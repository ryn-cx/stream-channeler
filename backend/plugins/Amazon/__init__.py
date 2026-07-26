# TODO: Validate
"""Amazon Prime Video plugin."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar, override
from urllib.parse import quote_plus

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Amazon.handlers import AmazonURLHandler, DetailURLHandler
from plugins.Amazon.helpers import HelperMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # DTZ007 - Amazon release dates carry no timezone; localized below.
        parsed = datetime.strptime(value, "%b %d, %Y").date()  # noqa: DTZ007
    except ValueError:
        return None
    return tz_datetime.combine(parsed, datetime.min.time())


class Amazon(HelperMixin, URLHandlerPlugin[AmazonURLHandler], register=True):
    """Amazon Prime Video plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[AmazonURLHandler], ...]] = (DetailURLHandler,)
    TMDB_PROVIDER_NAMES = ("Amazon Prime Video", "Amazon Video", "Prime Video")

    @classmethod
    @override
    def _domain(cls) -> str:
        return "amazon.com"

    @classmethod
    def _detail_url(cls, asin: str) -> str:
        return cls.build_url(f"gp/video/detail/{asin}")

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series or Movie]\n"
            "> `https://www.amazon.com/dp/B095RHJ52R`\n\n"
        )

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(
            f"s?url=search-alias%3Dinstant-video&field-keywords={quote_plus(query)}",
        )

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="Amazon Prime Video",
            favicon_url="https://www.amazon.com/favicon.ico",
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
            show = self._upsert_movie(source, show_key, force=force)
        else:
            show = self._upsert_series_show(source, show_key, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        return show

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_page(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=page.series_title(),
                description=page.synopsis(),
                media_type="TV Show",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=7),
            )
            show = self._merge_and_upsert_show(
                show,
                source,
                show_check.record,
                show_key,
                "tv",
            )
        else:
            show = show_check.record

        self._upsert_tv_seasons(show, show_key, force=force)

        return show

    def _upsert_tv_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_entry in enumerate(self._season_entries(show_key)):
            season_key = season_entry.asin
            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=self._detail_url(season_key),
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    season,
                    show,
                    season_check.record,
                    show_key,
                    "tv",
                )
            else:
                season = season_check.record

            self._upsert_tv_episodes(season, season_key, show_key, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        season_key: str,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self.detail_page(season_key).episodes()):
            episode_check = self._episode_check(
                item.asin,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            episode = Episode(
                key=item.asin,
                name=item.title,
                episode_number=item.episode_number,
                url=self._detail_url(item.asin),
                description=item.synopsis,
                image_url=item.image_url,
                duration=item.duration,
                release_date=_parse_date(item.release_date),
                air_date=_parse_date(item.release_date),
                sort_order=sort_order,
                episode_identifier=f"{self.plugin_key()} {item.asin}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                episode,
                season,
                episode_check.record,
                show_key,
                "tv",
            )

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_page(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                media_type="Movie",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=30),
            )
            show = self._merge_and_upsert_show(
                show,
                source,
                show_check.record,
                show_key,
                "movie",
            )
        else:
            show = show_check.record

        self._upsert_movie_season(show, show_key, force=force)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        if season_check := self._season_check(show, show_key, show_key, force=force):
            season = Season(
                key=show_key,
                season_number=0,
                sort_order=0,
                url=self._detail_url(show_key),
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                season,
                show,
                season_check.record,
                show_key,
                "movie",
            )
        else:
            season = season_check.record

        self._upsert_movie_episode(season, show_key, force=force)

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        if episode_check := self._episode_check(
            show_key,
            season,
            show_key,
            force=force,
        ):
            page = self.detail_page(show_key)
            episode = Episode(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                episode_number=0,
                sort_order=0,
                release_date=_parse_date(page.release_date()),
                episode_identifier=f"{self.plugin_key()} {show_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                episode,
                season,
                episode_check.record,
                show_key,
                "movie",
            )
