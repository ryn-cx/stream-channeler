# TODO: Validate
from typing import Any

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

type MediaRecord = Plugin | Source | Show | Season | Episode
type CanonicalRecord = CanonicalShow | CanonicalSeason | CanonicalEpisode
type Record = MediaRecord | CanonicalRecord

CHILDREN: dict[type, tuple[str, type]] = {
    Plugin: ("sources", Source),
    Source: ("shows", Show),
    Show: ("seasons", Season),
    Season: ("episodes", Episode),
    CanonicalShow: ("canonical_seasons", CanonicalSeason),
    CanonicalSeason: ("canonical_episodes", CanonicalEpisode),
}


# TODO: Validate
def children(record: Record) -> list[Record]:
    entry = CHILDREN.get(type(record))
    if entry is None:
        return []
    child_records: list[Record] = getattr(record, entry[0])
    return child_records


# TODO: Validate
class SerializationMixin:
    # TODO: Validate
    @staticmethod
    def _dump_model(model: Record) -> dict[str, Any]:
        """Recursively dump a model into a dict."""
        data = model.model_dump()
        if type(model) in CHILDREN:
            key, _ = CHILDREN[type(model)]
            data[key] = sorted(
                [
                    SerializationMixin._dump_model(child)
                    for child in getattr(model, key)
                ],
                key=lambda x: x["id"],
            )
        return data

    # TODO: Validate
    @staticmethod
    def _load_model[
        T: (
            Plugin,
            Source,
            Show,
            Season,
            Episode,
            CanonicalShow,
            CanonicalSeason,
            CanonicalEpisode,
        ),
    ](
        model_class: type[T],
        data: dict[str, Any],
    ) -> T:
        """Recursively load a dict into a model."""
        model = model_class.model_validate(data)
        if model_class in CHILDREN:
            key, child_class = CHILDREN[model_class]
            setattr(
                model,
                key,
                [
                    SerializationMixin._load_model(child_class, child)
                    for child in data[key]
                ],
            )
        return model
