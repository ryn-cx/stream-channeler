# TODO: Validate
from typing import override

from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.validator import Validator


def crunchyroll_urls(path: str, slug: str) -> tuple[str, ...]:
    locales = ("", "/de", "/pt-br")
    suffixes = ("", "/", f"/{slug}")
    return tuple(
        f"{locale}/{path}{suffix}" for locale in locales for suffix in suffixes
    )


class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    """Validate all Crunchyroll content."""

    plugin_class = Crunchyroll


class CrunchyrollStandardTests(StandardTests[Crunchyroll], CrunchyrollValidator):
    pass


class CrunchyrollUpdateSourceTests(
    UpdateSourceTests[Crunchyroll],
    CrunchyrollValidator,
):
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # Source.update will mock download a new browse file, this file will then
        # be used to set Source.data_timestamp, then Source.update_at will be set
        # to the interval the source is scheduled at after Source.data_timestamp.
        # TODO: More accurate timestamp checking
        validator = validator.incremented(Source, "update_at")

        # Source.update will mock download a new browse file that includes a mock
        # new entry for the show. There is no way to tell what part of the show
        # the entry is for, so the show and all of its seasons are marked.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # The existing seasons may or may not already have an update_at value.
        return validator.populated_or_decremented(Season, "update_at")


class InvalidCrunchyrollURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll
