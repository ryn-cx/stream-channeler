# TODO: Validate
from __future__ import annotations

from abc import ABC
from itertools import groupby
from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.plugins.identifiers import TMDB_VIDEOS_SOURCE_KEY
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.keys import watch_identifier
from app.tmdb_media.tmdb import get_media_type_and_tmdb_id
from app.utils import tz_datetime
from plugins.TMDB.files import MoviesVideos, TVSeriesVideos
from plugins.TMDB.shared import TMDBImporter
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from datetime import datetime

    from tminidb.movie.videos.models import Result as MovieVideo
    from tminidb.tv_series.videos.models import Result as TvSeriesVideo

    from app.sources.models import Source


# TODO: Validate
class TMDBVideosImporter(TMDBImporter, ABC):
    # TODO: Validate
    def movies_videos_file(self, tmdb_movie_id: int) -> MoviesVideos:
        return self._cached_file(MoviesVideos, tmdb_movie_id)

    # TODO: Validate
    def tv_series_videos_file(self, tmdb_tv_title_id: int) -> TVSeriesVideos:
        return self._cached_file(TVSeriesVideos, tmdb_tv_title_id)

    # TODO: Validate
    def videos_file(self, tmdb_title_key: str) -> MoviesVideos | TVSeriesVideos:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(tmdb_title_key)
        if media_type == TMDBMediaType.movie:
            return self.movies_videos_file(tmdb_media_id)
        return self.tv_series_videos_file(tmdb_media_id)

    # TODO: Validate
    @staticmethod
    def videos_title_key(tmdb_title_key: str) -> str:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(tmdb_title_key)
        return f"{media_type} {tmdb_media_id}"

    # TODO: Validate
    @staticmethod
    def video_url(video: MovieVideo | TvSeriesVideo) -> str:
        return {
            "YouTube": f"https://www.youtube.com/watch?v={video.key}",
            "Vimeo": f"https://vimeo.com/{video.key}",
        }[video.site]

    # TODO: Validate
    @staticmethod
    def video_thumbnail_url(video: MovieVideo | TvSeriesVideo) -> str | None:
        if video.site == "YouTube":
            return f"https://i.ytimg.com/vi/{video.key}/hqdefault.jpg"
        return None

    # TODO: Validate
    def _videos_source(self) -> Source:
        if TMDB_VIDEOS_SOURCE_KEY not in self._sources:
            self._sources[TMDB_VIDEOS_SOURCE_KEY] = self.upsert_source(
                TMDB_VIDEOS_SOURCE_KEY,
            )
        return self._sources[TMDB_VIDEOS_SOURCE_KEY]

    # TODO: Validate
    def _existing_videos_title(self, tmdb_title_key: str) -> Title | None:
        return self._preload_title(
            self.videos_title_key(tmdb_title_key),
            TMDB_VIDEOS_SOURCE_KEY,
            preload_episodes=True,
        ).one_or_none()

    # TODO: Validate
    @override
    def _delete_title(self, title: Title) -> None:
        if videos_title := self._existing_videos_title(title.key):
            videos_title.soft_delete()
        super()._delete_title(title)

    # TODO: Validate
    def _upsert_videos_title(self, tmdb_title: Title) -> None:
        existing_title = self._existing_videos_title(tmdb_title.key)
        videos_file = self.videos_file(tmdb_title.key)
        videos: list[MovieVideo | TvSeriesVideo] = sorted(
            videos_file.parsed().results,
            key=lambda video: (video.type, video.published_at),
        )
        if not videos:
            if existing_title:
                existing_title.soft_delete()
            return

        media_type, tmdb_media_id = get_media_type_and_tmdb_id(tmdb_title.key)
        data_timestamp = videos_file.record_data_timestamp
        source = self._videos_source()
        videos_title = Title(
            key=self.videos_title_key(tmdb_title.key),
            name=tmdb_title.name,
            description=tmdb_title.description,
            url=f"{self.tmdb_url(media_type, tmdb_media_id)}/videos",
            image_url=tmdb_title.image_url,
            thumbnail_url=tmdb_title.thumbnail_url,
            poster_url=tmdb_title.poster_url,
            poster_thumbnail_url=tmdb_title.poster_thumbnail_url,
            year=tmdb_title.year,
            original_language=tmdb_title.original_language,
            media_type=MediaType.series,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)

        videos_by_type = {
            video_type: list(type_videos)
            for video_type, type_videos in groupby(videos, key=lambda video: video.type)
        }
        for sort_order, (video_type, type_videos) in enumerate(videos_by_type.items()):
            self._upsert_videos_season(
                videos_title,
                video_type,
                sort_order,
                type_videos,
                data_timestamp,
            )
        videos_title.soft_delete_missing_children(videos_by_type)
        self._link_videos_title(videos_title, tmdb_title)

    # TODO: Validate
    def _upsert_videos_season(
        self,
        videos_title: Title,
        video_type: str,
        sort_order: int,
        videos: list[MovieVideo | TvSeriesVideo],
        data_timestamp: datetime,
    ) -> None:
        existing_season = Season.get_from_memory(self.session, videos_title, video_type)
        season = Season(
            key=video_type,
            name=video_type,
            season_number=None,
            sort_order=sort_order,
            data_timestamp=data_timestamp,
            title_id=videos_title.id,
        ).upsert(videos_title, existing_season)
        for episode_sort_order, video in enumerate(videos):
            existing_episode = Episode.get_from_memory(self.session, season, video.id)
            Episode(
                key=video.id,
                watch_identifier=watch_identifier(video.site, video.key),
                name=video.name,
                url=self.video_url(video),
                image_url=self.video_thumbnail_url(video),
                thumbnail_url=self.video_thumbnail_url(video),
                air_date=video.published_at,
                sort_order=episode_sort_order,
                data_timestamp=data_timestamp,
                season_id=season.id,
            ).upsert(season, existing_episode)
        season.soft_delete_missing_children(video.id for video in videos)

    # TODO: Validate
    def _link_videos_title(self, videos_title: Title, tmdb_title: Title) -> None:
        if videos_title.tmdb_title_links:
            return
        self.session.add(
            TitleTmdbTitle(
                title_id=videos_title.id,
                tmdb_title_id=tmdb_title.id,
                note="Automatic: TMDB Videos",
                linked_title=videos_title,
                tmdb_title=tmdb_title,
            ),
        )
        videos_title.link_status = "Linked"
        videos_title.tmdb_title_validated_at = tz_datetime.now()
