# TODO: Validate


from datetime import timedelta
from typing import override

from freezegun import freeze_time
from sqlmodel import Session

from app.shows.models import Show
from plugins.TMDB import TMDB
from plugins.Tubi import Tubi
from tests.old_mess.plugins.plugin_validator.context_managers import mock_update
from tests.plugins.plugin_validator_alt import (
    PluginValidatorAlt,
    UpdatePluginTestsAlt,
    UpdateTestsAlt,
    URLTestsAlt,
)
from tests.plugins.plugin_validator_alt.database import IMPORT_TIME, UPDATE_TIME
from tests.plugins.plugin_validator_alt.log_stats import log_stats

SEPARATOR = "/"
"""What separates the keys naming where an episode sits."""


# TODO: Validate
class TMDBValidatorAlt(PluginValidatorAlt[TMDB]):
    plugin_class = TMDB
    urls: tuple[str, ...] = (
        "/{media_type}/{parse_url_response}",
        "/{media_type}/{parse_url_response}/",
        "/{media_type}/{parse_url_response}?language=en-US",
        # A title's own sub-pages carry the id too, and the watch page is what a
        # link to where a title streams points at.
        "/{media_type}/{parse_url_response}/watch?language=en-US",
        # TMDB redirects a title's slug to the canonical URL, so a pasted link
        # usually carries one.
        "/{media_type}/{parse_url_response}-{show_slug}",
    )



