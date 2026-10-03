# TODO: Validate
from datetime import UTC, datetime
from typing import override

from sqlmodel import Session, select

from app.episodes.models import Episode
from app.titles.models import Title
from app.titles.service.linking import link_title, old_link_title_to_tmdb
from app.tmdb_media.filters import is_not_linked
from plugins.AdultSwim import AdultSwim
from plugins.Amazon import Amazon
from plugins.Crunchyroll import Crunchyroll
from plugins.DisneyPlus import DisneyPlus
from plugins.Hulu import Hulu
from plugins.ParamountPlus import ParamountPlus
from plugins.Peacock import Peacock
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import AbstractPlugin
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator import PluginValidator
from tests.plugins.plugin_validator.database import no_channel_initialization
from tests.plugins.plugin_validator.log_stats import log_stats


# TODO: Validate
class LinkerTests[PluginT: AbstractPlugin](PluginValidator[PluginT]):
    import_time = datetime(2026, 9, 23, tzinfo=UTC)
    restrict_registered_plugins = False
    unlinkable_episode_names: tuple[str, ...] = ()

    # TODO: Validate
    @override
    def _initialize_plugins(self, session: Session) -> None:
        with no_channel_initialization([TMDB]):
            TMDB.initialize_plugin(session)
        super()._initialize_plugins(session)

    # TODO: Validate
    def link_titles(self, session: Session) -> None:
        for title in self.plugin_titles(session):
            link_title(session, title)
        session.flush()
        session.expire_all()

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        self.link_titles(session)

    # TODO: Validate
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert episodes, "The import produced no episodes to link."
        unlinked = [
            episode.key
            for episode in episodes
            if not episode.tmdb_episode_links
            and episode.name not in self.unlinkable_episode_names
        ]
        assert not unlinked, f"Episodes with no TMDB episode link: {unlinked}"


# TODO: Validate
class TestSubDubEpisodes(LinkerTests[DisneyPlus]):
    """Test episodes that are basically identical except for being Sub or Dub."""

    plugin_class = DisneyPlus
    title_key = "993d48dc-d507-47cb-8cca-23e6794f6f66"
    urls = ("/browse/entity-{title_key}",)


# TODO: Validate
class TestSubDubEpisodes2(TestSubDubEpisodes):
    title_key = "f5d4278b-6acb-4a63-a7a2-eab91de2611e"


# TODO: Validate
class TestMisnumberedEpisodes(LinkerTests[DisneyPlus]):
    plugin_class = DisneyPlus
    title_key = "a9f7811c-8610-4458-b8db-7e0e195d6ae6"
    urls = ("/browse/entity-{title_key}",)


# TODO: Validate
class TestSubDubEpisodes3(LinkerTests[Hulu]):
    plugin_class = Hulu
    series_id = "f5d4278b-6acb-4a63-a7a2-eab91de2611e"
    urls = ("/series/{series_id}",)


# TODO: Validate
class TestRenamedEpisodes(LinkerTests[Hulu]):
    plugin_class = Hulu
    series_id = "9c91ffa3-dc20-48bf-8bc5-692e37c76d88"
    urls = ("/series/{series_id}",)


# TODO: Validate
class TestHuluAttackOnTitan(LinkerTests[Hulu]):
    plugin_class = Hulu
    series_id = "9c91ffa3-dc20-48bf-8bc5-692e37c76d88"
    urls = ("/series/{series_id}",)
    unlinkable_episode_names = (
        "S0E1 Attack on Titan Final Season Part 2 - PV 2",
        "S1E25 (Sub) The Wall/Stohess District Raid, Part 3",
    )

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert episodes, "The import produced no episodes to link."

        unlinked = sorted(
            f"S{episode.season.season_number}E{episode.episode_number} {episode.name}"
            for episode in episodes
            if not episode.tmdb_episode_links
        )
        expected = sorted(self.unlinkable_episode_names)
        assert unlinked == expected, (
            f"Episodes with no TMDB episode link: {unlinked} Expected: {expected}"
        )


# TODO: Validate
class TestScoredTwoWayNameMatches(LinkerTests[Hulu]):
    plugin_class = Hulu
    series_id = "699df5c5-3fd5-4021-a344-a60b42483d0d"
    urls = ("/series/{series_id}",)
    two_part_episode_key = "9d4ce495-b41d-4a39-8a54-b5de29158682"

    # TODO: Validate
    @staticmethod
    def label(episode: Episode) -> str:
        return (
            f"S{episode.season.season_number}E{episode.episode_number} "
            f"{episode.duration}s {episode.name}"
        )

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert len(episodes) == 618, (  # noqa: PLR2004
            f"Hulu lists 618 episodes for this series, found {len(episodes)}."
        )

        wrong: list[str] = []
        for episode in episodes:
            if episode.season.season_number == 0:
                if episode.tmdb_episode_links:
                    wrong.append(f"Extra is linked: {self.label(episode)}")
                continue

            if episode.duration is None:
                wrong.append(f"Episode has no duration: {self.label(episode)}")
                continue

            if episode.key == self.two_part_episode_key:
                continue

            holds_two_episodes = 1200 <= episode.duration <= 1500  # noqa: PLR2004
            if holds_two_episodes and episode.tmdb_episode_links:
                wrong.append(f"Pairing is linked: {self.label(episode)}")
            if not holds_two_episodes and not episode.tmdb_episode_links:
                wrong.append(f"Episode is not linked: {self.label(episode)}")

        assert not wrong, "\n".join(["", *wrong])


