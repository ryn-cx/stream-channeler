# TODO: Validate
from plugins.Crunchyroll import Crunchyroll
from tests.plugins.plugin_validator_alt import PluginValidatorAlt, StandardTestsAlt


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
