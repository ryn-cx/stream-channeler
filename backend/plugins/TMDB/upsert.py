# TODO: Validate
"""Store what TMDB holds as canonical media rather than as this plugin's own.

TMDB is not a website anything can be watched on, so it has no `Source`, no
`Show` and no episodes of its own. What it has is the record of what a title
*is*, which is exactly what a canonical row holds, so a title is imported
straight into `CanonicalShow` / `CanonicalSeason` / `CanonicalEpisode`.

The `Plugin` row survives, because it still owns the `File` response cache that
every download here reads through.
"""

from __future__ import annotations

from typing import override

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_media.service import (
    canonical_episode_for,
    canonical_season_for,
    canonical_show_for,
)
from app.canonical_shows.models import CanonicalShow
from app.media.media_type import MediaType
from app.models import Visibility
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from plugins.TMDB.files import (
    air_datetime,
    backdrop_image_url,
    duration_seconds,
    poster_image_url,
    still_image_url,
    title_page_url,
)
from plugins.TMDB.helpers import HelperMixin
from plugins.TMDB.keys import (
    MOVIE_EPISODE_NUMBER,
    MOVIE_SEASON_NUMBER,
    show_key,
)


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Reads TMDB into the canonical tables."""

    # TODO: Validate
    @override
    def _upsert_plugin(
        self,
        plugin_user: User,
        existing_plugin: Plugin | None,
    ) -> Plugin:
        """Create the `Plugin` record as private.

        Nothing here is streamable, and the plugin no longer holds media of its
        own; the row exists so the `File` response cache has an owner.
        """
        return Plugin(
            key=self.plugin_key(),
            name=self.plugin_name(),
            version=self._VERSION,
            visibility=Visibility.private,
            anonymous=False,
            user_id=plugin_user.id,
        ).upsert_and_set_update_at(plugin_user, existing_plugin)

    # TODO: Validate
    @override
    def _upsert_source(self) -> Source:
        """Raise, because TMDB is nowhere anything can be watched.

        Every other plugin's source is a website with media on it. TMDB's media
        is the canonical record itself, which belongs to no source, so nothing
        should ever ask this plugin for one.
        """
        message = "TMDB holds canonical media and has no source of its own"
        raise NotImplementedError(message)

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        """Raise, because TMDB stores no `Show`.

        `import_title` is what reads a title in, and it writes canonical rows.
        """
        message = "TMDB imports titles as canonical media, not as a Show"
        raise NotImplementedError(message)

    # TODO: Validate
    def import_title(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> CanonicalShow | None:
        """Store a title and everything under it as canonical media.

        A copy of the title on any website reads these rows for whatever its own
        site does not carry, so a title is imported as soon as one of them
        resolves it rather than only when a `User` asks for it.

        Returns None when TMDB has no title for the id, which is stored as an
        empty file rather than raised, so a caller working from an id a website
        guessed at is not stopped by one that turned out to be wrong.
        """
        key = show_key(media_type, tmdb_id)
        detail_file = self._show_files(key)[0]
        detail_file.download_if_outdated()
        if not detail_file.database_record.content:
            return None

        canonical_show = self._upsert_canonical_show(media_type, tmdb_id)
        if media_type == MediaType.movie:
            self._upsert_movie(canonical_show, tmdb_id)
        else:
            for season_number in self._season_numbers(key):
                self._upsert_series_season(canonical_show, tmdb_id, season_number)
        return canonical_show

    # TODO: Validate
    def _upsert_canonical_show(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> CanonicalShow:
        """Write what TMDB says about a title onto the row standing for it."""
        if media_type == MediaType.movie:
            movie = self.movie_detail_file(tmdb_id).parsed()
            name = movie.title
            description = movie.overview
            image_url = backdrop_image_url(movie.backdrop_path) or poster_image_url(
                movie.poster_path,
            )
        else:
            series = self.show_detail_file(tmdb_id).parsed()
            name = series.name
            description = series.overview
            image_url = backdrop_image_url(series.backdrop_path) or poster_image_url(
                series.poster_path,
            )

        canonical = canonical_show_for(self.session, media_type, tmdb_id)
        canonical.url = title_page_url(media_type, tmdb_id)
        canonical.name = name
        canonical.description = description
        canonical.media_type = (
            "Movie" if media_type == MediaType.movie else "TV Show"
        )
        canonical.image_url = image_url
        return canonical

    # TODO: Validate
    def _season_numbers(self, key: str) -> list[int]:
        """Return the season numbers TMDB gives a series, read off its key file."""
        return [
            int(season_key.rsplit("/", 1)[1])
            for season_key in self._season_keys_from_file(key)
        ]

    # TODO: Validate
    def _upsert_series_season(
        self,
        canonical_show: CanonicalShow,
        tmdb_id: int,
        season_number: int,
    ) -> None:
        """Write a series season and its episodes onto their canonical rows."""
        detail = self.season_detail_file(tmdb_id, season_number).parsed()
        canonical_season = canonical_season_for(
            self.session,
            MediaType.tv,
            detail.id,
            canonical_show.id,
        )
        canonical_season.url = title_page_url(MediaType.tv, tmdb_id)
        canonical_season.name = detail.name
        canonical_season.season_number = season_number
        canonical_season.sort_order = season_number
        canonical_season.image_url = poster_image_url(detail.poster_path)

        for sort_order, episode in enumerate(detail.episodes):
            air = air_datetime(episode.air_date)
            canonical_episode = canonical_episode_for(
                self.session,
                MediaType.tv,
                episode.id,
                canonical_season.id,
            )
            self._write_episode(
                canonical_episode,
                url=title_page_url(MediaType.tv, tmdb_id),
                name=episode.name,
                description=episode.overview,
                image_url=still_image_url(episode.still_path),
                duration=duration_seconds(episode.runtime),
                air=air,
                episode_number=episode.episode_number,
                sort_order=sort_order,
            )

    # TODO: Validate
    def _upsert_movie(self, canonical_show: CanonicalShow, tmdb_id: int) -> None:
        """Write a film as a single season holding the film as its only episode."""
        movie = self.movie_detail_file(tmdb_id).parsed()
        canonical_season = canonical_season_for(
            self.session,
            MediaType.movie,
            movie.id,
            canonical_show.id,
        )
        canonical_season.url = title_page_url(MediaType.movie, tmdb_id)
        canonical_season.name = movie.title
        canonical_season.season_number = MOVIE_SEASON_NUMBER
        canonical_season.sort_order = MOVIE_SEASON_NUMBER
        canonical_season.image_url = poster_image_url(movie.poster_path)

        release = air_datetime(movie.release_date)
        canonical_episode = canonical_episode_for(
            self.session,
            MediaType.movie,
            movie.id,
            canonical_season.id,
        )
        self._write_episode(
            canonical_episode,
            url=title_page_url(MediaType.movie, tmdb_id),
            name=movie.title,
            description=movie.overview,
            image_url=backdrop_image_url(movie.backdrop_path),
            duration=duration_seconds(movie.runtime),
            air=release,
            episode_number=MOVIE_EPISODE_NUMBER,
            sort_order=MOVIE_EPISODE_NUMBER,
        )

    # TODO: Validate
    def _write_episode(  # noqa: PLR0913 - One argument per field TMDB reports.
        self,
        canonical_episode: CanonicalEpisode,
        *,
        url: str | None,
        name: str | None,
        description: str | None,
        image_url: str | None,
        duration: int | None,
        air,  # noqa: ANN001 - The parsed air date, or None.
        episode_number: int | None,
        sort_order: int,
    ) -> None:
        """Write what TMDB says about an episode onto the row standing for it."""
        canonical_episode.url = url
        canonical_episode.name = name
        canonical_episode.description = description
        canonical_episode.image_url = image_url
        canonical_episode.duration = duration
        canonical_episode.release_date = air
        canonical_episode.air_date = air
        canonical_episode.episode_number = episode_number
        canonical_episode.sort_order = sort_order

    # TODO: Validate
    def tmdb_title_url(self, media_type: MediaType, tmdb_id: int) -> str | None:
        """Return the title's page on themoviedb.org."""
        return title_page_url(media_type, tmdb_id)
