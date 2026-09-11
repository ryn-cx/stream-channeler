# TODO: Validate
import json
from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session

from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.tmdb import (
    tmdb_title_key,
)
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.TMDB import TMDB
from plugins.TMDB.files import TVSeasonsWatchProviders, TVSeriesWatchProviders
from plugins.utils.constants import INCOMPLETE_STATUS
from tests.app.plugins.utils import create_random_plugin
from tests.app.seasons.utils import create_random_season
from tests.app.sources.utils import create_random_source
from tests.app.titles.utils import create_random_title


# TODO: Validate
def _sync_title_providers(
    session: Session,
    title_key: str,
    *stored: File,
) -> None:
    """Sync the title's providers, then read the `stored` rows back.

    A plugin reads and writes its files through a session of its own, so the row
    a test put in place and the row the sync wrote to are two objects standing
    for the same record. The sync's writes are pushed out and the test's objects
    are dropped, so reading one asks the database rather than answering with what
    the test set.
    """
    plugin = TMDB(session)
    plugin.sync_title_watch_providers(title_key)
    plugin.session.flush()
    for record in stored:
        session.expire(record)


# TODO: Validate
def _providers_body(tmdb_id: int, provider_names: list[str]) -> str:
    return json.dumps(
        {
            "id": tmdb_id,
            "results": {
                "US": {
                    "link": f"https://www.themoviedb.org/tv/{tmdb_id}/watch",
                    "flatrate": [
                        {
                            "logo_path": f"/{name}.jpg",
                            "provider_id": index,
                            "provider_name": name,
                            "display_priority": index,
                        }
                        for index, name in enumerate(provider_names, start=1)
                    ],
                },
            },
        },
    )


# TODO: Validate
def _store_file(  # noqa: PLR0913
    session: Session,
    plugin: Plugin,
    key: str,
    content: str,
    data_timestamp: datetime,
    update_at: datetime | None,
) -> File:
    file = File(
        key=key,
        content=content,
        data_timestamp=data_timestamp,
        update_at=update_at,
        plugin_id=plugin.id,
        extra={},
    )
    session.add(file)
    session.flush()
    return file


# TODO: Validate
def _store_title_providers(  # noqa: PLR0913
    session: Session,
    plugin: Plugin,
    tmdb_id: int,
    downloaded_at: date,
    provider_names: list[str],
    data_timestamp: datetime,
    update_at: datetime | None = None,
) -> File:
    return _store_file(
        session,
        plugin,
        TVSeriesWatchProviders(session, plugin, tmdb_id, downloaded_at).file_key(),
        _providers_body(tmdb_id, provider_names),
        data_timestamp,
        update_at,
    )


# TODO: Validate
def _store_season_providers(  # noqa: PLR0913
    session: Session,
    plugin: Plugin,
    tmdb_id: int,
    season_number: int,
    downloaded_at: date,
    provider_names: list[str],
    data_timestamp: datetime,
    update_at: datetime | None = None,
) -> File:
    return _store_file(
        session,
        plugin,
        TVSeasonsWatchProviders(
            session,
            plugin,
            tmdb_id,
            season_number,
            downloaded_at,
        ).file_key(),
        _providers_body(tmdb_id, provider_names),
        data_timestamp,
        update_at,
    )


# TODO: Validate
@pytest.fixture
def tmdb_plugin(function_scoped_session: Session) -> Plugin:
    plugin = create_random_plugin(function_scoped_session, key="TMDB")
    create_random_source(function_scoped_session, plugin, key="TMDB")
    return plugin


# TODO: Validate
@pytest.fixture
def tmdb_title(function_scoped_session: Session, tmdb_plugin: Plugin) -> Title:
    return create_random_title(
        function_scoped_session,
        tmdb_plugin.sources[0],
        key=tmdb_title_key(TMDBMediaType.tv, 1399),
    )


# TODO: Validate
def _linked_listing(
    session: Session,
    canonical: Title,
    plugin_key: str,
    data_timestamp: datetime,
) -> tuple[Title, Season]:
    plugin = create_random_plugin(session, key=plugin_key)
    source = create_random_source(session, plugin, key=plugin_key)
    listing = create_random_title(
        session,
        source,
        is_linked=True,
        update_at=None,
        data_timestamp=data_timestamp,
    )
    season = create_random_season(
        session,
        listing,
        update_at=None,
        data_timestamp=data_timestamp,
    )
    session.add(
        TitleTmdbTitle(title_id=listing.id, tmdb_title_id=canonical.id),
    )
    session.flush()
    session.expire(canonical, ["linked_titles"])
    return listing, season