# TODO: Validate
class TestTVShow(
    URLTestsAlt[TMDB],
    UpdatePluginTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "tv"
    parse_url_response = "107113"
    show_slug = "only-murders-in-the-building"
    urls = (
        *TMDBValidatorAlt.urls,
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )



# TODO: Validate
class TestArcher(
    URLTestsAlt[TMDB],
    UpdatePluginTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "tv"
    parse_url_response = "10283"
    show_slug = "archer"
    urls = (
        *TMDBValidatorAlt.urls,
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )


# TODO: Validate
class TestWelcomeToTheJapariPark(
    URLTestsAlt[TMDB],
    UpdatePluginTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "tv"
    parse_url_response = "88459"
    show_slug = "welcome-to-the-japari-park"
    urls = (
        *TMDBValidatorAlt.urls,
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )


# TODO: Validate
class TestLaidBackCamp(
    URLTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "tv"
    parse_url_response = "76075"
    show_slug = "laid-back-camp"
    urls = (
        *TMDBValidatorAlt.urls,
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )


# TODO: Validate
class TestSpaceGhostAndDinoBoy(
    URLTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "tv"
    parse_url_response = "3303"
    show_slug = "space-ghost-and-dino-boy"
    urls = (
        *TMDBValidatorAlt.urls,
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )


# TODO: Validate
class TestSuperman(
    URLTestsAlt[TMDB],
    UpdatePluginTestsAlt[TMDB],
    UpdateTestsAlt[TMDB],
    TMDBValidatorAlt,
):
    media_type = "movie"
    parse_url_response = "95414"
    show_slug = "superman"


# TODO: Validate
class TestSupermanRelinkedTubi(TMDBValidatorAlt):
    media_type = "movie"
    parse_url_response = "95414"
    show_slug = "superman"
    urls = ("https://www.themoviedb.org/movie/95414-superman?language=en-US",)
    relinked_url = (
        "https://tubitv.com/series/300001134/superman-original-fleischer-restoration"
    )

    # TODO: Validate
    @override
    def _initialize_extra_files(self, session: Session) -> None:
        Tubi(session).import_url(self.relinked_url)

    # TODO: Validate
    def shows_of(self, session: Session, plugin_key: str) -> list[Show]:
        return [
            show
            for show in self.all_shows(session)
            if show.source.plugin.key == plugin_key
        ]

    # TODO: Validate
    def test_forced_update_keeps_the_relinked_listing(
        self,
        session_with_files: Session,
    ) -> None:
        self.import_url(session_with_files)
        tmdb_show = self.shows_of(session_with_files, "TMDB")[0]

        listed = self.shows_of(session_with_files, "Tubi")
        assert listed, "Watchmode listed no Tubi listing to take off."
        for show in listed:
            session_with_files.delete(show)
        session_with_files.flush()
        session_with_files.expire_all()

        with freeze_time(IMPORT_TIME):
            Tubi(session_with_files).import_url(self.relinked_url, tmdb_show)
        session_with_files.flush()
        session_with_files.expire_all()

        relinked_keys = {show.key for show in self.shows_of(session_with_files, "Tubi")}
        assert relinked_keys == {"300001134"}

        with log_stats(self), freeze_time(UPDATE_TIME), mock_update():
            assert tmdb_show.data_timestamp
            tmdb_show.update_at = tmdb_show.data_timestamp + timedelta(seconds=1)
            TMDB(session_with_files).update_show(tmdb_show, force=True)
            session_with_files.flush()
        session_with_files.expire_all()

        assert {
            show.key for show in self.shows_of(session_with_files, "Tubi")
        } == relinked_keys
        self.assert_state(session_with_files, "forced_update_keeps_relinked_listing")


# # TODO: Validate
# class TestTV1(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
#     TMDBValidatorAlt,
# ):
#     """Tests a TV series.

#     The series is available on Crunchyroll, Amazon Prime Video Purchase, and Crunchyroll
#     on Amazon Prime Video.

#     Episodes also need to be matched across multiple episode groups."""

#     media_type = "tv"
#     parse_url_response = "30991"
#     show_slug = "cowboy-bebop"
#     urls = (
#         *TMDBValidatorAlt.urls,
#         # Only a show has seasons, so the page listing them is a sub-page a
#         # movie's URLs cannot carry.
#         "/{media_type}/{parse_url_response}/seasons?language=en-US",
#     )


# # TODO: Validate
# class TestTV2(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
#     TMDBValidatorAlt,
# ):
#     """Tests a TV series.

#     The series is available on Crunchyroll, Hulu, Netflix, and Crunchyroll on Amazon
#     Prime Video.
#     """

#     media_type = "tv"
#     parse_url_response = "57041"
#     show_slug = "gintama"
#     urls = (
#         *TMDBValidatorAlt.urls,
#         "/{media_type}/{parse_url_response}/seasons?language=en-US",
#     )


# # TODO: Validate
# class TestTV3(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
#     TMDBValidatorAlt,
# ):
#     media_type = "tv"
#     parse_url_response = "107113"
#     show_slug = "only-murders-in-the-building"
#     urls = (
#         *TMDBValidatorAlt.urls,
#         "/{media_type}/{parse_url_response}/seasons?language=en-US",
#     )


# # TODO: Validate
# class ForcedReimportTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
#     """Tests that a forced re-import makes the links an import made a second time.

#     Which episode of a website's listing is which TMDB episode is worked out by
#     the import that stores the listing, so a listing that was stored before the
#     matching knew how to pair them keeps whatever it was left with. A forced
#     re-import is what is left to fix those, and it can only fix them if it
#     reaches every plugin the first import reached rather than stopping at the
#     title it is given, which is what an import of a stored title otherwise does.

#     The links are taken off by hand rather than by importing against an older
#     version of the code, so what the re-import has to put back is exactly what
#     the first import worked out.
#     """

#     # TODO: Validate
#     def _canonical_episode_keys(self, session: Session) -> dict[str, str | None]:
#         """Name the TMDB episode each stored episode points at, by key.

#         By key because the id of a canonical row says nothing on its own, and
#         under the path of keys leading to the copy so that an episode is
#         compared against itself.
#         """
#         keys: dict[str, str | None] = {}
#         for plugin in self.select_plugins_with_children(session):
#             for source in plugin.sources:
#                 for show in source.shows:
#                     for season in show.seasons:
#                         for episode in season.episodes:
#                             path = SEPARATOR.join(
#                                 (
#                                     plugin.key,
#                                     source.key,
#                                     show.key,
#                                     season.key,
#                                     episode.key,
#                                 ),
#                             )
#                             canonical = episode.canonical_episode
#                             keys[path] = canonical.key if canonical else None
#         return keys

#     # TODO: Validate
#     @staticmethod
#     def _unlink_canonical_episodes(session: Session) -> int:
#         """Make every episode stand for itself again, and return how many were changed."""
#         copies = session.exec(
#             select(Episode).where(col(Episode.canonical_episode_id).is_not(None)),
#         ).all()
#         for episode in copies:
#             episode.canonical_episode = None
#         session.flush()
#         session.expire_all()
#         return len(copies)

#     # TODO: Validate
#     def test_forced_reimport_relinks_canonical_episodes(
#         self,
#         session_with_files: Session,
#     ) -> None:
#         url = self.url
#         assert url

#         self.import_url(session_with_files)
#         original_links = self._canonical_episode_keys(session_with_files)

#         unlinked = self._unlink_canonical_episodes(session_with_files)
#         assert unlinked, "The import pointed no episode at a TMDB episode."

#         with log_stats(self):
#             self.import_url(session_with_files, url, force=True)

#         assert self._canonical_episode_keys(session_with_files) == original_links
#         self.assert_state(session_with_files, "forced_reimport")

# # TODO: Validate
# class TestMovieWithMixedCrunchyroll(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
#     ForcedReimportTestsAlt[TMDB],
#     TMDBValidatorAlt,
# ):
#     media_type = "movie"
#     parse_url_response = "566466"
#     show_slug = "laid-back-camp-the-movie"


# # TODO: Validate
# class TestTVWithMixedCrunchyroll(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
#     TMDBValidatorAlt,
# ):
#     media_type = "tv"
#     parse_url_response = "76075"
#     show_slug = "laid-back-camp"
#     urls = (
#         *TMDBValidatorAlt.urls,
#         # Only a show has seasons, so the page listing them is a sub-page a
#         # movie's URLs cannot carry.
#         "/{media_type}/{parse_url_response}/seasons?language=en-US",
#     )


# # TODO: Validate
# class SeededSiblingTestsAlt(
#     URLTestsAlt[TMDB],
#     UpdatePluginTestsAlt[TMDB],
#     UpdateTestsAlt[TMDB],
# ):
#     seed_url: str

#     # TODO: Validate
#     def _seed(self, session: Session) -> None:
#         self.plugin_class(session).import_url(self.seed_url)
#         session.flush()
#         session.expire_all()

#     # TODO: Validate
#     @override
#     def _import_url(
#         self,
#         session: Session,
#         url: str | None = None,
#         *,
#         force: bool = False,
#     ) -> list[URLImportResult]:
#         self._seed(session)
#         return super()._import_url(session, url, force=force)


# # TODO: Validate
# class TestSeededMovieWithMixedCrunchyroll(
#     SeededSiblingTestsAlt,
#     TestMovieWithMixedCrunchyroll,
# ):
#     seed_url = "themoviedb.org/tv/76075"


# # TODO: Validate
# class TestSeededTVWithMixedCrunchyroll(
#     SeededSiblingTestsAlt,
#     TestTVWithMixedCrunchyroll,
# ):
#     seed_url = "themoviedb.org/movie/566466"
