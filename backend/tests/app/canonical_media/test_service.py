# TODO: Validate
import pytest
from sqlmodel import Session

from app.canonical_media.service import add_canonical_show
from app.episodes.canonical_links import link_episode
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


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
def _canonical_show(session: Session, key: str) -> Show:
    show = Show(key=key, source_id=_source(session).id)
    session.add(show)
    session.flush()
    return show


# TODO: Validate
def _canonical_episode(session: Session, key: str) -> Episode:
    season = Season(key=key, show=_canonical_show(session, key))
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
def test_link_canonical_show_makes_the_show_non_canonical(
    function_scoped_session: Session,
) -> None:
    show = _canonical_show(function_scoped_session, "tmdb-show-1")
    canonical_show = _canonical_show(function_scoped_session, "tmdb-show-2")

    add_canonical_show(function_scoped_session, show, canonical_show)

    assert not show.is_canonical
    assert show.canonical_show_ids == [canonical_show.id]


# TODO: Validate
def test_link_canonical_show_treats_every_title_alike(
    function_scoped_session: Session,
) -> None:
    show = _canonical_show(function_scoped_session, "tmdb-show-1")
    first = _canonical_show(function_scoped_session, "tmdb-show-2")
    second = _canonical_show(function_scoped_session, "tmdb-show-3")

    add_canonical_show(function_scoped_session, show, first)
    add_canonical_show(function_scoped_session, show, second)

    assert set(show.canonical_show_ids) == {first.id, second.id}
    assert show.sole_canonical_show_id is None


# TODO: Validate
def test_link_canonical_show_rejects_a_copy_as_the_title(
    function_scoped_session: Session,
) -> None:
    show = _canonical_show(function_scoped_session, "tmdb-show-1")
    copy = _canonical_show(function_scoped_session, "tmdb-show-2")
    canonical_show = _canonical_show(function_scoped_session, "tmdb-show-3")
    add_canonical_show(function_scoped_session, copy, canonical_show)

    with pytest.raises(ValueError, match="is not a canonical show"):
        add_canonical_show(function_scoped_session, show, copy)


# TODO: Validate
def test_link_canonical_show_rejects_a_title_copies_hang_off(
    function_scoped_session: Session,
) -> None:
    show = _canonical_show(function_scoped_session, "tmdb-show-1")
    copy = _canonical_show(function_scoped_session, "tmdb-show-2")
    canonical_show = _canonical_show(function_scoped_session, "tmdb-show-3")
    add_canonical_show(function_scoped_session, copy, show)
    function_scoped_session.flush()

    with pytest.raises(ValueError, match="has other shows linked to it"):
        add_canonical_show(function_scoped_session, show, canonical_show)


# TODO: Validate
def test_link_episode_links_the_show_to_the_title(
    function_scoped_session: Session,
) -> None:
    episode = _canonical_episode(function_scoped_session, "tmdb-episode-1")
    canonical_episode = _canonical_episode(function_scoped_session, "tmdb-episode-2")

    link_episode(function_scoped_session, episode, canonical_episode)

    assert episode.season.show.canonical_show_ids == [
        canonical_episode.season.show.id,
    ]