# TODO: Validate
class TestSyncWatchProviders:
    # TODO: Validate
    def test_a_provider_that_appeared_marks_its_listing_and_seasons(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Hulu",
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        newest = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert listing.update_at == newest.data_timestamp
        assert season.update_at == newest.data_timestamp

    # TODO: Validate
    def test_a_provider_that_left_marks_its_listing(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, _season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Netflix",
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        newest = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            [],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert listing.update_at == newest.data_timestamp

    # TODO: Validate
    def test_a_listing_of_a_provider_that_did_not_move_is_left_alone(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        netflix, netflix_season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Netflix",
            stored_at,
        )
        hulu, _hulu_season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Hulu",
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert netflix.update_at is None
        assert netflix_season.update_at is None
        assert hulu.update_at is not None

    # TODO: Validate
    def test_identical_files_mark_nothing(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Netflix",
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert listing.update_at is None
        assert season.update_at is None

    # TODO: Validate
    def test_a_provider_no_plugin_carries_marks_nothing(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Netflix",
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix", "A Service Nothing Imports"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert listing.update_at is None
        assert season.update_at is None

    # TODO: Validate
    def test_a_season_file_marks_the_same_records_the_title_file_would(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Hulu",
            stored_at,
        )
        _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        newest = _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_season_watch_providers(
            tmdb_title.key,
            1,
        )

        assert listing.update_at == newest.data_timestamp
        assert season.update_at == newest.data_timestamp

    # TODO: Validate
    def test_a_season_sync_leaves_the_title_file_alone(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        older_title_file = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        newer_title_file = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )
        _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            tz_datetime.now().date(),
            ["Netflix"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_season_watch_providers(
            tmdb_title.key,
            1,
        )

        assert older_title_file.extra == {}
        assert newer_title_file.extra == {}

    # TODO: Validate
    def test_a_title_sync_leaves_the_season_files_alone(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        older_season_file = _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        newer_season_file = _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix"],
            tz_datetime.now(),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert older_season_file.extra == {}
        assert newer_season_file.extra == {}

    # TODO: Validate
    def test_a_movie_title_is_left_alone(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
    ) -> None:
        movie = create_random_title(
            function_scoped_session,
            tmdb_plugin.sources[0],
            key=tmdb_title_key(TMDBMediaType.movie, 27205),
        )
        listing, _season = _linked_listing(
            function_scoped_session,
            movie,
            "Netflix",
            tz_datetime.now() - timedelta(days=30),
        )

        TMDB(function_scoped_session).sync_title_watch_providers(movie.key)

        assert listing.update_at is None


# TODO: Validate
class TestWatchProvidersFileStatus:
    # TODO: Validate
    def test_only_the_newest_file_is_left_incomplete(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        oldest = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=60),
        )
        middle = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 15),
            ["Netflix", "Hulu"],
            tz_datetime.now() - timedelta(days=30),
        )
        newest = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Hulu"],
            tz_datetime.now(),
        )

        _sync_title_providers(
            function_scoped_session,
            tmdb_title.key,
            oldest,
            middle,
            newest,
        )

        assert oldest.status is None
        assert middle.status is None
        assert newest.status == INCOMPLETE_STATUS

    # TODO: Validate
    def test_a_completed_file_is_not_compared_again(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored_at = tz_datetime.now() - timedelta(days=30)
        listing, _season = _linked_listing(
            function_scoped_session,
            tmdb_title,
            "Hulu",
            stored_at,
        )
        older = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            stored_at,
        )
        older.status = None
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix", "Hulu"],
            tz_datetime.now(),
        )
        function_scoped_session.flush()

        TMDB(function_scoped_session).sync_title_watch_providers(tmdb_title.key)

        assert listing.update_at is None

    # TODO: Validate
    def test_a_lone_file_is_left_incomplete(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        only = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix"],
            tz_datetime.now(),
        )

        _sync_title_providers(function_scoped_session, tmdb_title.key, only)

        assert only.status == "Incomplete"


# TODO: Validate
class TestWatchProvidersFileKeys:
    # TODO: Validate
    def test_a_title_file_is_keyed_by_the_day_it_was_downloaded(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
    ) -> None:
        file = TVSeriesWatchProviders(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
        )
        assert file.file_key() == "TV Series/Watch Providers/1399/2026-08-01.json"

    # TODO: Validate
    def test_a_season_file_is_keyed_by_its_season_and_that_day(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
    ) -> None:
        file = TVSeasonsWatchProviders(
            function_scoped_session,
            tmdb_plugin,
            1399,
            2,
            date(2026, 8, 1),
        )
        assert file.file_key() == "TV Seasons/Watch Providers/1399/2/2026-08-01.json"

    # TODO: Validate
    def test_asking_for_no_day_answers_with_the_newest_stored_file(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
    ) -> None:
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=30),
        )
        newest = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 15),
            ["Hulu"],
            tz_datetime.now(),
        )

        file = TMDB(function_scoped_session).tv_series_watch_providers_file(1399)

        assert file.file_key() == newest.key

    # TODO: Validate
    def test_asking_for_no_day_before_anything_is_stored_answers_with_today(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,  # noqa: ARG002
    ) -> None:
        file = TMDB(function_scoped_session).tv_series_watch_providers_file(1399)

        today = tz_datetime.now().date().isoformat()
        assert file.file_key() == f"TV Series/Watch Providers/1399/{today}.json"

    # TODO: Validate
    def test_a_season_file_of_one_season_is_not_read_as_anothers(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
    ) -> None:
        stored = _store_season_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            1,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now(),
        )
        plugin = TMDB(function_scoped_session)

        assert plugin.tv_seasons_watch_providers_file(1399, 1).file_key() == stored.key
        today = tz_datetime.now().date().isoformat()
        assert (
            plugin.tv_seasons_watch_providers_file(1399, 2).file_key()
            == f"TV Seasons/Watch Providers/1399/2/{today}.json"
        )


