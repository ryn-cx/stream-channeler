# TODO: Validate
import uuid
from typing import override

from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin import BasePlugin
from tests.old_mess.plugins.plugin_validator import (
    PluginValidator,
    UpdatePluginTests,
    UpdateTests,
    URLTests,
)
from tests.old_mess.plugins.plugin_validator.canonical_links import SEPARATOR
from tests.old_mess.plugins.plugin_validator.log_stats import log_stats
from tests.old_mess.plugins.plugin_validator.validator import Validator


# TODO: Validate
class TMDBValidator(PluginValidator[TMDB]):
    plugin_class = TMDB
    urls = (
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
    @override
    def update_plugin_validator(self, session: Session, plugin: Plugin) -> Validator:
        """Expect the refresh to move when the catalogue is next due.

        Every other plugin schedules its next run off a `Source`, which is left
        where it was by an update of the plugin itself. TMDB's titles hang off
        the plugin row, so the row that says how current they are is the same
        row that says when they are next read.
        """
        validator = super().update_plugin_validator(session, plugin)
        return validator.incremented(plugin.id, "update_at")

    # TODO: Validate
    @override
    def generic_update_validator(
        self,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Validator:
        """Leave TMDB's own row unjudged when another plugin's copy is updated.

        Updating a copy reads the title again, which moves the row saying how
        current TMDB's catalogue is - but only when the update reached for a
        TMDB file, and which files an update reaches for is decided by how stale
        the copy's own files are. What the title itself came out as is the same
        either way, and that is what the canonical rows are checked for.
        """
        validator = super().generic_update_validator(entity)
        if isinstance(entity, Plugin):
            return validator
        return validator.ignored(
            self.imported_plugin.plugin.id,
            "modified_at",
            "data_timestamp",
            "update_at",
        )


# TODO: Validate
class ForcedReimportTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that a forced re-import makes the links an import made a second time.

    Which episode of a website's listing is which TMDB episode is worked out by
    the import that stores the listing, so a listing that was stored before the
    matching knew how to pair them keeps whatever it was left with. A forced
    re-import is what is left to fix those, and it can only fix them if it
    reaches every plugin the first import reached rather than stopping at the
    title it is given, which is what an import of a stored title otherwise does.

    The links are taken off by hand rather than by importing against an older
    version of the code, so what the re-import has to put back is exactly what
    the first import worked out.
    """

    # TODO: Validate
    def _detached_plugins(self, session: Session) -> list[Plugin]:
        """Return a detached copy of every plugin's tree, not only the one under test.

        An import stores a listing under the plugin of the service that streams
        it, and TMDB's own tree holds none of the copies whose links this is
        about.
        """
        return [
            self._load_model(Plugin, self._dump_model(plugin))
            for plugin in self.select_plugins_with_children(session)
        ]

    # TODO: Validate
    def _canonical_episode_keys(self, session: Session) -> dict[str, str | None]:
        """Name the TMDB episode each stored episode points at, by key.

        By key because the id of a canonical row says nothing on its own, and
        under the path of keys leading to the copy so that an episode is
        compared against itself.
        """
        keys: dict[str, str | None] = {}
        for plugin in self.select_plugins_with_children(session):
            for source in plugin.sources:
                for show in source.shows:
                    for season in show.seasons:
                        for episode in season.episodes:
                            path = SEPARATOR.join(
                                (
                                    plugin.key,
                                    source.key,
                                    show.key,
                                    season.key,
                                    episode.key,
                                ),
                            )
                            canonical = episode.canonical_episode
                            keys[path] = canonical.key if canonical else None
        return keys

    # TODO: Validate
    @staticmethod
    def _unlink_canonical_episodes(session: Session) -> set[uuid.UUID]:
        """Make every episode stand for itself again, and return which were changed."""
        copies = session.exec(
            select(Episode).where(col(Episode.canonical_episode_id).is_not(None)),
        ).all()
        unlinked = {episode.id for episode in copies}
        for episode in copies:
            episode.canonical_episode = None
        session.flush()
        session.expire_all()
        return unlinked

    # TODO: Validate
    def forced_reimport_validator(self, unlinked: set[uuid.UUID]) -> Validator:
        """Rules for the state a forced re-import leaves behind.

        An episode whose link was taken off is written twice - once to take it
        off and once to put it back - so it is the one thing that cannot come out
        of this as it went in.
        """
        validator = Validator()
        for episode_id in unlinked:
            validator.incremented(episode_id, "modified_at")
        return validator

    # TODO: Validate
    def test_forced_reimport_relinks_canonical_episodes(
        self,
        session_with_files: Session,
    ) -> None:
        url = self.url
        assert url

        self._import_url(session_with_files)
        original_plugins = self._detached_plugins(session_with_files)
        original_links = self._canonical_episode_keys(session_with_files)

        unlinked = self._unlink_canonical_episodes(session_with_files)
        assert unlinked, "The import pointed no episode at a TMDB episode."

        with log_stats(self):
            self.imported_plugin = self.plugin_class(session_with_files)
            self.imported_plugin.import_url(url, force=True)
        session_with_files.flush()
        session_with_files.expire_all()

        assert self._canonical_episode_keys(session_with_files) == original_links

        validator = self.forced_reimport_validator(unlinked)
        actual_plugins = self._detached_plugins(session_with_files)
        assert [plugin.key for plugin in original_plugins] == [
            plugin.key for plugin in actual_plugins
        ]
        for original, actual in zip(original_plugins, actual_plugins, strict=True):
            self.validate_state(validator, original, actual)


# TODO: Validate
class TestMovieWithMixedCrunchyroll(
    URLTests[TMDB],
    UpdatePluginTests[TMDB],
    UpdateTests[TMDB],
    ForcedReimportTests[TMDB],
    TMDBValidator,
):
    media_type = "movie"
    parse_url_response = "566466"
    show_slug = "laid-back-camp-the-movie"


# TODO: Validate
class TestTVWithMixedCrunchyroll(
    URLTests[TMDB],
    UpdatePluginTests[TMDB],
    UpdateTests[TMDB],
    TMDBValidator,
):
    media_type = "tv"
    parse_url_response = "76075"
    show_slug = "laid-back-camp"
    urls = (
        *TMDBValidator.urls,
        # Only a show has seasons, so the page listing them is a sub-page a
        # movie's URLs cannot carry.
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )


# TODO: Validate
class SeededSiblingTests(
    URLTests[TMDB],
    UpdatePluginTests[TMDB],
    UpdateTests[TMDB],
):
    seed_url: str

    # TODO: Validate
    def _seed(self, session: Session) -> None:
        self.plugin_class(session).import_url(self.seed_url)
        session.flush()
        session.expire_all()

    # TODO: Validate
    @override
    def _import_url(
        self,
        session: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        self._seed(session)
        return super()._import_url(session, url)

    # TODO: Validate
    @override
    def test_import_url(self, session_with_files: Session) -> None:
        self._seed(session_with_files)
        super().test_import_url(session_with_files)

    # TODO: Validate
    @override
    def test_import_url_variants(
        self,
        session_with_files: Session,
        url_variant: str,
    ) -> None:
        self._seed(session_with_files)
        super().test_import_url_variants(session_with_files, url_variant)


# TODO: Validate
class TestSeededMovieWithMixedCrunchyroll(
    SeededSiblingTests,
    TestMovieWithMixedCrunchyroll,
):
    seed_url = "themoviedb.org/tv/76075"


# TODO: Validate
class TestSeededTVWithMixedCrunchyroll(
    SeededSiblingTests,
    TestTVWithMixedCrunchyroll,
):
    seed_url = "themoviedb.org/movie/566466"
