# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.DisneyPlus import DisneyPlus
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class DisneyPlusValidator(PluginValidator[DisneyPlus]):
    plugin_class = DisneyPlus

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


class DisneyPlusStandardTests(StandardTests[DisneyPlus], DisneyPlusValidator):
    pass


class EntityURLs:
    urls: tuple[str, ...] = (
        "/browse/entity-{entity_id}",
        "/browse/entity-{entity_id}/",
        "/en-gb/browse/entity-{entity_id}",
    )


class TestHuluSeries(EntityURLs, DisneyPlusStandardTests):
    entity_id = "52b8dd8a-eff2-4ed2-9b8d-7c0039df1c53"


class TestSeries(EntityURLs, DisneyPlusStandardTests):
    entity_id = "5ca4c1af-3963-471d-ab3e-0484feb9308b"


class TestMovie(EntityURLs, DisneyPlusStandardTests):
    entity_id = "6e497c43-d4da-4e12-b100-d4d38dc2a7ff"


class InvalidDisneyPlusValidator(InvalidURLValidator[DisneyPlus]):
    plugin_class = DisneyPlus


class TestInvalid(EntityURLs, InvalidDisneyPlusValidator):
    entity_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
