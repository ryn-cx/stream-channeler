# TODO: Validate
# import pytest
# from sqlmodel import Session

# from app.plugins.plugins.HiDive import HiDivePlugin
# from app.plugins.plugins.utils.abstract_plugin import InvalidURLError
# from tests.plugins.helpers import get_urls
# from tests.plugins.plugin_validator import PluginValidator
# from tests.plugins.validator import Validator


# @pytest.mark.parametrize(
#     ("url"),
#     get_urls(
#         HiDivePlugin.domains(),
#         ["/season/32819", "/playlist/19813"],
#     ),
# )
# def test_is_valid_url_format(url: str) -> None:
#     url = url + "/series/GXJPK3GZJ/fake-url"
#     assert HiDivePlugin.is_valid_url_format(url)


# class HiDiveValidator(PluginValidator):
#     pass


# class TestTVShow(HiDiveValidator):
#     # Must be a TV show with recently aired episodes to properly test update_source.
#     url = "hidive.com/season/32819"
#     plugin_class = HiDivePlugin


# class TestTVShowWithMultipleSeasons(HiDiveValidator):
#     url = "hidive.com/season/19334"
#     # TODO: There are literally no TV shows with multiple seasons on HiDive to use for
#     # testing update_source.
#     skip_update_source = True
#     plugin_class = HiDivePlugin


# class TestMovie(HiDiveValidator):
#     # TODO: There are literally no recently released movies on HiDive to use for testing
#     # update_source.
#     skip_update_source = True
#     url = "hidive.com/playlist/19813"
#     plugin_class = HiDivePlugin


# def test_invalid_tv_show(db: Session) -> None:
#     url = "hidive.com/season/123456789"
#     plugin = HiDivePlugin(db)

#     with pytest.raises(
#         InvalidURLError,
#         match="Unexpected response status code: 404",
#     ):
#         plugin.import_url(url)


# def test_invalid_movie(db: Session) -> None:
#     url = "hidive.com/playlist/123456789"
#     plugin = HiDivePlugin(db)

#     with pytest.raises(
#         InvalidURLError,
#         match="Unexpected response status code: 404",
#     ):
#         plugin.import_url(url)
