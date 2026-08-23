# TODO: Validate
from freezegun import freeze_time
from sqlmodel import Session, select

from app.canonical_media.keys import is_tmdb_key
from app.config import settings
from app.episodes.models import Episode
from app.shows.models import Show
from app.shows.service import update_show_episode_group, update_show_extra
from app.users.models import User
from app.watches.identifiers import watched_canonical_ids
from app.watches.schemas import WatchCreate
from app.watches.services import create_watch
from plugins.Crunchyroll import Crunchyroll
from plugins.TMDB.episode_groups import dump_extra
from tests.old_mess.plugins.plugin_validator.context_managers import mock_update
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt
from tests.plugins.plugin_validator_alt.database import IMPORT_TIME, UPDATE_TIME


# TODO: Validate
class CrunchyrollValidatorAlt(PluginValidatorAlt[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/series/{parse_url_response}",
        "/series/{parse_url_response}/",
        # Crunchyroll redirects a series to the URL carrying its slug, so a
        # pasted link usually carries one.
        "/series/{parse_url_response}/{show_slug}",
        # A locale sits in front of the path for anybody not browsing from the
        # default one, and the same series is behind every one of them.
        "/de/series/{parse_url_response}/{show_slug}",
    )


# A series Crunchyroll files under one listing that TMDB numbers as more than
# one title: the three seasons are a series, the movie is a film of its own, and
# the spinoff is a third. Each of them is a title the listing is a copy of.
# TODO: Validate
class TestMixedTMDB(StandardTestsAlt[Crunchyroll], CrunchyrollValidatorAlt):
    """Crunchyroll combines the Laid Back camp tv show and movie into a single series."""

    parse_url_response = "GRWEW95KR"
    show_slug = "laid-back-camp"


# A series TMDB has nothing to answer with, which leaves every episode standing
# only for itself. What the linker does when it finds a title is covered by the
# tests above; this is what it does when it finds none.
# TODO: Validate
class TestNoTMDBMatchFound(StandardTestsAlt[Crunchyroll], CrunchyrollValidatorAlt):
    """Crunchyroll has a series that TMDB is not holding a title for."""

    parse_url_response = "G6DQNPE1R"
    show_slug = "ah-my-buddha"


# A series of several seasons that Crunchyroll and TMDB both file as one, which
# is neither of the awkward shapes above. The tests around it are for the
# ordinary case: the seasons line up, so every episode has a TMDB episode to be
# matched to and the numbering is read straight through.
# TODO: Validate
class TestSeries1(StandardTestsAlt[Crunchyroll], CrunchyrollValidatorAlt):
    """Crunchyroll has a multi-season series TMDB holds as one title."""

    parse_url_response = "GYQWNXPZY"
    show_slug = "fire-force"


# The order Crunchyroll follows for Detective Conan, which is one of the episode
# groups TMDB keeps beside the title's own numbering.
CRUNCHYROLL_EPISODE_GROUP = "69106aac2465062343ce84c4"


# A series long enough that TMDB and the websites carrying it disagree about how
# it is divided up, which is what an episode group is for.
# TODO: Validate
class TestSwappingEpisodeGroup(StandardTestsAlt[Crunchyroll], CrunchyrollValidatorAlt):
    """Crunchyroll numbers this series by an order of TMDB's rather than its own."""

    parse_url_response = "G6JQVM3ER"
    show_slug = "detective-conan"

    # TODO: Validate
    def tmdb_show(self, session: Session) -> Show:
        """Return the TMDB title the imported listing was matched to."""
        for show in self.all_shows(session):
            if is_tmdb_key(show.key):
                return show
        message = "The import matched no TMDB title to swap the order of"
        raise AssertionError(message)

    # TODO: Validate
    def test_swapped_episode_group(self, session_with_files: Session) -> None:
        """Read the title in a chosen order, and write down what that left.

        Set through the same service the edit screen sets it through, so what is
        recorded is what setting an order actually does: the order is checked
        against the ones TMDB holds, the title is read again in it, and every
        copy of the title is matched against the new numbering.

        On the same frozen clock the ordinary updates run on, since reading the
        title again is an update like any other and a real clock would date the
        rows differently on every run.

        Written down as a state of its own, so the seasons and numbering this
        order produces can be read against the ones the title's own order did in
        `import_url`. The episodes keep their ids across the swap, so what moves
        between the two is what the order is for.
        """
        self.import_url(session_with_files)
        tmdb_show = self.tmdb_show(session_with_files)
        with freeze_time(UPDATE_TIME), mock_update():
            update_show_extra(
                session_with_files,
                tmdb_show,
                dump_extra(CRUNCHYROLL_EPISODE_GROUP),
            )
        self.assert_state(session_with_files, "swapped_episode_group")


# A series whose episodes Crunchyroll numbers by an order TMDB keeps beside the
# title's own, without the title having been moved onto that order. The names
# are what the two agree on, and the numbers only line up once the other orders
# are read, so this is what says the linker reads them.
# TODO: Validate
class TestEpisodeGroupNameMatching(
    StandardTestsAlt[Crunchyroll],
    CrunchyrollValidatorAlt,
):
    """Crunchyroll numbers this series as one of TMDB's other orders numbers it."""

    parse_url_response = "GYVNXMVP6"
    show_slug = "cowboy-bebop"

    # TODO: Validate
    def tmdb_show(self, session: Session) -> Show:
        for show in self.all_shows(session):
            if is_tmdb_key(show.key):
                return show
        message = "The import matched no TMDB title to swap the order of"
        raise AssertionError(message)

    # TODO: Validate
    def crunchyroll_show(self, session: Session) -> Show:
        """Return the listing Crunchyroll itself carries."""
        for show in self.all_shows(session):
            if show.source.plugin.key == Crunchyroll.plugin_key():
                return show
        message = "The import wrote no Crunchyroll listing to update"
        raise AssertionError(message)

    # TODO: Validate
    def crunchyroll_episodes(self, session: Session) -> list[Episode]:
        """Every episode Crunchyroll itself carries.

        TMDB's own episodes are what everything else is matched against and
        stand for themselves, so a canonical row is not one waiting on a link
        and is no part of what these tests read.
        """
        return [
            episode
            for episode in self.all_episodes(session)
            if episode.season.show.source.plugin.key == Crunchyroll.plugin_key()
        ]

    # TODO: Validate
    def assert_every_episode_links_to_tmdb(self, session: Session) -> None:
        """Fail where an episode Crunchyroll carries stands for nothing."""
        unlinked = [
            episode.key
            for episode in self.crunchyroll_episodes(session)
            if episode.canonical_episode is None
        ]
        assert not unlinked, (
            f"These episodes were matched to no TMDB episode: {unlinked}"
        )

    # TODO: Validate
    def test_every_episode_links_to_tmdb(self, session_with_files: Session) -> None:
        """Every episode Crunchyroll carries stands for a TMDB episode.

        The listing is read in the title's own order, so an episode is only ever
        reached by a matcher that read the other orders as well. An episode
        standing for nothing is one no matcher could place, which is what this
        would catch.
        """
        self.import_url(session_with_files)
        self.assert_every_episode_links_to_tmdb(session_with_files)

    # TODO: Validate
    def test_every_episode_links_to_tmdb_after_relinking(
        self,
        session_with_files: Session,
    ) -> None:
        """Every episode is matched again once its link has been taken off.

        An import matches an episode as it writes it, so what the first test
        reads is the matching that happened alongside a listing being read for
        the first time. Here the listing is already stored and every link is
        taken off it, which leaves the update matching episodes that are all
        there is left to match - the state a listing is in whenever the matching
        is run again over rows nothing has changed.

        Forced, since the listing was read a moment ago and an update that reads
        it as current would write nothing and match nothing.
        """
        self.import_url(session_with_files)
        show = self.crunchyroll_show(session_with_files)
        for episode in self.crunchyroll_episodes(session_with_files):
            episode.canonical_episode = None
            episode.canonical_episode_locked = False
            episode.canonical_episode_note = None
        session_with_files.flush()

        with freeze_time(UPDATE_TIME), mock_update():
            self.plugin_class(session_with_files).update_show(show, force=True)
            session_with_files.flush()

        self.assert_every_episode_links_to_tmdb(session_with_files)

    # TODO: Validate
    def watching_user(self, session: Session) -> User:
        statement = select(User).where(User.email == settings.FIRST_SUPERUSER)
        return session.exec(statement).one()

    # TODO: Validate
    def crunchyroll_episode_named(self, session: Session, name: str) -> Episode:
        for episode in self.crunchyroll_episodes(session):
            if episode.name == name:
                return episode
        message = f"Crunchyroll carries no episode named {name}"
        raise AssertionError(message)

    # TODO: This test should be generalized to be a generic service test
    # TODO: Validate
    def test_watch_survives_an_episode_group_change(
        self,
        session_with_files: Session,
    ) -> None:
        blu_ray_episode_group = "606a5cf909c24c00782bbf59"
        episode_name = "Honky Tonk Women"
        episode_number = 2
        reordered_episode_number = 3

        self.import_url(session_with_files)
        user = self.watching_user(session_with_files)
        episode = self.crunchyroll_episode_named(session_with_files, episode_name)

        canonical = episode.canonical_episode
        assert canonical is not None
        assert canonical.name == episode_name
        assert canonical.episode_number == episode_number

        with freeze_time(IMPORT_TIME):
            create_watch(
                session_with_files,
                user.id,
                episode,
                WatchCreate(verified=True),
            )

        tmdb_show = self.tmdb_show(session_with_files)
        with freeze_time(UPDATE_TIME), mock_update():
            update_show_episode_group(
                session_with_files,
                tmdb_show,
                blu_ray_episode_group,
            )
            session_with_files.flush()
        session_with_files.expire_all()

        reordered = self.crunchyroll_episode_named(session_with_files, episode_name)
        reordered_canonical = reordered.canonical_episode
        assert reordered_canonical is not None
        assert reordered_canonical.name == episode_name
        assert reordered_canonical.episode_number == reordered_episode_number

        watched = set(session_with_files.exec(watched_canonical_ids(user.id)).all())
        assert watched == {reordered_canonical.id}