# TODO: Validate
class TestSplitEpisodes(LinkerTests[Amazon]):
    plugin_class = Amazon
    title_key = "0HV1F820S9I36TNRPPM3CQYYF5"
    urls = ("/detail/{title_key}",)


# TODO: Validate
class TestMovieTemp(LinkerTests[Crunchyroll]):
    plugin_class = Crunchyroll
    title_key = "G1XHJVWD3"
    urls = ("/series/{title_key}",)


# TODO: Validate
class MovieLinkerTests[PluginT: AbstractPlugin](LinkerTests[PluginT]):
    tmdb_movie_url: str

    def link_movie(self, session: Session) -> None:
        imported = TMDB(session).validate_and_import_url(self.tmdb_movie_url)
        movie = session.exec(
            select(Title).where(
                is_not_linked(Title),
                Title.key == imported[0].title.key,
            ),
        ).one()
        for title in self.plugin_titles(session):
            old_link_title_to_tmdb(session, title, movie, "Manual: Selection")

    @override
    def link_titles(self, session: Session) -> None:
        super().link_titles(session)
        self.link_movie(session)
        session.flush()
        session.expire_all()


# TODO: Validate
class TestAttackOnTitan(MovieLinkerTests[Crunchyroll]):
    plugin_class = Crunchyroll
    title_key = "GR751KNZY"
    urls = ("/series/{title_key}",)
    unlinkable_episode_names = ("PV",)
    tmdb_movie_url = "https://www.themoviedb.org/movie/1333100"


# TODO: Validate
class TestRelinkWithTwoTmdbTitles(MovieLinkerTests[Crunchyroll]):
    plugin_class = Crunchyroll
    title_key = "GR751KNZY"
    urls = ("/series/{title_key}",)
    tmdb_movie_url = "https://www.themoviedb.org/movie/1333100"
    expected_links = (
        (
            "Night of the Graduation Ceremony - Humanity Rises Again (2)",
            "The Night of the Closing Ceremony: Humanity's Comeback (2)",
        ),
        (
            "First Battle - Battle of Trost (1)",
            "First Battle: The Struggle for Trost (1)",
        ),
    )

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert episodes, "The import produced no episodes to link."

        titles = self.plugin_titles(session_with_files)
        linked_tmdb_names = sorted(
            link.tmdb_title.name for title in titles for link in title.tmdb_title_links
        )
        assert len(linked_tmdb_names) == 2, (  # noqa: PLR2004
            f"Expected the title to be linked to a film and a series, "
            f"found {linked_tmdb_names}"
        )

        by_name = {episode.name: episode for episode in episodes}
        wrong: list[str] = []
        for name, tmdb_name in self.expected_links:
            episode = by_name.get(name)
            if episode is None:
                wrong.append(f"{name} was not imported")
                continue
            linked = sorted(
                link.tmdb_episode.name or "" for link in episode.tmdb_episode_links
            )
            if linked != [tmdb_name]:
                wrong.append(f"{name} is linked to {linked}, expected [{tmdb_name!r}]")
        assert not wrong, "\n".join(["", *wrong])


# TODO: Validate
class TestGintama(LinkerTests[Crunchyroll]):
    """Gintama has some weird episodes that are worth testing."""

    plugin_class = Crunchyroll
    title_key = "GYQ4MKDZ6"
    urls = ("/series/{title_key}",)

    # TODO: Validate
    def episode(self, session: Session, key: str) -> Episode:
        return next(
            episode for episode in self.plugin_episodes(session) if episode.key == key
        )

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        assert self.episode(session_with_files, "GRWEX2GJR").is_linked

        linked_classics = [
            episode.key
            for episode in self.plugin_episodes(session_with_files)
            if episode.name and "Gintama Classic" in episode.name and episode.is_linked
        ]
        assert not linked_classics, (
            "Gintama Classic episodes are remakes that TMDB does not list, so they "
            f"must stay unlinked: {linked_classics}"
        )


# TODO: Validate
class TestClipSeasons(LinkerTests[AdultSwim]):
    plugin_class = AdultSwim
    title_key = "ballmastrz-9009"
    urls = ("/videos/{title_key}",)

    # TODO: Validate
    @staticmethod
    def is_clip(episode: Episode) -> bool:
        return episode.season.key.startswith("clip-")

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert episodes, "The import produced no episodes to link."

        linked_clips = [
            episode.key
            for episode in episodes
            if self.is_clip(episode) and episode.tmdb_episode_links
        ]
        assert not linked_clips, (
            "Clips are excerpts rather than episodes of the title, so TMDB does not "
            f"list them and they must stay unlinked: {linked_clips}"
        )

        unlinked = [
            episode.key
            for episode in episodes
            if not self.is_clip(episode) and not episode.tmdb_episode_links
        ]
        assert not unlinked, f"Episodes with no TMDB episode link: {unlinked}"


