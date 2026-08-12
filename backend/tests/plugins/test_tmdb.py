# TODO: Validate
from typing import override

from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import URLImportResult
from tests.old_mess.plugins.plugin_validator import (
    PluginValidator,
    UpdatePluginTests,
    UpdateTests,
    URLTests,
)
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
class TestMovieWithMixedCrunchyroll(
    URLTests[TMDB],
    UpdatePluginTests[TMDB],
    UpdateTests[TMDB],
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
