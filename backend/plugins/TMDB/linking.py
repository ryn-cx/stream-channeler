# TODO: Validate

from __future__ import annotations

from collections.abc import Sequence

from app.episodes.linking.tmdb_facts import EpisodeNumbering
from app.files.models import File
from plugins.TMDB.shared import TMDBShared


# TODO: Validate
class TMDBLinking(TMDBShared):
    # TODO: Validate
    def preload_episode_translations_files(
        self,
        numberings: Sequence[EpisodeNumbering],
    ) -> Sequence[File]:
        return self._get_files_by_keys(
            file_keys=[
                self.tv_episodes_translations_file(
                    tmdb_tv_show_id=numbering.tmdb_show_id,
                    season_number=numbering.season_number,
                    episode_number=numbering.episode_number,
                ).file_key()
                for numbering in numberings
            ],
        )

    def preload_movie_translations_files(
        self,
        tmdb_movie_ids: Sequence[int],
    ) -> Sequence[File]:
        return self._get_files_by_keys(
            [
                self.movies_translations_file(tmdb_movie_id).file_key()
                for tmdb_movie_id in tmdb_movie_ids
            ],
        )

    # TODO: Validate
    def translated_episode_names(
        self,
        tmdb_tv_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> Sequence[str]:
        """Return every language's name for one episode of a title.

        An episode's translations are the one thing about a TMDB episode that is
        not stored alongside it, so whatever matches an episode by name reads
        them through here.
        """
        translations = self.tv_episodes_translations_file(
            tmdb_tv_show_id=tmdb_tv_show_id,
            season_number=season_number,
            episode_number=episode_number,
        ).parsed()
        return [translation.data.name for translation in translations.translations]

    # TODO: Validate
    def translated_movie_names(self, tmdb_movie_id: int) -> Sequence[str]:
        """Return every language's title for one film.

        A film's translations are not stored alongside it, the same way an
        episode's are not, so whatever matches a film by name reads them through
        here.
        """
        translations = self.movies_translations_file(tmdb_movie_id).parsed()
        return [
            translation.data.title
            for translation in translations.translations
            if translation.data and translation.data.title
        ]

    # TODO: Validate
    def alternate_episode_numbers(
        self,
        tmdb_tv_show_id: int,
    ) -> dict[int, dict[int, frozenset[str]]]:
        groups = self.tv_series_episode_groups_file(tmdb_tv_show_id).parsed()

        numbers: dict[int, dict[int, set[str]]] = {}
        for option in groups.results:
            detail = self.tv_episode_groups_details_file(option.id).parsed()
            for group in detail.groups:
                for number, episode in enumerate(group.episodes, start=1):
                    order_names = numbers.setdefault(episode.id, {}).setdefault(
                        number,
                        set(),
                    )
                    order_names.add(detail.name)
        return {
            episode_id: {
                number: frozenset(order_names)
                for number, order_names in episode_numbers.items()
            }
            for episode_id, episode_numbers in numbers.items()
        }
