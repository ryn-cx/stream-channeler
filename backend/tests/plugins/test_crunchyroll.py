# TODO: Validate
from sqlmodel import Session, select

from app.config import settings
from app.episodes.models import Episode
from app.titles.models import Title
from app.users.models import User
from app.watches.identifiers import watched_tmdb_record_ids
from app.watches.schemas import WatchCreate
from app.watches.service.management import create_watch
from plugins.Crunchyroll import Crunchyroll
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator import PluginValidator, StandardTests
from tests.plugins.plugin_validator.stored_files import (
    mock_update,
)


# TODO: Validate
class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/series/{parse_url_response}",
        "/series/{parse_url_response}/",
        "/series/{parse_url_response}/{title_slug}",
        "/de/series/{parse_url_response}/{title_slug}",
    )


class TestSeries(StandardTests[Crunchyroll], CrunchyrollValidator):
    parse_url_response = "GRWEW95KR"
    title_slug = "laid-back-camp"


class TestDeletedSeries(StandardTests[Crunchyroll], CrunchyrollValidator):
    # It appears that when a series is removed from crunchyroll the main title page will
    # remain but there will be no seasons or episodes.
    parse_url_response = "GRVN31D5Y"
    title_slug = "encouragement-of-climb"


# TODO: Validate
class TestWeirdSeasonName(StandardTests[Crunchyroll], CrunchyrollValidator):
    parse_url_response = "G6E58N5VY"
    title_slug = "hinako-note"


# TODO: Validate
class TestMovieByKeyword(StandardTests[Crunchyroll], CrunchyrollValidator):
    """Some movies are identified by using a keyword instead of a tag."""

    parse_url_response = "GKEH2G7GG"
    title_slug = "hells"


# TODO: Validate
class TestUntitledEpisodes(StandardTests[Crunchyroll], CrunchyrollValidator):
    parse_url_response = "G62487M9Y"
    title_slug = "dropkick-on-my-devil"


# TODO: Validate
class TestManyEpisodes(StandardTests[Crunchyroll], CrunchyrollValidator):
    parse_url_response = "GRMG8ZQZR"
    title_slug = "one-piece"
