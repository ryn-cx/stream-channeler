# TODO: Validate

from __future__ import annotations

from typing import override

from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.shared import TMDBSearch


# TODO: Validate
class TMDBLinking(TMDBSearch):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    # TODO: Validate
    def alternate_episode_numbers(
        self,
        tmdb_tv_title_id: int,
    ) -> dict[int, dict[int, frozenset[str]]]:
        groups = self.tv_series_episode_groups_file(tmdb_tv_title_id).parsed()

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