# TODO: Validate
class TestClipsSeason(LinkerTests[ParamountPlus]):
    plugin_class = ParamountPlus
    title_key = "csi-vegas"
    urls = ("/shows/{title_key}/",)

    # TODO: Validate
    @staticmethod
    def is_clip(episode: Episode) -> bool:
        return episode.season.season_number == 0 and episode.season.name == "Clips"

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        clips = [episode for episode in episodes if self.is_clip(episode)]
        assert clips, "The import produced no clips season to leave unlinked."

        linked_clips = [episode.key for episode in clips if episode.tmdb_episode_links]
        assert not linked_clips, (
            "Clips are excerpts rather than episodes of the title, so TMDB does not "
            f"list them and they must stay unlinked: {linked_clips}"
        )

        unmarked_clips = [
            episode.key for episode in clips if episode.tmdb_absent_at is None
        ]
        assert not unmarked_clips, (
            f"Clips that were not marked as absent from TMDB: {unmarked_clips}"
        )

        validated_clips = [
            episode.key
            for episode in clips
            if episode.tmdb_episode_validated_at is not None
        ]
        assert not validated_clips, (
            "Marking a clip absent from TMDB is the linker's own reading rather than "
            f"a user's, so it must not count as validated: {validated_clips}"
        )


# TODO: Validate
class TestNumberedEpisodeNames(LinkerTests[Amazon]):
    plugin_class = Amazon
    title_key = "0GJTGLAG0LNO6Q0HYOQ67M768N"
    urls = ("/detail/{title_key}",)


# TODO: Validate
class TestSpinOffSeason(MovieLinkerTests[Crunchyroll]):
    plugin_class = Crunchyroll
    title_key = "GRWEW95KR"
    urls = ("/series/{title_key}",)
    tmdb_movie_url = "https://www.themoviedb.org/movie/566466"
    solo_camping_season_key = "GY5P02W3Y"
    movie_season_key = "GRJQC18W2"

    # TODO: Validate
    @classmethod
    def is_solo_camping(cls, episode: Episode) -> bool:
        return episode.season.key == cls.solo_camping_season_key

    # TODO: Validate
    @classmethod
    def is_movie(cls, episode: Episode) -> bool:
        return episode.season.key == cls.movie_season_key

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        episodes = self.plugin_episodes(session_with_files)
        assert episodes, "The import produced no episodes to link."

        movie_episodes = [episode for episode in episodes if self.is_movie(episode)]
        assert movie_episodes, "The import produced no movie season to link."
        unlinked_movie = [
            episode.key for episode in movie_episodes if not episode.tmdb_episode_links
        ]
        assert not unlinked_movie, (
            "The movie the title was manually matched to must be picked up without a "
            f"match of its own: {unlinked_movie}"
        )

        solo_camping = [
            episode for episode in episodes if self.is_solo_camping(episode)
        ]
        assert solo_camping, "The import produced no solo camping season."
        linked_solo_camping = [
            episode.key for episode in solo_camping if episode.tmdb_episode_links
        ]
        assert not linked_solo_camping, (
            "The solo camping season is a spin off that TMDB does not list under this "
            f"title, so it must stay unlinked: {linked_solo_camping}"
        )

        unlinked = [
            episode.key
            for episode in episodes
            if not self.is_solo_camping(episode) and not episode.tmdb_episode_links
        ]
        assert not unlinked, f"Episodes with no TMDB episode link: {unlinked}"


# TODO: Validate
class TestSeasnn2ToSeason0Special(LinkerTests[Amazon]):
    plugin_class = Amazon
    title_key = "0G9UKNOYX3HCEAQEZ4UGEQJ02K"
    urls = ("/detail/{title_key}",)


# TODO: Validate
class TestSeasnn2ToSeason0SpecialCrunchyroll(LinkerTests[Crunchyroll]):
    plugin_class = Crunchyroll
    title_key = "G1XHJV2X9"
    urls = ("/series/{title_key}",)


# TODO: Validate
class TestPeacockLaid(LinkerTests[Peacock]):
    plugin_class = Peacock
    urls = ("https://www.peacocktv.com/watch/asset/tv/laid/8568714747501460112",)

    # TODO: Validate
    @override
    def test_linker(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self), frozen_clock(self.import_time):
            self.link_titles(session_with_files)

        titles = self.plugin_titles(session_with_files)
        assert titles, "The import produced no titles to link."
        linked_tmdb_names = sorted(
            link.tmdb_title.name or ""
            for title in titles
            for link in title.tmdb_title_links
        )
        assert linked_tmdb_names == ["Laid"], (
            f"Expected the title to be linked to Laid, found {linked_tmdb_names}"
        )
