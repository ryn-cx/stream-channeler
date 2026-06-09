# TODO: Validate
import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from difflib import get_close_matches
from itertools import chain
from typing import cast, override

from just_scrape.custom_buy_box_offers import (
    response_models as custom_buy_box_offers_models,
)
from just_scrape.url_title_details import response_models as url_title_details_models
from loguru import logger
from sqlmodel import col, select

from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import strict_re, tz_datetime
from plugins.JustWatch.files import (
    FileMixin,
    NewTitleBucket,
    NewTitles,
    ProvidersLocale,
)
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    PluginSearchResultSource,
    URLImportResult,
)


class JustWatch(FileMixin, register=True):
    _VERSION = "0.0.1"

    @override
    def initialize_source(self) -> None:
        if self.plugin.data_timestamp is None:
            providers_file = self.providers_locale_file()
            providers_file.download_if_outdated()

            self._upsert_sources(providers_file)

            bucket = self.new_titles_bucket_file(providers_file.data_timestamp)
            bucket.download_if_outdated()
            bucket.database_record.extra = "Incomplete"

            self._download_new_titles_bucket_if_missing()

            self.plugin.data_timestamp = self.plugin_data_timestamp()
            self.plugin.set_update_at(self.plugin.data_timestamp + timedelta(days=1))

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/TV Show on Hulu]\n"
            "> `Hulu justwatch.com/us/tv-show/breaking-bad`\n\n"
            "> [!TIP/Movie on Netflix]\n"
            "> `Netflix justwatch.com/us/movie/inception`\n\n"
            "> [!WARNING/TV Show on All Websites (may cause duplicates)]\n"
            "> `justwatch.com/us/tv-show/breaking-bad`\n\n"
            "> [!WARNING/Movie on All Websites (may cause duplicates)]\n"
            "> `Netflix justwatch.com/us/movie/inception`\n\n"
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self.parse_url(url)
        source_name = parsed["source_name"]
        show_key = parsed["show_key"]
        season_key = parsed["season_key"]

        if not (shows := self._preload_show(show_key=show_key).all()):
            self._validate_show_key(show_key, url)
            _cache = (
                self._download_show_files(show_key),
                self._preload_sources().all(),
            )
            shows = self._upsert_shows(show_key)

        return self._create_url_import_results(shows, source_name, season_key)

    @classmethod
    @override
    def parse_url(cls, url: str) -> dict[str, str]:
        match = strict_re.strict_match(cls._url_regex(), url)
        return {
            "source_name": match.group("source_name"),
            "show_key": match.group("show_key"),
            "locale": match.group("locale"),
            "season_key": match.group("season_key"),
        }

    def _validate_show_key(self, show_key: str, url: str) -> None:
        series_json = self.url_title_details_file(show_key)
        series_json.download_if_outdated()
        self.raise_invalid_url_if_no_content(series_json, url)

    def _create_url_import_results(
        self,
        shows: Sequence[Show],
        source_name: str | None,
        season_key: str | None,
    ) -> list[URLImportResult]:
        # If the user specified a source name get the show for that source only,
        # otherwise get all shows.
        filtered_shows = self._get_matching_show(shows, source_name)

        # If no season was specified all shows should be returned.
        if not season_key:
            return [
                URLImportResult(show=show, is_whitelist=False)
                for show in filtered_shows
            ]

        # If the URL that the user used was for a specific season only return that
        # season. The season.id value in the database is the internal one used by
        # JustWatch, but the user's input will be the external one so the easiest way
        # to match a season is by using the actual season number.
        season_number = int(season_key.split("-")[-1])
        return [
            URLImportResult(show=show, seasons=[season], is_whitelist=True)
            for show in filtered_shows
            if (
                season := next(
                    s for s in show.seasons if s.season_number == season_number
                )
            )
            and season.episodes
        ]

    def _get_matching_show(
        self,
        shows: Sequence[Show],
        source_name: str | None,
    ) -> Sequence[Show]:
        """Filters shows based on the closest match to the given source name.

        Returns:
        - If source_name is None or empty, all shows are returned.
        - If source_name is a valid string, the show with the closest matching name is
        returned.

        """
        if not source_name or not shows:
            return shows

        source_name = source_name.lower()
        sources: dict[str, Show] = {
            show.source.name.lower(): show for show in shows if show.source.name
        }
        best_match = get_close_matches(source_name, sources, n=1, cutoff=0.0)
        return [sources[best_match[0]]]

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        providers_file = self.providers_locale_file()
        providers_file.download_if_outdated(self.plugin.update_at)
        self._upsert_sources(providers_file)

        _cache = plugin.sources
        self._download_latest_new_titles_bucket()
        self._process_new_titles_buckets()

        plugin.data_timestamp = self.plugin_data_timestamp()
        plugin.set_update_at(plugin.data_timestamp + timedelta(days=1))

    def _process_new_titles_buckets(self) -> None:
        for bucket in self._get_new_new_title_buckets():
            for edge in bucket.parsed_edges():
                short_name = edge.key.package.short_name
                source = Source.get_from_memory(self.session, self.plugin, short_name)
                # TODO: This is just bypassing a serious error.
                if not source:
                    continue

                new_titles_file = self.new_titles_file(source.key, edge.key.date)
                new_titles_file.download_if_outdated()
                # Files are always considered incomplete at this point because none of
                # the data has been imported yet.
                new_titles_file.database_record.extra = "Incomplete"
                source.set_update_at(source.modified_at)

            bucket.database_record.extra = None

    def _get_new_new_title_buckets(self) -> list[NewTitleBucket]:
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
                File.extra == "Incomplete",
            )
            .order_by(col(File.data_timestamp).asc())
        )
        return [
            self.new_titles_bucket_file(file)
            for file in self.session.exec(statement).all()
        ]

    @override
    def update_source(self, source: Source) -> None:
        new_titles_files = self._pending_new_titles_files(source)
        if not new_titles_files:
            msg = f"Source {source.key} has no pending new titles files to update."
            raise ValueError(msg)

        self._download_new_titles_files(new_titles_files)
        self._process_new_titles_files(source, new_titles_files)

        incomplete_minimum_timestamps: list[datetime] = []
        for new_titles_file in new_titles_files:
            minimum_timestamp = self.minimum_new_titles_timestamp(new_titles_file)

            # If the file is too new consider it incomplete because more entries may be
            # added at a later time.
            if minimum_timestamp > new_titles_file.data_timestamp:
                new_titles_file.database_record.extra = "Incomplete"
                incomplete_minimum_timestamps.append(minimum_timestamp)
            else:
                new_titles_file.database_record.extra = None

        if incomplete_minimum_timestamps:
            source.set_update_at(min(incomplete_minimum_timestamps))
        else:
            source.update_at = None

        source.data_timestamp = max(
            new_titles_file.data_timestamp for new_titles_file in new_titles_files
        )

    def _process_new_titles_files(
        self,
        source: Source,
        new_titles_files: list[NewTitles],
    ) -> None:
        _cache = source.shows

        for file in new_titles_files:
            source = Source.get_one(self.session, self.plugin, file.source_key)
            _cache_sources = self._preload_sources(
                file.source_key,
                preload_seasons=True,
            ).all()

            logger.info("Processing new titles file: {}", file.database_record.key)
            for edge in file.parsed_edges():
                full_path = edge.node.content.full_path
                match edge.node.field__typename:
                    case "Season":
                        show_key, season_key = full_path.rsplit("/", 1)
                    case "Movie":
                        show_key = full_path
                        season_key = full_path
                    case _:
                        msg = f"Unknown field__typename: {edge.node.field__typename}"
                        raise ValueError(msg)

                # Need to match on show because if this is a new season looking up an
                # existing season would fail.
                if show := Show.get_from_memory(self.session, source, show_key):
                    logger.info("Matched show: {}", show.name or show_key)
                    _cache_seasons = show.seasons
                    # If the season was found only the season needs to be updated.
                    if season := Season.get_from_memory(self.session, show, season_key):
                        season.set_update_at(file.data_timestamp)
                    # If no season was found this contains a new episode so the show
                    # needs to be updated.
                    else:
                        show.set_update_at(file.data_timestamp)

    @classmethod
    def _url_regex(cls) -> str:
        # Example URLs:
        # https://www.justwatch.com/us/tv-show/kaiju-no-8
        # https://www.justwatch.com/us/tv-show/kaiju-no-8/season-1
        # https://www.justwatch.com/us/movie/weapons-2026
        # E501 - Splitting the regex into multiple lines does not make it more readable.
        url_string = r"(?P<show_key>\/(?P<locale>[a-zA-Z]{2})\/(?:tv-show|movie)\/.+?)(?:\/|$)(?:(?P<season_key>.+?)(?:\/|$))?"
        source_name_regex = r"^(?P<source_name>.*?)"
        domain_regex = cls._domain_regex()
        # Remove the start of string character to support choosing a source by placing
        # it in front of the URL.
        domain_regex = domain_regex.replace("^", "", 1)

        return source_name_regex + domain_regex + url_string

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["justwatch.com"]

    @property
    def _images_base_url(self) -> str:
        """Return the base URL for images."""
        return f"https://images.{self._domain()}"

    def _format_image_url(
        self,
        url: str | None,
        profile: int = 100,
        format: str = "jpeg",  # noqa: A002 - TODO: Rename argument shadowing builtin
    ) -> str | None:
        """Format a JustWatch image URL with the correct base URL and profile."""
        if url is None:
            return None
        return f"{self._images_base_url}{url}".replace(
            "{profile}",
            f"s{profile}",
        ).replace("{format}", format)

    def _favicon_url(self, provider: dict[str, str]) -> str | None:
        """Build a provider's icon URL.

        JustWatch serves provider icons at
        ``{base}/icon/<id>/s<profile>/<technical_name>.jpeg``.
        """
        icon_url = self._format_image_url(provider["icon_url"], profile=100)
        if icon_url is None:
            return None
        return f"{icon_url}/{provider['technical_name']}.jpeg"

    @staticmethod
    def _clean_external_url(url: str) -> str:
        """Extract the actual external URL from JustWatch's redirect wrapper."""
        match = re.search(r"r=(https?://[^&]+)", url)
        return match.group(1) if match else url

    @staticmethod
    def _find_matching_episode(
        source_key: str,
        node: custom_buy_box_offers_models.Node | url_title_details_models.Node,
    ) -> custom_buy_box_offers_models.Offer | None:
        """Find the offer that matches the source key.

        The just_scrape models split offers into separate categorized lists
        (flatrate, buy, rent, free, fast); walk them all and return the first
        item whose package short_name matches.
        """
        for item in chain(
            node.flatrate,
            node.buy,
            node.rent,
            node.free,
            node.fast,
        ):
            if item is None:
                continue
            if item.package.short_name == source_key:
                return cast("custom_buy_box_offers_models.Offer", item)
        return None

    def _sources_with_offers(  # type: ignore[override]
        self,
        show_key: str,
    ) -> list[tuple[str, custom_buy_box_offers_models.Offer]]:
        """Return (source_key, offer) pairs for all sources that have offers."""
        parsed_json = self.url_title_details_file(show_key).parsed()
        results: list[tuple[str, custom_buy_box_offers_models.Offer]] = []
        if not parsed_json.data.url_v2.node.offers:
            return results

        seen: set[str] = set()
        for offer in parsed_json.data.url_v2.node.offers:
            if offer.package.short_name not in seen:
                seen.add(offer.package.short_name)
                results.append((offer.package.short_name, offer))  # type: ignore[arg-type]

        return results

    def _upsert_sources(self, providers_file: ProvidersLocale) -> None:
        for provider in providers_file.parsed():
            source = Source.get_from_memory(
                self.session,
                self.plugin,
                provider["short_name"],
            )

            source = Source(
                key=provider["short_name"],
                name=provider["clear_name"],
                favicon_url=self._favicon_url(provider),
                plugin_id=self.plugin.id,
            ).upsert(self.plugin, source)

            # Only use the data timestamp from the providers file for the initial
            # import. If the source already has a data_timestamp keep it because it will
            # be based on data from the new titles files which are more up to date.
            if not source.data_timestamp:
                source.data_timestamp = providers_file.data_timestamp

    def _upsert_shows(self, show_key: str) -> list[Show]:
        shows: list[Show] = []
        for source_key, _ in self._sources_with_offers(show_key):
            source = Source.get_one_from_memory(self.session, self.plugin, source_key)
            shows.append(self._upsert_show(source, show_key))
        return shows

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)

        parsed_json = self.url_title_details_file(show_key).parsed()
        offer = next(
            offer
            for source_key, offer in self._sources_with_offers(show_key)
            if source_key == source.key
        )
        media_type = self._media_type(show_key)
        show = Show(
            key=show_key,
            name=parsed_json.data.url_v2.node.content.title,
            media_type=media_type,
            description=parsed_json.data.url_v2.node.content.short_description,
            url=self._clean_external_url(offer.standard_web_url),
            image_url=self._images_base_url
            + parsed_json.data.url_v2.node.content.full_backdrops[0].backdrop_url,
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_seasons(show, show_key)

        self.soft_delete_missing_seasons(show_key)

        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        if self._media_type(show_key) == "TV Show":
            self._upsert_show_seasons(show, show_key)
        else:
            self._upsert_movie_season(show, show_key)

    def _upsert_show_seasons(self, show: Show, show_key: str) -> None:
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
            season = Season(
                image_url=image_url,
                # TODO: Should I use the other ID that matches the URL instead?
                key=season_data.id,
                sort_order=season_data.content.season_number,
                season_number=season_data.content.season_number,
                data_timestamp=self.season_data_timestamp(season_data.id, show_key),
                show_id=show.id,
            ).upsert(show, existing_season)
            self._upsert_season_episodes(show, season, season_data, show_key)
            self.soft_delete_missing_episodes(season.key)

    def _upsert_movie_season(self, show: Show, show_key: str) -> None:
        parsed_json = self.url_title_details_file(show_key).parsed()
        node_id = parsed_json.data.url_v2.node.id
        existing_season = Season.get_from_memory(self.session, show, node_id)
        season = Season(
            key=node_id,
            name="Movie",
            sort_order=0,
            data_timestamp=self.season_data_timestamp(node_id, show_key),
            show_id=show.id,
        ).upsert(show, existing_season)
        upserted_key = self._upsert_movie_episode(show, season, show_key)
        expected_keys = [upserted_key] if upserted_key else []
        season.soft_delete_missing_children(expected_keys)

    @staticmethod
    def _date_to_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return tz_datetime.combine(value, datetime.min.time())

    def _upsert_season_episodes(
        self,
        show: Show,
        season: Season,
        season_data: url_title_details_models.Season,
        show_key: str,
    ) -> None:
        source_key = show.source.key
        custom_season_episodes_file = self.custom_season_episodes_file(
            season_data.id,
        )
        backdrops = (
            self.url_title_details_file(show_key)
            .parsed()
            .data.url_v2.node.content.full_backdrops
        )
        for i, season_episode in enumerate(
            custom_season_episodes_file.parsed_episodes(),
        ):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                season_episode.id,
            )
            episode_timestamp = self.episode_data_timestamp(
                season_episode.id,
                season.key,
                show_key,
            )
            if (
                existing_episode
                and existing_episode.data_timestamp == episode_timestamp
                and existing_episode.deleted_at is None
            ):
                continue

            buy_box_offers = self.custom_buy_box_offers_file(season_episode.id)
            episode_info = self._find_matching_episode(
                source_key,
                buy_box_offers.parsed().data.node,
            )
            if not episode_info:
                continue

            # For a little bit of variety in the images, rotate through the backdrop
            # images so every episode doesn't have the same image.
            backdrop_image = backdrops[i % len(backdrops)].backdrop_url

            Episode(
                url=self._clean_external_url(episode_info.standard_web_url),
                key=season_episode.id,
                name=season_episode.content.title,
                description=season_episode.content.short_description,
                duration=season_episode.content.runtime * 60,
                sort_order=season_episode.content.episode_number,
                episode_number=season_episode.content.episode_number,
                data_timestamp=episode_timestamp,
                image_url=self._images_base_url + backdrop_image,
                release_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
                air_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

    def _upsert_movie_episode(
        self,
        show: Show,
        season: Season,
        show_key: str,
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
        episode_timestamp = self.episode_data_timestamp(
            episode_info.id,
            season.key,
            show_key,
        )
        if (
            existing_episode
            and existing_episode.data_timestamp == episode_timestamp
            and existing_episode.deleted_at is None
        ):
            return episode_info.id

        node = parsed_data.data.url_v2.node
        Episode(
            url=self._clean_external_url(episode_info.standard_web_url),
            key=episode_info.id,
            name=node.content.title,
            description=node.content.short_description,
            duration=node.content.runtime * 60,
            sort_order=0,
            episode_number=0,
            data_timestamp=episode_timestamp,
            release_date=self._date_to_datetime(node.content.original_release_date),
            air_date=self._date_to_datetime(node.content.original_release_date),
            season_id=season.id,
        ).upsert(season, existing_episode)
        return episode_info.id

    # TODO: Consider caching this if it is slow.
    def _get_source_lookup(self) -> dict[str, dict[str, str]]:
        """Build a short_name -> {clear_name, icon_url} mapping from ProvidersLocale."""
        providers_file = self.providers_locale_file()
        providers_file.download_if_outdated()
        return {
            provider["short_name"]: {
                "clear_name": provider["clear_name"],
                "icon_url": self._favicon_url(provider),  # type: ignore[dict-item]
            }
            for provider in providers_file.parsed()
        }

    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_titles_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=30)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()

        source_lookup = self._get_source_lookup()

        results: list[PluginSearchResult] = []
        for edge in parsed.data.search_titles.edges:
            node = edge.node
            poster_url = node.content.poster_url
            image_url = (
                f"{self._images_base_url}{poster_url.replace('{profile}', 's166').replace('{format}', 'webp')}"
                if poster_url
                else None
            )

            seen_sources: dict[str, PluginSearchResultSource] = {}
            for offer in node.offers:
                short_name = offer.package.short_name
                if short_name not in seen_sources:
                    info = source_lookup.get(short_name)
                    seen_sources[short_name] = PluginSearchResultSource(
                        name=info["clear_name"] if info else short_name,
                        icon_url=info["icon_url"] if info else None,
                    )

            media_type = "TV Show" if node.object_type == "SHOW" else "Movie"
            results.append(
                PluginSearchResult(
                    title=node.content.title,
                    url=f"justwatch.com{node.content.full_path}",
                    year=node.content.original_release_year,
                    image_url=image_url,
                    media_type=media_type,
                    sources=list(seen_sources.values()),
                ),
            )

        return PluginSearchResults(
            has_source_selection=True,
            results=results,
        )
