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


# TODO: Validate
def crunchyroll_urls(path: str, slug: str) -> tuple[str, ...]:
    locales = ("", "/de", "/pt-br")
    suffixes = ("", "/", f"/{slug}")
    return tuple(
        f"{locale}/{path}{suffix}" for locale in locales for suffix in suffixes
    )


# TODO: Validate
class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    """Validate all Crunchyroll content."""

    plugin_class = Crunchyroll


# TODO: Validate
class CrunchyrollStandardTests(StandardTests[Crunchyroll], CrunchyrollValidator):
    pass


# TODO: Validate
class CrunchyrollUpdateSourceTests(
    UpdateSourceTests[Crunchyroll],
    CrunchyrollValidator,
):
    # TODO: Validate
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # Source.update will mock download a new browse file, this file will then
        # be used to set Source.data_timestamp, then Source.update_at will be set
        # to the interval the source is scheduled at after Source.data_timestamp.
        # TODO: More accurate timestamp checking
        # Only the source being updated, since this plugin reads two of them and
        # updating one leaves the other where it was.
        validator = validator.incremented(source.id, "update_at")

        # Source.update will mock download a new browse file that includes a mock
        # new entry for the show. There is no way to tell what part of the show
        # the entry is for, so the show and all of its seasons are marked.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # The existing seasons may or may not already have an update_at value.
        return validator.populated_or_decremented(Season, "update_at")


# TODO: Validate
class InvalidCrunchyrollURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll
