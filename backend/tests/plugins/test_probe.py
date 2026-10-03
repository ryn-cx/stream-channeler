from typing import override

from sqlmodel import Session

from plugins.DisneyPlus import DisneyPlus
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.test_linker import LinkerTests


class TestProbe(LinkerTests[DisneyPlus]):
    plugin_class = DisneyPlus
    title_key = "a9f7811c-8610-4458-b8db-7e0e195d6ae6"
    urls = ("/browse/entity-{title_key}",)

    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with frozen_clock(self.import_time):
            self.link_titles(session_with_files)
        for episode in self.plugin_episodes(session_with_files):
            print(
                "ROW",
                "|",
                episode.season.season_number,
                "|",
                episode.episode_number,
                "|",
                episode.duration,
                "|",
                len(episode.tmdb_episode_links),
                "|",
                "; ".join(
                    f"S{link.tmdb_episode.season.season_number}"
                    f"E{link.tmdb_episode.episode_number} {link.tmdb_episode.name}"
                    f" [{link.note}]"
                    for link in episode.tmdb_episode_links
                ),
                "|",
                episode.name,
            )
        for title in self.plugin_titles(session_with_files):
            for tmdb_title in title.tmdb_titles:
                for season in tmdb_title.seasons:
                    for tmdb_episode in season.episodes:
                        print(
                            "TMDB",
                            "|",
                            season.season_number,
                            "|",
                            tmdb_episode.episode_number,
                            "|",
                            len(tmdb_episode.linked_episodes),
                            "|",
                            tmdb_episode.name,
                        )
        assert False
