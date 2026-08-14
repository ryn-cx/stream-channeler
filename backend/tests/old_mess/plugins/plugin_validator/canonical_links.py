# TODO: Validate
from collections.abc import Sequence

from app.plugins.models import Plugin
from app.shows.models import Show

type CanonicalLinks = dict[str, list[str]]

SEPARATOR = " > "


# TODO: Validate
def _show_canonical_keys(show: Show) -> list[str]:
    """The key of every title `show` is a copy of."""
    return sorted({link.canonical_show.key for link in show.canonical_show_links})


# TODO: Validate
def collect_canonical_links(plugins: Sequence[Plugin]) -> CanonicalLinks:
    """Name what each copy is a copy of by key rather than by id.

    A copy points at a canonical row by an id that is generated afresh on every
    run, so an id is only ever good for saying whether the link changed and
    never for saying which row it is now of. The keys are what stay put, so the
    link is written down as the key of the row at each end, under a path of the
    keys leading to the copy, which is what makes the two runs comparable.

    Every plugin is walked rather than only the one under test, because a copy
    an import writes is often stored under the plugin of the service that
    streams it and it is that copy whose links the import settles.
    """
    links: CanonicalLinks = {}
    for plugin in plugins:
        for source in plugin.sources:
            for show in source.shows:
                show_path = SEPARATOR.join((plugin.key, source.key, show.key))
                links[show_path] = _show_canonical_keys(show)
                for season in show.seasons:
                    season_path = SEPARATOR.join((show_path, season.key))
                    links[season_path] = [season.canonical_season.key]
                    for episode in season.episodes:
                        episode_path = SEPARATOR.join((season_path, episode.key))
                        links[episode_path] = [episode.canonical_episode.key]
    return links
