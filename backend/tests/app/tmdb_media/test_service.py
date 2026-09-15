# TODO: Validate
import pytest
from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.tmdb_links import link_episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.linking import old_link_title_to_tmdb


# TODO: Validate
def _source(session: Session) -> Source:
    plugin = Plugin.get(session, "TestPlugin")
    if plugin is None:
        plugin = Plugin(key="TestPlugin")
        session.add(plugin)
    source = Source.get(session, plugin, "TestPlugin")
    if source is None:
        source = Source(key="TestPlugin", plugin_id=plugin.id)
        session.add(source)
    session.flush()
    return source


# TODO: Validate
def _tmdb_title(session: Session, key: str) -> Title:
    title = Title(key=key, source_id=_source(session).id)
    session.add(title)
    session.flush()
    return title


# TODO: Validate
def _tmdb_episode(session: Session, key: str) -> Episode:
    season = Season(key=key, title=_tmdb_title(session, key))
    session.add(season)
    session.flush()
    episode = Episode(
        key=key,
        season=season,
        watch_identifier=f"TestPlugin {key}",
    )
    session.add(episode)
    session.flush()
    return episode


# TODO: Validate
def test_link_tmdb_title_makes_the_title_linked(
    function_scoped_session: Session,
) -> None:
    title = _tmdb_title(function_scoped_session, "tmdb-title-1")
    tmdb_title = _tmdb_title(function_scoped_session, "tmdb-title-2")

    old_link_title_to_tmdb(function_scoped_session, title, tmdb_title, "Test")

    assert title.is_linked
    assert title.tmdb_title_ids == [tmdb_title.id]


# TODO: Validate
def test_link_tmdb_title_treats_every_title_alike(
    function_scoped_session: Session,
) -> None:
    title = _tmdb_title(function_scoped_session, "tmdb-title-1")
    first = _tmdb_title(function_scoped_session, "tmdb-title-2")
    second = _tmdb_title(function_scoped_session, "tmdb-title-3")

    old_link_title_to_tmdb(function_scoped_session, title, first, "Test")
    old_link_title_to_tmdb(function_scoped_session, title, second, "Test")

    assert set(title.tmdb_title_ids) == {first.id, second.id}
    assert title.sole_tmdb_title_id is None


# TODO: Validate
def test_link_tmdb_title_rejects_a_copy_as_the_title(
    function_scoped_session: Session,
) -> None:
    title = _tmdb_title(function_scoped_session, "tmdb-title-1")
    copy = _tmdb_title(function_scoped_session, "tmdb-title-2")
    tmdb_title = _tmdb_title(function_scoped_session, "tmdb-title-3")
    old_link_title_to_tmdb(function_scoped_session, copy, tmdb_title, "Test")

    with pytest.raises(ValueError, match="is not a canonical title"):
        old_link_title_to_tmdb(function_scoped_session, title, copy, "Test")


# TODO: Validate
def test_link_tmdb_title_rejects_a_title_copies_hang_off(
    function_scoped_session: Session,
) -> None:
    title = _tmdb_title(function_scoped_session, "tmdb-title-1")
    copy = _tmdb_title(function_scoped_session, "tmdb-title-2")
    tmdb_title = _tmdb_title(function_scoped_session, "tmdb-title-3")
    old_link_title_to_tmdb(function_scoped_session, copy, title, "Test")
    function_scoped_session.flush()

    with pytest.raises(ValueError, match="has other titles linked to it"):
        old_link_title_to_tmdb(function_scoped_session, title, tmdb_title, "Test")


# TODO: Validate
def test_link_episode_links_the_title_to_the_title(
    function_scoped_session: Session,
) -> None:
    episode = _tmdb_episode(function_scoped_session, "tmdb-episode-1")
    tmdb_episode = _tmdb_episode(function_scoped_session, "tmdb-episode-2")

    link_episode(function_scoped_session, episode, tmdb_episode)

    assert episode.season.title.tmdb_title_ids == [
        tmdb_episode.season.title.id,
    ]