# TODO: Validate
class TestStaggeredMonthlyUpdateAt:
    # TODO: Validate
    def test_the_day_a_file_falls_due_on_does_not_move_with_when_it_was_read(
        self,
    ) -> None:
        read_at = tz_datetime.now()
        days = {
            staggered_monthly_update_at("1399", read_at + timedelta(days=offset)).day
            for offset in range(40)
        }

        assert len(days) == 1

    # TODO: Validate
    def test_the_month_rolls_over_at_the_end_of_the_year(
        self,
    ) -> None:
        december = tz_datetime.fromisoformat("2026-12-31T23:00:00+00:00")

        due = staggered_monthly_update_at("1399", december)

        assert (due.year, due.month) == (december.year + 1, 1)


# TODO: Validate
class TestWatchProvidersFileSchedule:
    # TODO: Validate
    def test_a_title_that_has_come_due_is_read_into_a_file_of_its_own(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=30),
        )
        tmdb_title.update_at = tz_datetime.now() - timedelta(days=1)
        plugin = TMDB(function_scoped_session)

        file = plugin.tv_series_watch_providers_file(
            1399,
            plugin._due_watch_providers_date(tmdb_title),  # noqa: SLF001
        )

        today = tz_datetime.now().date().isoformat()
        assert file.file_key() == f"TV Series/Watch Providers/1399/{today}.json"

    # TODO: Validate
    def test_a_title_that_has_not_come_due_is_answered_with_the_file_as_it_stands(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=30),
        )
        tmdb_title.update_at = tz_datetime.now() + timedelta(days=1)
        plugin = TMDB(function_scoped_session)

        file = plugin.tv_series_watch_providers_file(
            1399,
            plugin._due_watch_providers_date(tmdb_title),  # noqa: SLF001
        )

        assert file.file_key() == stored.key

    # TODO: Validate
    def test_a_title_that_is_not_asking_to_be_read_is_answered_with_the_file_as_it_stands(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        stored = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=30),
        )
        tmdb_title.update_at = None
        plugin = TMDB(function_scoped_session)

        file = plugin.tv_series_watch_providers_file(
            1399,
            plugin._due_watch_providers_date(tmdb_title),  # noqa: SLF001
        )

        assert file.file_key() == stored.key

    # TODO: Validate
    def test_a_file_read_against_a_newer_one_stops_asking_to_be_read(
        self,
        function_scoped_session: Session,
        tmdb_plugin: Plugin,
        tmdb_title: Title,
    ) -> None:
        older = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            date(2026, 8, 1),
            ["Netflix"],
            tz_datetime.now() - timedelta(days=30),
            tz_datetime.now() - timedelta(days=1),
        )
        newer = _store_title_providers(
            function_scoped_session,
            tmdb_plugin,
            1399,
            tz_datetime.now().date(),
            ["Netflix"],
            tz_datetime.now(),
            tz_datetime.now() + timedelta(days=20),
        )

        _sync_title_providers(
            function_scoped_session,
            tmdb_title.key,
            older,
            newer,
        )

        assert older.update_at is None
        assert newer.update_at is not None
