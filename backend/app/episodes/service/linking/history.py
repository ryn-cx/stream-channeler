# TODO: Validate

import uuid
from typing import Any

from sqlalchemy import (
    Integer,
    Select,
    String,
    Uuid,
    cast,
    literal,
    null,
    union_all,
)
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.schemas import (
    EpisodeLinkHistoryOutput,
    EpisodeLinkHistoryPublic,
)
from app.episodes.service.records import episode_record
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title

_source_episode: Any = aliased(Episode)
_source_season: Any = aliased(Season)
_source_title: Any = aliased(Title)
_source_source: Any = aliased(Source)
_source_plugin: Any = aliased(Plugin)
_tmdb_episode: Any = aliased(Episode)
_tmdb_season: Any = aliased(Season)
_tmdb_title: Any = aliased(Title)


# TODO: Validate
def _link_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("link").label("kind"),
            col(EpisodeTmdbEpisode.id).label("entry_id"),
            col(EpisodeTmdbEpisode.episode_id).label("episode_id"),
            col(EpisodeTmdbEpisode.tmdb_episode_id).label("tmdb_episode_id"),
            col(EpisodeTmdbEpisode.note).label("note"),
            col(EpisodeTmdbEpisode.created_at).label("happened_at"),
            _source_title.name.label("title_name"),
            _source_source.key.label("source_key"),
            _source_plugin.key.label("plugin_name"),
            _source_season.season_number.label("season_number"),
            _source_episode.episode_number.label("episode_number"),
            _source_episode.name.label("episode_name"),
            _tmdb_title.name.label("tmdb_title_name"),
            _tmdb_season.season_number.label("tmdb_season_number"),
            _tmdb_episode.episode_number.label("tmdb_episode_number"),
            _tmdb_episode.name.label("tmdb_episode_name"),
        )
        .select_from(EpisodeTmdbEpisode)
        .join(
            _source_episode,
            onclause=col(EpisodeTmdbEpisode.episode_id) == _source_episode.id,
        )
        .join(_source_season, onclause=_source_episode.season_id == _source_season.id)
        .join(_source_title, onclause=_source_season.title_id == _source_title.id)
        .join(_source_source, onclause=_source_title.source_id == _source_source.id)
        .join(_source_plugin, onclause=_source_source.plugin_id == _source_plugin.id)
        .join(
            _tmdb_episode,
            onclause=col(EpisodeTmdbEpisode.tmdb_episode_id) == _tmdb_episode.id,
        )
        .join(_tmdb_season, onclause=_tmdb_episode.season_id == _tmdb_season.id)
        .join(_tmdb_title, onclause=_tmdb_season.title_id == _tmdb_title.id)
        .where(
            col(EpisodeTmdbEpisode.manual_tmdb_link).is_(True),
            col(_source_episode.deleted_at).is_(None),
            col(_tmdb_episode.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _ignored_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("ignored").label("kind"),
            col(Episode.id).label("entry_id"),
            col(Episode.id).label("episode_id"),
            cast(null(), Uuid).label("tmdb_episode_id"),
            cast(null(), String).label("note"),
            col(Episode.ignored_at).label("happened_at"),
            col(Title.name).label("title_name"),
            col(Source.key).label("source_key"),
            col(Plugin.key).label("plugin_name"),
            col(Season.season_number).label("season_number"),
            col(Episode.episode_number).label("episode_number"),
            col(Episode.name).label("episode_name"),
            cast(null(), String).label("tmdb_title_name"),
            cast(null(), Integer).label("tmdb_season_number"),
            cast(null(), Integer).label("tmdb_episode_number"),
            cast(null(), String).label("tmdb_episode_name"),
        )
        .select_from(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            col(Episode.ignored_at).is_not(None),
            col(Episode.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _absent_entries() -> Select[Any]:
    return (  # type: ignore[no-any-return]
        select(  # type: ignore[call-overload]
            literal("absent").label("kind"),
            col(Episode.id).label("entry_id"),
            col(Episode.id).label("episode_id"),
            cast(null(), Uuid).label("tmdb_episode_id"),
            cast(null(), String).label("note"),
            col(Episode.tmdb_absent_at).label("happened_at"),
            col(Title.name).label("title_name"),
            col(Source.key).label("source_key"),
            col(Plugin.key).label("plugin_name"),
            col(Season.season_number).label("season_number"),
            col(Episode.episode_number).label("episode_number"),
            col(Episode.name).label("episode_name"),
            cast(null(), String).label("tmdb_title_name"),
            cast(null(), Integer).label("tmdb_season_number"),
            cast(null(), Integer).label("tmdb_episode_number"),
            cast(null(), String).label("tmdb_episode_name"),
        )
        .select_from(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            col(Episode.tmdb_absent_at).is_not(None),
            col(Episode.tmdb_episode_validated_at).is_not(None),
            col(Episode.deleted_at).is_(None),
        )
    )


# TODO: Validate
def list_episode_link_history(
    session: Session,
    params: ReadOptions,
) -> EpisodeLinkHistoryPublic:
    entries = union_all(
        _link_entries(),
        _ignored_entries(),
        _absent_entries(),
    ).subquery()
    columns: dict[str, Any] = {
        "kind": entries.c.kind,
        "created_at": entries.c.happened_at,
        "note": entries.c.note,
        "title_name": entries.c.title_name,
        "source_key": entries.c.source_key,
        "plugin_name": entries.c.plugin_name,
        "season_number": entries.c.season_number,
        "episode_number": entries.c.episode_number,
        "episode_name": entries.c.episode_name,
        "tmdb_title_name": entries.c.tmdb_title_name,
        "tmdb_season_number": entries.c.tmdb_season_number,
        "tmdb_episode_number": entries.c.tmdb_episode_number,
        "tmdb_episode_name": entries.c.tmdb_episode_name,
    }
    base = select(entries)  # type: ignore[call-overload]
    filtered = _apply_filter_options(base, params.filter_options, columns)
    total_count = session.exec(
        select(func.count()).select_from(base.subquery()),
    ).one()
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            columns,
            [entries.c.happened_at],
            entries.c.entry_id,  # type: ignore[arg-type]
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return EpisodeLinkHistoryPublic(
        data=_history_outputs(session, list(session.execute(page).all())),
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )


# TODO: Validate
def _history_outputs(
    session: Session,
    entries: list[Any],
) -> list[EpisodeLinkHistoryOutput]:
    episodes = _episodes_by_id(
        session,
        {entry.episode_id for entry in entries}
        | {entry.tmdb_episode_id for entry in entries if entry.tmdb_episode_id},
    )
    return [
        EpisodeLinkHistoryOutput(
            id=entry.entry_id,
            kind=entry.kind,
            episode_id=entry.episode_id,
            tmdb_episode_id=entry.tmdb_episode_id,
            note=entry.note,
            created_at=entry.happened_at,
            episode=episode_record(episodes[entry.episode_id]),
            tmdb=(
                episode_record(episodes[entry.tmdb_episode_id])
                if entry.tmdb_episode_id
                else None
            ),
        )
        for entry in entries
    ]


# TODO: Validate
def _episodes_by_id(
    session: Session,
    episode_ids: set[uuid.UUID],
) -> dict[uuid.UUID, Episode]:
    if not episode_ids:
        return {}
    statement = Episode.select_with_plugin_eager().where(
        col(Episode.id).in_(episode_ids),
    )
    return {episode.id: episode for episode in session.exec(statement).all()}
